# -*- coding: utf-8 -*-

"""Helpers shared by the bot commands.

argparse is written for command line programs: on any problem it prints to
stdout/stderr and calls sys.exit(). Inside an IRC bot that would either kill
the process or lose the message. BotArgumentParser captures everything
argparse wants to print so the caller can send it back over IRC instead.
"""

import argparse
import logging
from irc.client import ServerConnection


class _ParserExit(Exception):
    """Raised internally instead of letting argparse call sys.exit()."""


class BotArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never exits and never writes to stdout/stderr.

    Everything argparse would print (help, usage, errors) is collected in
    ``self.output`` as a list of text blocks. argparse funnels every error
    through ``error()`` -> ``print_usage()`` + ``exit()``, so overriding the
    printing and exiting hooks is enough.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output: list[str] = []

    def print_usage(self, file=None):
        self.output.append(self.format_usage())

    def print_help(self, file=None):
        self.output.append(self.format_help())

    def exit(self, status=0, message=None):
        if message:
            self.output.append(message)
        raise _ParserExit()


def parse_or_reply(
    parser: BotArgumentParser, args: list, connection: ServerConnection, target: str
) -> argparse.Namespace | None:
    """Parse ``args`` with ``parser``; on any problem answer the user.

    Returns the namespace on success. Otherwise the help/usage/error text
    is sent to ``target`` and None is returned, so the caller just returns.
    """
    try:
        return parser.parse_args(args)
    except _ParserExit:
        lines = [
            line
            for block in parser.output
            for line in block.splitlines()
            if line.strip()
        ]
        logging.debug("Help text: %s", lines)
        for line in lines:
            connection.privmsg(target, line)
        return None


def reply_target(event) -> str:
    """Where to answer: the user for private messages, the channel otherwise."""
    if event.type == "privmsg":
        return event.source.nick
    return event.target
