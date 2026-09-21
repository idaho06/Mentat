# -*- coding: utf-8 -*-

""" Module for the op command. """

import logging
from irc.client import ServerConnection
from mentat.config import Config
from mentat.commands.common import reply_target


def op(connection: ServerConnection, event, args: list, config: Config):
    """Gives channel operator status.

    ``op`` in a channel ops the caller; ``op <nick> [channel]`` ops ``nick``
    in ``channel`` (the current one by default).
    """
    logging.debug("Entering op function: e: %s, args: %s", event, args)
    nick = event.source.nick
    if not config.is_admin(nick):
        return
    talk_to = reply_target(event)

    if 1 <= len(args) <= 2:
        nick_to_op = args[0]
        channel = args[1] if len(args) > 1 else talk_to
        logging.debug("Channel: %s, Nick to op: %s", channel, nick_to_op)
        connection.mode(channel, f"+o {nick_to_op}")
    elif not args and event.type != "privmsg":
        connection.mode(talk_to, f"+o {nick}")
