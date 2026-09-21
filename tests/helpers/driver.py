"""Drives a Mentat bot from a test without its blocking start() loop."""

import time
from collections import deque

import irc.bot
from mentat.bot import Mentat
from mentat.status import Status


class NoReconnect(irc.bot.ReconnectStrategy):
    """Reconnect strategy that never reconnects.

    The library's default ExponentialBackoff is a single shared instance
    whose state leaks between bots, and a reconnect scheduled from one test
    would fire in the next.
    """

    def run(self, bot):
        pass


class BotDriver:
    """Connects the bot and pumps its reactor until a condition holds.

    ``Mentat.start()`` calls the blocking ``process_forever``; the driver
    reproduces its two other lines (status transition and connect) and
    then lets tests advance the reactor one ``process_once`` at a time.
    """

    def __init__(self, bot: Mentat, keep_raw: int = 50):
        self.bot = bot
        self.raw_lines: deque = deque(maxlen=keep_raw)
        bot.reactor.add_global_handler(
            "all_raw_messages",
            lambda _c, event: self.raw_lines.append(event.arguments[0]),
            -50,
        )

    def start(self):
        """Same as Mentat.start without process_forever."""
        self.bot.status.transition("connect")
        self.bot._connect()  # pylint: disable=protected-access

    def pump(self, timeout: float = 0.05):
        """Process pending IRC input once."""
        self.bot.reactor.process_once(timeout)

    def run_until(self, predicate, timeout: float = 5.0, step: float = 0.05):
        """Pump the reactor until ``predicate()`` is true or ``timeout`` expires."""
        deadline = time.monotonic() + timeout
        while True:
            self.pump(step)
            if predicate():
                return
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"condition not met in {timeout}s; last raw lines: "
                    f"{list(self.raw_lines)}"
                )

    def wait_status(self, status: str, timeout: float = 5.0):
        self.run_until(lambda: self.bot.status.get_status() == status, timeout)

    def wait_joined(self, channel: str, timeout: float = 5.0):
        self.run_until(lambda: channel in self.bot.channels, timeout)

    def connect_and_join(self, channel: str = "#mentat"):
        """Start the bot and wait until it is connected and in ``channel``."""
        self.start()
        self.wait_status(Status.CONNECTED)
        self.wait_joined(channel)

    def inject_line(self, raw: str):
        """Feed a raw server line to the bot as if the server had sent it.

        For events the in-process server cannot produce (KICK, MODE, the
        Spanish 433). Goes through the library's parser, so the library's
        own channel tracking and Mentat's on_* handlers both run.
        """
        self.bot.connection._process_line(raw)  # pylint: disable=protected-access
