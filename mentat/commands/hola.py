# -*- coding: utf-8 -*-
"""Module for the hola command."""

import logging
from irc.client import ServerConnection
from mentat.config import Config
from mentat.commands.common import BotArgumentParser, parse_or_reply, reply_target


def hola(connection: ServerConnection, event, args: list, _config: Config):
    """Function to handle the hola command."""
    logging.debug(
        "Entering hola function: c: %s, e: %s, args: %s", connection, event, args
    )
    nick = event.source.nick
    talk_to = reply_target(event)

    parser = BotArgumentParser(
        description="Comando de saludo",
        prog="hola",
    )

    parser.add_argument(
        "-n",
        "--nick",
        dest="nick",
        type=str,
        help="Nick del usuario a saludar",
        required=False,
    )

    hola_args = parse_or_reply(parser, args, connection, talk_to)
    if hola_args is None:
        return

    connection.privmsg(talk_to, "Hola, " + (hola_args.nick or nick))
