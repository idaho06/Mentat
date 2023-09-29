import logging
from mentat.config import Config


class Logger(object):
    def __init__(self, config: Config):
        logging.debug("Entering Logger class")
        self.config = config

    def pubmsg(self, e):
        logging.debug(f"Entering pubmsg function: e: {e}")
        logging.info(
            f"Channel: {e.target} | User: {e.source.nick} | Message: {e.arguments[0]}"
        )

    def privmsg(self, e):
        logging.debug(f"Entering privmsg function: e: {e}")
        logging.info(f"User: {e.source.nick} | Message: {e.arguments[0]}")
