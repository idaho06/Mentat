"""A minimal raw IRC client used as "the other user" in integration tests."""

import queue
import socket
import threading
import time

from jaraco.stream import buffer


class RawIRCClient:
    """Talks to an IRC server over a plain socket.

    A reader thread queues every line received (answering PING itself).
    Waiting is done with ``wait_for``, which keeps pumping the bot's
    reactor through ``driver`` so the bot and the client progress together.
    """

    def __init__(self, host: str, port: int, driver=None):
        self.driver = driver
        self.sock = socket.create_connection((host, port), timeout=5)
        self.lines: queue.Queue = queue.Queue()
        self.seen: list[str] = []
        self.nick = None
        self._closed = False
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self):
        buf = buffer.LenientDecodingLineBuffer()
        while not self._closed:
            try:
                data = self.sock.recv(4096)
            except OSError:
                break
            if not data:
                break
            buf.feed(data)
            for line in buf.lines():
                if line.startswith("PING"):
                    self.send_raw("PONG " + line[5:])
                    continue
                self.lines.put(line)

    def send_raw(self, line: str):
        self.sock.sendall(line.encode("utf-8") + b"\r\n")

    def send_bytes(self, data: bytes):
        """Send raw bytes (for invalid UTF-8 tests)."""
        self.sock.sendall(data + b"\r\n")

    def register(self, nick: str, timeout: float = 5.0):
        self.nick = nick
        self.send_raw(f"NICK {nick}")
        self.send_raw(f"USER {nick} 0 * :{nick}")
        self.wait_for(lambda line: f" 001 {nick} " in line, timeout)

    def join(self, channel: str, timeout: float = 5.0):
        self.send_raw(f"JOIN {channel}")
        self.wait_for(
            lambda line: line.startswith(f":{self.nick}!")
            and f"JOIN {channel}" in line.replace(":", "", 2),
            timeout,
        )

    def say(self, target: str, text: str):
        self.send_raw(f"PRIVMSG {target} :{text}")

    def wait_for(self, predicate, timeout: float = 5.0) -> str:
        """Return the first received line matching ``predicate``.

        Lines already consumed by a previous wait are not considered again;
        ``seen`` keeps everything for diagnostics.
        """
        deadline = time.monotonic() + timeout
        while True:
            if self.driver is not None:
                self.driver.pump(0.02)
            try:
                line = self.lines.get(timeout=0.02)
            except queue.Empty:
                line = None
            if line is not None:
                self.seen.append(line)
                if predicate(line):
                    return line
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"{self.nick}: no matching line in {timeout}s; seen: {self.seen}"
                )

    def expect_privmsg(self, from_nick: str, target: str, timeout: float = 5.0) -> str:
        """Wait for a PRIVMSG from ``from_nick`` to ``target``; return its text."""
        prefix = f":{from_nick}!"
        line = self.wait_for(
            lambda l: l.startswith(prefix) and f" PRIVMSG {target} :" in l, timeout
        )
        return line.split(f" PRIVMSG {target} :", 1)[1]

    def quit(self):
        try:
            self.send_raw("QUIT :bye")
        except OSError:
            pass
        self.close()

    def close(self):
        self._closed = True
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
