# -*- coding: utf-8 -*-

""" Module for the part command. """

import io
import sys
import logging
import argparse
from irc.client import ServerConnection
from mentat.config import Config


def part(connection: ServerConnection, event, args, config: Config):
    """Function to handle the part command."""
    logging.debug("Entering part function")
    logging.debug("Event: %s, Args: %s", event, args)

    if not config.is_admin(event.source.nick):
        return

    nick = event.source.nick
    talk_to = None
    if event.type == "privmsg":
        talk_to = nick
    else:
        talk_to = event.target

    parser = argparse.ArgumentParser(
        description="Part command",
        prog="part",
        exit_on_error=False,
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

    # Redirect stdout to capture the help text
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    old_stderr = sys.stderr
    sys.stderr = io.StringIO()

    help_text = ""
    part_args = argparse.Namespace()
    try:
        part_args = parser.parse_args(args)
    except SystemExit:
        # Get the help text
        help_text = sys.stdout.getvalue()
    except argparse.ArgumentError as exc:
        # Get the help text
        help_text = sys.stdout.getvalue()
        # Add the error message to the help text
        help_text += f"\n{exc}"
    except argparse.ArgumentTypeError as exc:
        logging.error("Exception: %s", exc)
        # Get the help text
        help_text = sys.stdout.getvalue()
        # Add the error message to the help text
    finally:
        help_text += sys.stderr.getvalue()
        # Restore stdout
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    if help_text != "":
        logging.debug("Help text: %s", help_text)
        for help_line in help_text.splitlines():
            connection.privmsg(talk_to, help_line)
        return

    connection.part(part_args.channel, part_args.reason)