import logging
from mentat.config import Config
from datetime import datetime


class Logger(object):
    def __init__(self, config: Config):
        logging.debug("Entering Logger class")
        self.config = config

    def pubmsg(self, e):
        logging.debug(f"Entering pubmsg function: e: {e}")
        logging.info(
            f"Channel: {e.target} | User: {e.source.nick} | Message: {e.arguments[0]}"
        )
        channel = e.target
        channel = channel.replace("#", "channel_")
        filename = f"{self.config.logdir}/{channel}.log"
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(filename, "a") as f:
            f.write(f"{time} <{e.source.nick}> {e.arguments[0]}\n")

    def privmsg(self, e):
        logging.debug(f"Entering privmsg function: e: {e}")
        logging.info(f"User: {e.source.nick} | Message: {e.arguments[0]}")
        nick = e.source.nick
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"{self.config.logdir}/nick_{nick}.log"
        with open(filename, "a") as f:
            f.write(f"{time} {e.arguments[0]}\n")
