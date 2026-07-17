"""PTY-backed interactive shell for the Fix Pro Bridge."""

from __future__ import annotations

import json
import fcntl
import os
import pty
import select
import signal
import struct
import termios
import threading
import time
from typing import Any

from app.websocket import WebSocketClient


def run(command: str, gateway_url: str, token: str, timeout: int = 120, session: str = "") -> None:
    ws = WebSocketClient(_session_url(gateway_url, token, "device", session), timeout=15)
    master, slave = pty.openpty()
    _resize(master, 120, 32)
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    env.setdefault("COLORTERM", "truecolor")
    cwd = os.path.expanduser("~/FixProBridge")
    pid = os.fork()
    if pid == 0:
        try:
            os.setsid()
            # Make the PTY the controlling terminal so sh enables job
            # control and interactive programs do not print "can't access tty".
            try:
                fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
            except OSError:
                pass
            os.dup2(slave, 0)
            os.dup2(slave, 1)
            os.dup2(slave, 2)
            os.close(master)
            os.close(slave)
            os.chdir(cwd if os.path.isdir(cwd) else os.path.expanduser("~"))
            os.execvpe("sh", ["sh"], env)
        finally:
            os._exit(127)
    os.close(slave)
    if command.strip():
        os.write(master, (command.rstrip() + "\n").encode("utf-8"))
    started = time.monotonic()
    stop = threading.Event()

    def output() -> None:
        while not stop.is_set():
            try:
                ready, _, _ = select.select([master], [], [], 0.25)
                if not ready:
                    continue
                data = os.read(master, 8192)
                if data:
                    ws.send_text(json.dumps({"type": "output", "data": data.decode("utf-8", "replace")}, ensure_ascii=False, separators=(",", ":")))
            except (OSError, ValueError):
                break

    def input_loop() -> None:
        try:
            while not stop.is_set():
                opcode, raw = ws.recv()
                if opcode == 8:
                    _terminate(pid)
                    break
                if opcode == 9:
                    continue
                if opcode != 1:
                    continue
                data = json.loads(raw.decode("utf-8", "replace"))
                kind = data.get("type")
                if kind == "input":
                    os.write(master, str(data.get("data", "")).encode("utf-8"))
                elif kind == "resize":
                    _resize(master, int(data.get("cols", 120)), int(data.get("rows", 32)))
                elif kind == "close":
                    _terminate(pid)
                    break
        except Exception as error:
            if not stop.is_set():
                _send_error(ws, str(error))
            _terminate(pid)

    ws.send_text(json.dumps({"type": "device_ready", "cwd": cwd, "pty": True}, separators=(",", ":")))
    reader = threading.Thread(target=output, daemon=True, name="bridge-pty-output")
    receiver = threading.Thread(target=input_loop, daemon=True, name="bridge-pty-input")
    reader.start()
    receiver.start()
    try:
        while True:
            waited, status = os.waitpid(pid, os.WNOHANG)
            if waited == pid:
                code = os.waitstatus_to_exitcode(status)
                ws.send_text(json.dumps({"type": "exit", "code": code}, separators=(",", ":")))
                break
            if time.monotonic() - started > max(5, min(300, timeout)):
                _terminate(pid)
                ws.send_text(json.dumps({"type": "exit", "code": 124, "message": "Timeout da sessão."}, separators=(",", ":")))
                break
            time.sleep(0.1)
    finally:
        stop.set()
        try:
            os.close(master)
        except OSError:
            pass
        ws.close()


def _session_url(url: str, token: str, role: str, session: str = "") -> str:
    separator = "&" if "?" in url else "?"
    suffix = f"&session={session}" if session else ""
    return f"{url}{separator}token={token}&role={role}{suffix}"


def _resize(fd: int, cols: int, rows: int) -> None:
    cols = max(40, min(240, cols))
    rows = max(10, min(100, rows))
    try:
        import fcntl
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except (OSError, ImportError):
        pass


def _terminate(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def _send_error(ws: WebSocketClient, message: str) -> None:
    try:
        ws.send_text(json.dumps({"type": "error", "message": message[:500]}, ensure_ascii=False, separators=(",", ":")))
    except OSError:
        pass
