"""Connect streaming wire framing (``application/connect+proto``).

The Go ``agent-compose-agent`` opens ``NodeConnect`` as a connect-go
bidirectional stream. connect-go's default streaming codec frames every message
as an *envelope*:

    ┌────────┬──────────────┬───────────────┐
    │ 1 byte │ 4 bytes (BE) │ N bytes       │
    │ flags  │ length (u32) │ payload       │
    └────────┴──────────────┴───────────────┘

* ``flags`` is a bitset. Bit ``0x02`` (``FLAG_END_STREAM``) marks the final
  *end-of-stream* envelope whose payload is a JSON trailer object, not a
  protobuf message. On success the trailer is ``{}``; on error it carries
  ``{"error": {"code": "...", "message": "..."}}`` plus any trailing metadata.
  Bit ``0x01`` (``FLAG_COMPRESSED``) marks a compressed payload — we neither
  send nor accept compression (we advertise identity), so a set compression bit
  on a data frame is treated as a protocol error.
* Data envelopes (``flags`` without the end bit) carry a binary-serialized
  protobuf message.

This module is transport-agnostic: it turns a byte stream into a sequence of
``(flags, payload)`` frames and back. The ASGI handler in
:mod:`connect_stream` owns the actual ``receive``/``send`` chunk plumbing.

References: connect protocol — "Streaming RPCs" envelope format.
"""
from __future__ import annotations

import json
import struct
from typing import Optional

# Content type connect-go uses for a binary-proto stream. The agent negotiates
# this by default (no ``WithProtoJSON`` option is set on the client).
CONTENT_TYPE = "application/connect+proto"

# Envelope flag bits.
FLAG_COMPRESSED = 0x01
FLAG_END_STREAM = 0x02

# 1 flag byte + 4-byte big-endian length prefix.
_PREFIX = struct.Struct(">BI")
PREFIX_LEN = _PREFIX.size  # 5


def encode_frame(payload: bytes, *, flags: int = 0) -> bytes:
    """Encode one envelope: ``flags || len(payload) || payload``."""
    return _PREFIX.pack(flags & 0xFF, len(payload)) + payload


def encode_message(msg) -> bytes:
    """Encode a protobuf message as a data envelope (flags = 0)."""
    return encode_frame(msg.SerializeToString(), flags=0)


def encode_end_stream(error: Optional[dict] = None) -> bytes:
    """Encode the terminal end-of-stream envelope.

    ``error`` is ``None`` for a clean close (trailer ``{}``) or a Connect error
    object ``{"code": str, "message": str}`` for a failure.
    """
    trailer: dict = {}
    if error is not None:
        trailer["error"] = error
    payload = json.dumps(trailer, separators=(",", ":")).encode("utf-8")
    return encode_frame(payload, flags=FLAG_END_STREAM)


class FrameDecoder:
    """Incremental decoder: feed raw bytes, pull out complete envelopes.

    The ASGI ``receive`` channel hands us arbitrary chunk boundaries, so we
    buffer and only surface a frame once its full ``5 + length`` bytes are in.
    """

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> None:
        if data:
            self._buf.extend(data)

    def __iter__(self):
        return self

    def __next__(self) -> tuple[int, bytes]:
        frame = self.next_frame()
        if frame is None:
            raise StopIteration
        return frame

    def next_frame(self) -> Optional[tuple[int, bytes]]:
        """Return the next ``(flags, payload)`` if a whole envelope is buffered,
        else ``None``. Does not block."""
        if len(self._buf) < PREFIX_LEN:
            return None
        flags, length = _PREFIX.unpack_from(self._buf, 0)
        total = PREFIX_LEN + length
        if len(self._buf) < total:
            return None
        payload = bytes(self._buf[PREFIX_LEN:total])
        del self._buf[:total]
        return flags, payload


def parse_end_stream(payload: bytes) -> dict:
    """Parse an end-of-stream trailer payload into a dict (``{}`` when empty)."""
    text = payload.decode("utf-8").strip()
    if not text:
        return {}
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}
