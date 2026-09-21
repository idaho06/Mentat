# -*- coding: utf-8 -*-
"""Module for the hola command."""

import logging
from irc.client import ServerConnection
from mentat.commands.common import (
    BotArgumentParser,
    parse_command_args,
    reply_target,
    send_lines,
)


def hola(connection: ServerConnection, event, args: list):
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

    hola_args, help_lines = parse_command_args(parser, args)
    if hola_args is None:
        send_lines(connection, talk_to, help_lines)
        return

    if hola_args.nick:
        connection.privmsg(talk_to, "Hola, " + hola_args.nick)
    else:
        connection.privmsg(talk_to, "Hola, " + nick)
