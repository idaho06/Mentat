"""Module for the login command."""

import logging
from irc.client import ServerConnection
from mentat.config import Config
from mentat.commands.common import BotArgumentParser, parse_or_reply


def login(connection: ServerConnection, event, args, config: Config):
    """Login to the bot"""
    logging.debug("Entering login function: e: %s, args: %s", event, args)
    nick = event.source.nick
    if event.type != "privmsg":
        logging.debug("No login in channels, send a private message")
        return

    parser = BotArgumentParser(
        description="Login command",
        prog="login",
    )

    parser.add_argument(
        "password",
        type=str,
        help="Password for the bot"
    )

    # the reply always goes to the user: login only works in private
    login_args = parse_or_reply(parser, args, connection, nick)
    if login_args is None:
        return

    if login_args.password != config.irc_admin_password:
        connection.privmsg(nick, "Wrong password")
        return

    config.set_admin(nick)
    connection.privmsg(nick, "Welcome, " + nick)
