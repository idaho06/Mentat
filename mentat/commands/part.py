# -*- coding: utf-8 -*-

""" Module for the part command. """

import logging
from irc.client import ServerConnection
from mentat.config import Config
from mentat.commands.common import BotArgumentParser, parse_or_reply, reply_target


def part(connection: ServerConnection, event, args, config: Config):
    """Function to handle the part command."""
    logging.debug("Entering part function")
    logging.debug("Event: %s, Args: %s", event, args)

    if not config.is_admin(event.source.nick):
        return

    talk_to = reply_target(event)

    parser = BotArgumentParser(
        description="Part command",
        prog="part",
    )

    parser.add_argument(
        "channel",
        type=str,
        help="Channel to part"
    )

    parser.add_argument(
        "-r",
        "--reason",
        type=str,
        help="Reason for parting",
        default="Leaving"
    )

    part_args = parse_or_reply(parser, args, connection, talk_to)
    if part_args is None:
        return

    connection.part(part_args.channel, part_args.reason)
    config.remove_channel(part_args.channel)
