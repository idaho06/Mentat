# -*- coding: utf-8 -*-

""" Module for the observa command: manages the watched-nicks list. """

import logging
from irc.client import ServerConnection
from mentat.config import Config, MAX_OBSERVA_NICKS
from mentat.commands.common import BotArgumentParser, parse_or_reply, reply_target


def _nick_parser(subcmd: str) -> BotArgumentParser:
    parser = BotArgumentParser(
        description=f"observa {subcmd}",
        prog=f"observa {subcmd}",
    )
    parser.add_argument("nick", type=str, help="Nick a vigilar")
    return parser


def observa(connection: ServerConnection, event, args, config: Config):
    """Function to handle the observa command."""
    logging.debug("Entering observa function")
    logging.debug("Event: %s, Args: %s", event, args)

    if not config.is_admin(event.source.nick):
        logging.debug("User is not admin")
        return

    talk_to = reply_target(event)

    if args and args[0] in ("-h", "--help"):
        parser = BotArgumentParser(
            description="Gestiona la lista de nicks vigilados",
            prog="observa",
            epilog="Subcomandos: pon <nick>, quita <nick>, lista",
        )
        parse_or_reply(parser, args, connection, talk_to)
        return

    if not args:
        online = sorted(n for n in config.observa_nicks if config.is_watched_nick_online(n))
        connection.privmsg(
            talk_to,
            ", ".join(online) if online else "Ningún nick vigilado está conectado",
        )
        return

    if args[0] == "pon":
        pon_args = parse_or_reply(_nick_parser("pon"), args[1:], connection, talk_to)
        if pon_args is None:
            return
        if not config.add_watched_nick(pon_args.nick):
            connection.privmsg(
                talk_to,
                f"Ya se vigilan {MAX_OBSERVA_NICKS} nicks (máximo)",
            )
            return
        connection.send_raw(f"WATCH +{pon_args.nick}")
        return

    if args[0] == "quita":
        quita_args = parse_or_reply(_nick_parser("quita"), args[1:], connection, talk_to)
        if quita_args is None:
            return
        config.remove_watched_nick(quita_args.nick)
        connection.send_raw(f"WATCH -{quita_args.nick}")
        return

    if args[0] == "lista":
        connection.privmsg(
            talk_to,
            ", ".join(config.observa_nicks) if config.observa_nicks else "No hay nicks vigilados",
        )
        return

    connection.privmsg(talk_to, f"Subcomando desconocido: {args[0]}")
