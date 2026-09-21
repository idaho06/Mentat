# -*- coding: utf-8 -*-

"""Module for the estado command.
   If user is admin, then shows uptime, and list of logged in channels.
   TODO: more info
"""

import logging
from datetime import datetime
from irc.client import ServerConnection
from mentat.config import Config
from mentat.commands.common import BotArgumentParser, parse_or_reply, reply_target


def estado(connection: ServerConnection, event, args, config: Config):
    """Function to handle the estado command."""
    logging.debug("Entering estado function")
    logging.debug("Event: %s, Args: %s", event, args)

    if not config.is_admin(event.source.nick):
        logging.debug("User is not admin")
        return

    talk_to = reply_target(event)

    parser = BotArgumentParser(
        description="Estado command",
        prog="estado",
    )

    if parse_or_reply(parser, args, connection, talk_to) is None:
        return

    uptime = datetime.now() - config.start_time
    connection.privmsg(talk_to, f"Uptime: {uptime}")
    connection.privmsg(talk_to, f"Channels: {config.irc_channels}")
    connection.privmsg(talk_to, f"Admin users: {config.irc_admin_users}")
