"""Minimal WebSocket client used by the interactive Bridge terminal.

It deliberately uses only the Python standard library so Termux does not need
another native dependency. The gateway speaks text JSON frames.
"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import ssl
import struct
from urllib.parse import urlparse


class WebSocketError(RuntimeError):
    pass


class WebSocketClient:
    def __init__(self, url: str, timeout: float = 10) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
            raise WebSocketError("URL WebSocket inválida.")
        self.url = url
        self.timeout = timeout
        self.sock = socket.create_connection((parsed.hostname, parsed.port or (443 if parsed.scheme == "wss" else 80)), timeout=timeout)
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            self.sock = context.wrap_socket(self.sock, server_hostname=parsed.hostname)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        host = parsed.hostname if parsed.port is None else f"{parsed.hostname}:{parsed.port}"
        request = (
            f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WebSocketError("Gateway fechou o handshake.")
            response += chunk
        if not response.startswith(b"HTTP/1.1 101"):
            raise WebSocketError(response.split(b"\r\n", 1)[0].decode("latin1", "replace"))

    def send_text(self, text: str) -> None:
        self._send(text.encode("utf-8"), 1)

    def recv(self) -> tuple[int, bytes]:
        first, second = self._read_exact(2)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        if length > 4 * 1024 * 1024:
            raise WebSocketError("Frame WebSocket excede o limite.")
        masked = bool(second & 0x80)
        mask = self._read_exact(4) if masked else b""
        data = bytearray(self._read_exact(length))
        if mask:
            for index in range(length):
                data[index] ^= mask[index % 4]
        return opcode, bytes(data)

    def close(self) -> None:
        try:
            self._send(b"", 8)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    def _send(self, payload: bytes, opcode: int) -> None:
        mask = os.urandom(4)
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length <= 0xFFFF:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        encoded = bytes(payload[index] ^ mask[index % 4] for index in range(length))
        self.sock.sendall(bytes(header) + mask + encoded)

    def _read_exact(self, size: int) -> bytes:
        result = bytearray()
        while len(result) < size:
            chunk = self.sock.recv(size - len(result))
            if not chunk:
                raise WebSocketError("Conexão WebSocket encerrada.")
            result.extend(chunk)
        return bytes(result)
