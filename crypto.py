"""Node authentication crypto: AES-256-GCM secret sealing + RFC-6238 TOTP.

Ported 1:1 from the Go daemon so the shipped ``agent-compose-agent`` binary
authenticates against us unchanged:

* ``SecretStore`` — seals/opens a node's per-node TOTP secret under a single
  node credential encryption key (``NODE_CREDENTIAL_ENCRYPTION_KEY``). Blob layout is
  ``base64(nonce || ciphertext||tag)`` with a random 12-byte GCM nonce —
  byte-identical to ``pkg/auth/secretstore``.
* TOTP (``generate``/``validate``) — HMAC-SHA1, 6 digits, 30s step, ±2 step
  window, matching ``pkg/auth/totp`` and Google-Authenticator defaults.
* ``ReplayCache`` — blocks reuse of an accepted ``(node_id, code)`` within the
  acceptance window.

The master key is the control root: every node's secret is sealed under it, so
a lost/rotated key strands every stored credential. We fail fast when it is
missing or malformed (mirroring the Go daemon) rather than generating one.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets as _secrets
import struct
import threading
import time as _time
from datetime import datetime, timezone

# ── TOTP parameters (match pkg/auth/totp) ──────────────────────────────────
TIME_STEP = 30      # seconds per RFC 6238 step
DIGITS = 6          # code length
SECRET_BYTES = 20   # generated-secret entropy
STEP_WINDOW = 2     # accept ±STEP_WINDOW steps (≈±60s skew)

# ── secret-store master key length (AES-256) ───────────────────────────────
KEY_BYTES = 32

_B32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


# ── base32 (no padding), tolerant decode — matches Go base32NoPad ──────────

def generate_secret() -> str:
    """Return a fresh random base32 (no-padding) secret string."""
    buf = _secrets.token_bytes(SECRET_BYTES)
    return base64.b32encode(buf).decode("ascii").rstrip("=")


def decode_secret(encoded: str) -> bytes:
    """Decode a base32 secret to raw bytes. Uppercases, strips whitespace,
    tolerates missing padding — matches Go ``totp.DecodeSecret``."""
    cleaned = "".join(encoded.split()).upper()
    if not cleaned:
        raise ValueError("decode totp secret: empty")
    pad = (-len(cleaned)) % 8
    try:
        decoded = base64.b32decode(cleaned + ("=" * pad))
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"decode totp secret: {exc}") from exc
    if not decoded:
        raise ValueError("decode totp secret: empty")
    return decoded


def _generate_at_counter(secret: bytes, counter: int) -> str:
    buf = struct.pack(">Q", counter)
    mac = hmac.new(secret, buf, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    binv = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    mod = 10 ** DIGITS
    return str(binv % mod).zfill(DIGITS)


def generate(secret: bytes, t: datetime) -> str:
    """TOTP code for ``secret`` at time ``t`` (UTC-normalized)."""
    counter = int(t.astimezone(timezone.utc).timestamp()) // TIME_STEP
    return _generate_at_counter(secret, counter)


def validate(secret: bytes, code: str, now: datetime, replay: "ReplayCache | None", node_id: str) -> bool:
    """True when ``code`` is valid for ``secret`` within ±STEP_WINDOW steps of
    ``now``; claims the ``(node_id, code)`` in ``replay`` to block reuse."""
    code = code.strip()
    if len(code) != DIGITS:
        return False
    base = int(now.astimezone(timezone.utc).timestamp()) // TIME_STEP
    for delta in range(-STEP_WINDOW, STEP_WINDOW + 1):
        step = base + delta
        if step < 0:
            continue
        if _generate_at_counter(secret, step) == code:
            if replay is not None and not replay.claim(node_id, code, now):
                return False  # replay
            return True
    return False


class ReplayCache:
    """Blocks reuse of an accepted ``(node_id, code)`` within the acceptance
    window. Memory-only; TTL covers the widest validating window + margin.

    A node that restarts inside the same 30s TOTP step derives the *same* code
    from the server time, so a pure TTL cache would lock it out until the step
    rolled over — the reconnect backoff starts at 1s, well inside the step, so
    the node would spin on PERMISSION_DENIED. ``release`` therefore drops a
    node's claims once its stream is gone: a genuine restart re-authenticates
    immediately, while a second live process reusing the code is still rejected
    for as long as the first one holds the connection.
    """

    def __init__(self) -> None:
        self._ttl = float((STEP_WINDOW * 2 + 1) * TIME_STEP) + 30.0
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def claim(self, node_id: str, code: str, now: datetime) -> bool:
        now_s = now.astimezone(timezone.utc).timestamp()
        with self._lock:
            self._prune_locked(now_s)
            key = f"{node_id}|{code}"
            if key in self._seen:
                return False
            self._seen[key] = now_s
            return True

    def release(self, node_id: str) -> None:
        """Drop every claim held by ``node_id`` (its connection ended)."""
        prefix = f"{node_id}|"
        with self._lock:
            for key in [k for k in self._seen if k.startswith(prefix)]:
                del self._seen[key]

    def _prune_locked(self, now_s: float) -> None:
        expired = [k for k, at in self._seen.items() if now_s - at > self._ttl]
        for k in expired:
            del self._seen[k]


def otpauth_uri(secret_b32: str, node_id: str, issuer: str = "agent-compose") -> str:
    """Build a standard ``otpauth://totp/...`` provisioning URI (SHA1, 6 digits,
    30s), so an operator can load the same secret into an authenticator app."""
    from urllib.parse import quote, urlencode

    label = quote(f"{issuer}:{node_id}")
    query = urlencode({
        "secret": secret_b32,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": str(DIGITS),
        "period": str(TIME_STEP),
    })
    return f"otpauth://totp/{label}?{query}"


# ── AES-256-GCM secret store (match pkg/auth/secretstore) ───────────────────

def parse_master_key(raw: str) -> bytes:
    """Decode a master key given as hex (64 chars) or base64 (std/url, padded
    or raw); must decode to exactly 32 bytes. Raises ValueError otherwise."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("master key is empty")
    if len(raw) == KEY_BYTES * 2:
        try:
            return binascii.unhexlify(raw)
        except (binascii.Error, ValueError):
            pass
    for decoder in (base64.standard_b64decode, base64.urlsafe_b64decode):
        for candidate in (raw, raw + "=" * ((-len(raw)) % 4)):
            try:
                decoded = decoder(candidate)
            except (binascii.Error, ValueError):
                continue
            if len(decoded) == KEY_BYTES:
                return decoded
    raise ValueError(f"master key must decode to {KEY_BYTES} bytes (hex or base64)")


