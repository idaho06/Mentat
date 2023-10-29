"""Module for logging messages to files."""

import logging
from datetime import datetime
from mentat.config import Config

# import irc.strings


class Logger(object):
    """Class for logging messages to files."""

    def __init__(self, config: Config):
        """Constructor for the Logger class."""
        logging.debug("Entering Logger class")
        self.config = config

    def pubmsg(self, event):
        """Stores messages from the channels."""
        logging.debug("Entering pubmsg function: e: %s", event)
        logging.debug(
            "Channel: %s | User: %s | Message: %s",
            event.target,
            event.source.nick,
            event.arguments[0],
        )
        channel = event.target
        channel = channel.replace("#", "channel_")
        filename = f"{self.config.logdir}/{channel}.log"
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(filename, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"{time} PUBMSG <{event.source.nick}> {event.arguments[0]}\n")
    
    def join_part(self, event):
        """Stores join and part messages from the channels."""
        logging.debug("Entering join function: e: %s", event)
        logging.info(
            "Channel: %s | User: %s | Action: %s",
            event.target,
            event.source.nick,
            event.type,
        )
        channel = event.target
        channel = channel.replace("#", "channel_")
        filename = f"{self.config.logdir}/{channel}.log"
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        action = event.type
        with open(filename, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"{time} * {event.source.nick} {action}ed the channel\n")

    def privmsg(self, event):
        """Stores messages from private messages."""
        logging.debug("Entering privmsg function: e: %s", event)
        logging.info("User: %s | Message: %s", event.source.nick, event.arguments[0])
        nick = event.source.nick
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"{self.config.logdir}/nick_{nick}.log"
        with open(filename, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"{time} {event.arguments[0]}\n")
