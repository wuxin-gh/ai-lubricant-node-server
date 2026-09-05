"""Unit tests for the in-process NodeService server crypto + wire framing.

These are pure-unit (no DB, no network): they lock the byte-level parity that
lets the shipped Go ``agent-compose-agent`` authenticate against us unchanged —
TOTP codes, AES-GCM seal/open, and the Connect streaming envelope format.
"""
from __future__ import annotations

from datetime import datetime, timezone

from node_server import crypto, envelope
from node_server.registry import Registry
from node_server import agentcompose_v2_pb2 as pb


# ── TOTP ────────────────────────────────────────────────────────────────────


def test_totp_rfc6238_test_vector():
    """RFC 6238 SHA1 vector: secret "12345678901234567890" at T=59 → 287082.

    This is the published test vector; matching it guarantees byte-parity with
    the Go ``totp.Generate`` (same HMAC-SHA1 / dynamic-truncation / mod path).
    """
    secret = b"12345678901234567890"
    t = datetime.fromtimestamp(59, tz=timezone.utc)
    assert crypto.generate(secret, t) == "287082"


def test_totp_generate_validate_roundtrip():
    secret_b32 = crypto.generate_secret()
    secret = crypto.decode_secret(secret_b32)
    now = crypto.utc_now()
    code = crypto.generate(secret, now)
    replay = crypto.ReplayCache()
    assert crypto.validate(secret, code, now, replay, "node-x") is True


def test_totp_replay_rejected():
    secret = crypto.decode_secret(crypto.generate_secret())
    now = crypto.utc_now()
    code = crypto.generate(secret, now)
    replay = crypto.ReplayCache()
    assert crypto.validate(secret, code, now, replay, "node-x") is True
    # Second use of the same (node, code) while the connection is live is replay.
    assert crypto.validate(secret, code, now, replay, "node-x") is False


def test_totp_claim_released_after_connection_ends():
    """A restarted node can authenticate again in the same 30-second step."""
    secret = crypto.decode_secret(crypto.generate_secret())
    now = crypto.utc_now()
    code = crypto.generate(secret, now)
    replay = crypto.ReplayCache()
    assert crypto.validate(secret, code, now, replay, "node-x") is True
    replay.release("node-x")
    assert crypto.validate(secret, code, now, replay, "node-x") is True


def test_totp_release_is_scoped_to_one_node():
    replay = crypto.ReplayCache()
    now = crypto.utc_now()
    assert replay.claim("node-a", "123456", now) is True
    assert replay.claim("node-b", "123456", now) is True
    replay.release("node-a")
    assert replay.claim("node-a", "123456", now) is True
    assert replay.claim("node-b", "123456", now) is False


def test_registry_releases_claim_only_for_current_connection():
    replay = crypto.ReplayCache()
    registry = Registry()
    registry.on_disconnect = replay.release
    now = crypto.utc_now()

    assert replay.claim("node-x", "123456", now) is True
    stale = registry.register("node-x", None)
    fresh = registry.register("node-x", None)

    # Teardown of the superseded stale stream must not release the fresh/live
    # node's claim (identity-safe unregister).
    registry.unregister("node-x", stale)
    assert replay.claim("node-x", "123456", now) is False

    # Once the actual current stream ends, a same-step restart can claim it.
    registry.unregister("node-x", fresh)
    assert replay.claim("node-x", "123456", now) is True


def test_totp_skew_window():
    secret = crypto.decode_secret(crypto.generate_secret())
    base = crypto.utc_now()
    # A code generated one step (30s) in the past still validates (±2 window).
    from datetime import timedelta

    past = base - timedelta(seconds=30)
    code = crypto.generate(secret, past)
    assert crypto.validate(secret, code, base, crypto.ReplayCache(), "n") is True