class SecretStore:
    """Seals/opens secrets under a fixed AES-256-GCM master key.

    Blob = ``base64(nonce || ciphertext||tag)``, 12-byte nonce — byte-compatible
    with the Go daemon so credentials are portable across the two servers.
    """

    def __init__(self, key: bytes) -> None:
        if len(key) != KEY_BYTES:
            raise ValueError(f"secretstore: master key must be {KEY_BYTES} bytes, got {len(key)}")
        # Imported lazily so importing this module never hard-requires the
        # server crypto stack when the node server is disabled.
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        self._aesgcm = AESGCM(key)
        self._nonce_size = 12

    def seal(self, plaintext: bytes) -> str:
        nonce = _secrets.token_bytes(self._nonce_size)
        sealed = self._aesgcm.encrypt(nonce, plaintext, None)
        return base64.standard_b64encode(nonce + sealed).decode("ascii")

    def open(self, blob: str) -> bytes:
        try:
            raw = base64.standard_b64decode(blob.strip())
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"secretstore: decode blob: {exc}") from exc
        if len(raw) < self._nonce_size:
            raise ValueError("secretstore: blob too short")
        nonce, ciphertext = raw[:self._nonce_size], raw[self._nonce_size:]
        try:
            return self._aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as exc:  # noqa: BLE001 — InvalidTag et al.
            raise ValueError("secretstore: decrypt (wrong master key or corrupt data)") from exc


def utc_now() -> datetime:
    """Timezone-aware UTC now (single source for server_time/heartbeat stamps)."""
    return datetime.now(timezone.utc)


def rfc3339nano(t: datetime) -> str:
    """Format ``t`` as RFC3339 with nanosecond precision + ``Z`` — the shape the
    Go agent parses with ``time.RFC3339Nano``."""
    t = t.astimezone(timezone.utc)
    # Python has microsecond precision; pad to 9 fractional digits.
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond * 1000:09d}" + "Z"


# Silence "imported but unused" for the time shim kept for parity/debugging.
_ = _time
