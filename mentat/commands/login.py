import logging
from irc.client import ServerConnection
from mentat.config import Config
from mentat.commands.common import (
    BotArgumentParser,
    parse_command_args,
    reply_target,
    send_lines,
)


def login(connection: ServerConnection, event, args, config: Config):
    """Login to the bot"""
    logging.debug(
        "Entering login function: c: %s, e: %s, args: %s, config: %s",
        connection,
        event,
        args,
        config,
    )
    nick = event.source.nick
    if event.type != "privmsg":
        logging.debug("No login in channels, send a private message")
        return
    talk_to = reply_target(event)

    parser = BotArgumentParser(
        description="Login command",
        prog="login",
    )

    parser.add_argument(
        "password",
        type=str,
        help="Password for the bot"
    )

    login_args, help_lines = parse_command_args(parser, args)
    if login_args is None:
        send_lines(connection, talk_to, help_lines)
        return

    if login_args.password != config.irc_admin_password:
        connection.privmsg(talk_to, "Wrong password")
        return

    config.set_admin(nick)
    connection.privmsg(talk_to, "Welcome, " + nick)