def test_totp_wrong_code_rejected():
    secret = crypto.decode_secret(crypto.generate_secret())
    now = crypto.utc_now()
    assert crypto.validate(secret, "000000", now, crypto.ReplayCache(), "n") in (True, False)
    # Deterministic wrong code: a code from far in the past (outside window).
    from datetime import timedelta

    stale = crypto.generate(secret, now - timedelta(seconds=3000))
    assert crypto.validate(secret, stale, now, crypto.ReplayCache(), "n") is False


# ── AES-256-GCM secret store ─────────────────────────────────────────────────


def test_secretstore_seal_open_roundtrip():
    key = bytes(range(32))
    store = crypto.SecretStore(key)
    plaintext = b"HELLO-SECRET-BASE32"
    sealed = store.seal(plaintext)
    assert store.open(sealed) == plaintext
    # The sealed blob is not the plaintext.
    assert plaintext.decode() not in sealed


def test_secretstore_wrong_key_fails():
    sealed = crypto.SecretStore(bytes(range(32))).seal(b"secret")
    other = crypto.SecretStore(bytes(range(32, 64)))
    try:
        other.open(sealed)
        assert False, "expected decrypt failure under wrong key"
    except ValueError:
        pass


def test_parse_master_key_hex_and_base64():
    import base64

    raw = bytes(range(32))
    hex_key = raw.hex()
    assert crypto.parse_master_key(hex_key) == raw
    b64_key = base64.standard_b64encode(raw).decode()
    assert crypto.parse_master_key(b64_key) == raw


def test_parse_master_key_rejects_bad_length():
    try:
        crypto.parse_master_key("deadbeef")
        assert False, "expected rejection of short key"
    except ValueError:
        pass


# ── Connect streaming envelope ────────────────────────────────────────────────


def test_envelope_message_roundtrip():
    frame = pb.NodeUpstreamFrame()
    frame.heartbeat.node_id = "node-1"
    frame.heartbeat.active_session_ids.extend(["s1", "s2"])
    raw = envelope.encode_message(frame)

    dec = envelope.FrameDecoder()
    dec.feed(raw)
    flags, payload = dec.next_frame()
    assert flags & envelope.FLAG_END_STREAM == 0
    out = pb.NodeUpstreamFrame()
    out.ParseFromString(payload)
    assert out.heartbeat.node_id == "node-1"
    assert list(out.heartbeat.active_session_ids) == ["s1", "s2"]


def test_envelope_chunk_boundary_reassembly():
    frame = pb.NodeUpstreamFrame()
    frame.register.node_id = "node-xyz"
    frame.register.totp_code = "123456"
    raw = envelope.encode_message(frame)

    dec = envelope.FrameDecoder()
    # Feed byte-by-byte: no frame until the last byte lands.
    for i, b in enumerate(raw):
        dec.feed(bytes([b]))
        got = dec.next_frame()
        if i < len(raw) - 1:
            assert got is None
        else:
            assert got is not None
            flags, payload = got
            out = pb.NodeUpstreamFrame()
            out.ParseFromString(payload)
            assert out.register.node_id == "node-xyz"


def test_envelope_end_stream_trailer():
    clean = envelope.encode_end_stream(None)
    dec = envelope.FrameDecoder()
    dec.feed(clean)
    flags, payload = dec.next_frame()
    assert flags & envelope.FLAG_END_STREAM
    assert envelope.parse_end_stream(payload) == {}

    err = envelope.encode_end_stream({"code": "permission_denied", "message": "nope"})
    dec2 = envelope.FrameDecoder()
    dec2.feed(err)
    _, payload2 = dec2.next_frame()
    parsed = envelope.parse_end_stream(payload2)
    assert parsed["error"]["code"] == "permission_denied"


def test_rfc3339nano_format():
    t = datetime(2026, 7, 25, 12, 0, 0, 123456, tzinfo=timezone.utc)
    s = crypto.rfc3339nano(t)
    # 9 fractional digits + Z, parseable by Go's time.RFC3339Nano.
    assert s == "2026-07-25T12:00:00.123456000Z"
