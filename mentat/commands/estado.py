# -*- coding: utf-8 -*-

"""Module for the estado command.
   If user is admin, then shows uptime, and list of logged in channels.
   TODO: more info
"""

import io
import sys
import logging
import argparse
from datetime import datetime
from irc.client import ServerConnection
from mentat.config import Config

def estado(connection: ServerConnection, event, args, config: Config):
    """Function to handle the estado command."""
    logging.debug("Entering estado function")
    logging.debug("Event: %s, Args: %s", event, args)

    if not config.is_admin(event.source.nick):
        logging.debug("User is not admin")
        return

    nick = event.source.nick
    talk_to = None
    if event.type == "privmsg":
        talk_to = nick
    else:
        talk_to = event.target

    parser = argparse.ArgumentParser(
        description="Estado command",
        prog="estado",
        exit_on_error=False,
    )

    parser.add_argument(
        "estado",
        type=str,
        help="Estado del bot"
    )

    # Redirect stdout to capture the help text
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    old_stderr = sys.stderr
    sys.stderr = io.StringIO()

    help_text = ""
    estado_args = argparse.Namespace()
    try:
        estado_args = parser.parse_args(args)
    except SystemExit:
        # Get the help text
        help_text = sys.stdout.getvalue()
    except argparse.ArgumentError as exc:
        # Get the help text
        help_text = sys.stdout.getvalue()
        # Add the error message to the help text
        help_text += f"\n{exc}"
    except argparse.ArgumentTypeError as exc:
        # Get the help text
        help_text = sys.stdout.getvalue()
        # Add the error message to the help text
        help_text += f"\n{exc}"
    finally:
        # Restore stdout
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    if help_text != "":
        logging.debug("Help text: %s", help_text)
        for help_line in help_text.splitlines():
            connection.privmsg(talk_to, help_line)
        return
    
    uptime = datetime.now() - config.start_time
    connection.privmsg(talk_to, f"Uptime: {uptime}")
    connection.privmsg(talk_to, f"Channels: {config.irc_channels}")
    connection.privmsg(talk_to, f"Admin users: {config.irc_admin_users}")
    
    return

