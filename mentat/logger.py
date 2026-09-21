"""Module for logging messages to files."""

import logging
from datetime import datetime
from mentat.config import Config


class SecretFilter(logging.Filter):  # pylint: disable=too-few-public-methods
    """Redacts the configured passwords from every log record it sees.

    Meant for the root handler, so it covers the bot's own logs and the
    irc library's (which logs "NICK nick:password" and the login command
    verbatim at DEBUG level) without any per-call-site care.
    """

    def __init__(self, config: Config):
        super().__init__()
        self.config = config

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        cleaned = self.config.redact(message)
        if cleaned != message:
            record.msg = cleaned
            record.args = ()
        return True


class Logger:
    """Class for logging messages to files."""

    def __init__(self, config: Config):
        """Constructor for the Logger class."""
        logging.debug("Entering Logger class")
        self.config = config

    def _append(self, filename: str, line: str):
        """Appends a timestamped line to ``filename`` in the log dir."""
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        path = f"{self.config.logdir}/{filename}"
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"{time} {self.config.redact(line)}\n")

    def _append_raw(self, filename: str, text: str):
        """Appends ``text`` verbatim: no timestamp prefix, no trailing newline."""
        path = f"{self.config.logdir}/{filename}"
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            f.write(self.config.redact(text))

    @staticmethod
    def _channel_file(channel: str) -> str:
        """Log file name for a channel."""
        return channel.replace("#", "channel_") + ".log"

    def pubmsg(self, event):
        """Stores messages from the channels."""
        logging.debug("Entering pubmsg function: e: %s", event)
        logging.debug(
            "Channel: %s | User: %s | Message: %s",
            event.target,
            event.source.nick,
            event.arguments[0],
        )
        self._append(
            self._channel_file(event.target),
            f"::: <{event.source.nick}> {event.arguments[0]}",
        )

    def join_part(self, event):
        """Stores join and part messages from the channels."""
        logging.debug("Entering join function: e: %s", event)
        logging.info(
            "Channel: %s | User: %s | Action: %s",
            event.target,
            event.source.nick,
            event.type,
        )
        action = event.type
        tag = '==='
        if action == 'join':
            tag = '==>'
        elif action == 'part':
            tag = '<=='
        self._append(
            self._channel_file(event.target),
            f"{tag} {event.source.nick} {action}ed the channel",
        )

    def privmsg(self, event):
        """Stores messages from private messages."""
        logging.debug("Entering privmsg function: e: %s", event)
        nick = event.source.nick
        logging.info("User: %s | Message: %s", nick, event.arguments[0])
        self._append(f"nick_{nick}.log", event.arguments[0])

    def action(self, event):
        """Stores actions from the channels."""
        logging.debug("Entering action function: e: %s", event)
        logging.info(
            "Channel: %s | User: %s | Action: %s",
            event.target,
            event.source.nick,
            event.arguments[0],
        )
        self._append(
            self._channel_file(event.target),
            f"-*- {event.source.nick} {event.arguments[0]}",
        )

    def kick(self, event):
        """Stores kick messages from the channels."""
        logging.debug("Entering kick function: e: %s", event)
        logging.info(
            "Channel: %s | User: %s | Action: %s",
            event.target,
            event.source.nick,
            event.arguments[0],
        )
        kicked = event.arguments[0]
        reason = event.arguments[1] if len(event.arguments) > 1 else ''
        self._append(
            self._channel_file(event.target),
            f"<=* {event.source.nick} has kicked {kicked}: {reason}",
        )

    def nick(self, event):
        """Stores nick changes."""
        logging.debug("Entering nick function: e: %s", event)
        logging.info(
            "nick %s changes nick to: %s",
            event.source.nick,
            event.target,
        )
        self._append(
            "nick_changes.log",
            f"*** {event.source.nick} is now known as {event.target}",
        )

    def umode(self, event):
        """Stores self (user) mode changes."""
        logging.debug("Entering umode function: e: %s", event)
        nick = event.source.nick if event.source else "unknown"
        action = event.arguments[0] if event.arguments else ""
        logging.info("User: %s | Mode: %s", nick, action)
        self._append("mode_changes.log", f"*** {nick} sets mode: {action}")

    def mode(self, event):
        """Stores channel mode changes."""
        logging.debug("Entering mode function: e: %s", event)
        nick = event.source.nick if event.source else "unknown"
        # the mode string plus its parameters, e.g. "+o idaho"
        action = " ".join(event.arguments)
        logging.info("Channel: %s | User: %s | Mode: %s", event.target, nick, action)
        self._append(
            self._channel_file(event.target), f"*** {nick} sets mode: {action}"
        )

    def watched_pubmsg(self, event):
        """Marks a channel message from a watched nick with a single dot."""
        self._append_raw(f"nick_{event.source.nick}.log", ".")

    def watched_join_part(self, event):
        """Stores join and part events for a watched nick, in its own file."""
        action = event.type
        tag = '==='
        if action == 'join':
            tag = '==>'
        elif action == 'part':
            tag = '<=='
        self._append(
            f"nick_{event.source.nick}.log",
            f"{tag} {event.source.nick} {action}ed the channel",
        )

    def watched_action(self, event):
        """Stores a CTCP action from a watched nick in its own file."""
        self._append(
            f"nick_{event.source.nick}.log",
            f"-*- {event.source.nick} {event.arguments[0]}",
        )

    def watched_kick(self, event, nick: str):
        """Stores a kick event in ``nick``'s own file (kicker or kicked)."""
        kicked = event.arguments[0]
        reason = event.arguments[1] if len(event.arguments) > 1 else ''
        self._append(
            f"nick_{nick}.log",
            f"<=* {event.source.nick} has kicked {kicked}: {reason}",
        )

    def watched_mode(self, event, nick: str):
        """Stores a channel mode change affecting a watched nick.

        Doesn't try to align flag letters with parameters positionally for
        multi-target lines (e.g. "+ov bob alice") — the whole line is logged
        whenever the watched nick appears anywhere among the parameters.
        """
        action = " ".join(event.arguments)
        self._append(
            f"nick_{nick}.log", f"*** {event.source.nick} sets mode: {action}"
        )

    def watched_nick(self, event):
        """Stores a rename of a watched nick in its (pre-rename) own file.

        Known limitation: this does not move the WATCH subscription or the
        Config.observa_nicks entry to the new nick — that stays a separate,
        explicit "observa quita/pon" step for now.
        """
        self._append(
            f"nick_{event.source.nick}.log",
            f"*** {event.source.nick} is now known as {event.target}",
        )

    def watched_away(self, event):
        """Stores an away-notify status change for a watched nick."""
        nick = event.source.nick
        if event.target:
            self._append(f"nick_{nick}.log", f"*** {nick} is away: {event.target}")
        else:
            self._append(f"nick_{nick}.log", f"*** {nick} is back")

    def watched_chghost(self, event):
        """Stores a host change (CHGHOST) for a watched nick."""
        nick = event.source.nick
        new_ident = event.target
        new_host = event.arguments[0] if event.arguments else ""
        self._append(
            f"nick_{nick}.log", f"*** {nick} changed host to {new_ident}@{new_host}"
        )

    def quit(self, event, channels):
        """Stores quit messages in every channel the nick was in."""
        logging.debug("Entering quit function: e: %s", event)
        nick = event.source.nick
        reason = event.arguments[0] if event.arguments else ""
        logging.info("User: %s | Quit message: %s", nick, reason)
        for channel in channels:
            self._append(
                self._channel_file(channel), f"<<< {nick} has quit: {reason}"
            )
