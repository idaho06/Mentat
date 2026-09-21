# -*- coding: utf-8 -*-

""" Module for the join command. """

import logging
from irc.client import ServerConnection
from mentat.config import Config
from mentat.commands.common import (
    BotArgumentParser,
    parse_command_args,
    reply_target,
    send_lines,
)


def join(connection: ServerConnection, event, args, config: Config):
    """Function to handle the join command."""
    logging.debug("Entering join function")
    logging.debug("Event: %s, Args: %s", event, args)

    if not config.is_admin(event.source.nick):
        logging.debug("User is not admin")
        return

    talk_to = reply_target(event)

    parser = BotArgumentParser(
        description="Join command",
        prog="join",
    )

    parser.add_argument(
        "channel",
        type=str,
        help="Channel to join"
    )

    join_args, help_lines = parse_command_args(parser, args)
    if join_args is None:
        send_lines(connection, talk_to, help_lines)
        return

    connection.join(join_args.channel)
    config.irc_channels.append(join_args.channel)
