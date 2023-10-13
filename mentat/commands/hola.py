# -*- coding: utf-8 -*-
"""Module for the hola command."""

import io
import sys
import logging
import argparse
from irc.client import ServerConnection


def hola(connection: ServerConnection, event, args: list):
    """Function to handle the hola command."""
    logging.debug(
        "Entering hola function: c: %s, e: %s, args: %s", connection, event, args
    )
    nick = event.source.nick
    talk_to = None
    if event.type == "privmsg":
        talk_to = nick
    else:
        talk_to = event.target

    parser = argparse.ArgumentParser(
        description="Comando de saludo",
        prog="hola",
        exit_on_error=False,
    )

    parser.add_argument(
        "-n",
        "--nick",
        dest="nick",
        type=str,
        help="Nick del usuario a saludar",
        required=False,
    )

    # Redirect stdout to capture the help text
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    help_text = ""
    hola_args = argparse.Namespace()
    try:
        hola_args = parser.parse_args(args)
    except SystemExit:
        # Get the help text
        help_text = sys.stdout.getvalue()
    except argparse.ArgumentError as exc:
        # Get the help text
        help_text = sys.stdout.getvalue()
        # Add the error message to the help text
        help_text += f"\n{exc}"
    finally:
        # Restore stdout
        sys.stdout = old_stdout

    if help_text != "":
        logging.debug("Help text: %s", help_text)
        for help_line in help_text.splitlines():
            connection.privmsg(talk_to, help_line)
    else:
        if hola_args.nick:
            connection.privmsg(talk_to, "Hola, " + hola_args.nick)
        else:
            connection.privmsg(talk_to, "Hola, " + nick)
