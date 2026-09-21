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
    ``self.output`` as a list of text blocks.
    """

    def __init__(self, *args, **kwargs):
        kwargs["exit_on_error"] = False
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

    def error(self, message):
        self.output.append(self.format_usage())
        self.output.append(f"{self.prog}: error: {message}")
        raise _ParserExit()


def parse_command_args(
    parser: BotArgumentParser, args: list
) -> tuple[argparse.Namespace | None, list[str]]:
    """Parse ``args`` with ``parser`` without ever raising or exiting.

    Returns ``(namespace, [])`` on success, or ``(None, lines)`` where
    ``lines`` is the help/usage/error text to send back to the user.
    """
    namespace = None
    try:
        namespace = parser.parse_args(args)
    except _ParserExit:
        pass
    except argparse.ArgumentError as exc:
        parser.output.append(parser.format_usage())
        parser.output.append(f"{parser.prog}: error: {exc}")
    lines = [
        line
        for block in parser.output
        for line in block.splitlines()
        if line.strip()
    ]
    if lines:
        logging.debug("Help text: %s", lines)
        return None, lines
    return namespace, []


def reply_target(event) -> str:
    """Where to answer: the user for private messages, the channel otherwise."""
    if event.type == "privmsg":
        return event.source.nick
    return event.target


def send_lines(connection: ServerConnection, target: str, lines: list):
    """Send each line as a separate PRIVMSG."""
    for line in lines:
        connection.privmsg(target, line)
