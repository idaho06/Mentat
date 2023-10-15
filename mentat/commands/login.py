import io
import sys
import logging
import argparse
from mentat.config import Config
from irc.client import ServerConnection


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
    talk_to = None
    if event.type == "privmsg":
        talk_to = nick
    else:
        logging.debug("No login in channels, send a private message")
        return # no login in channels
    
    parser = argparse.ArgumentParser(
        description="Login command",
        prog="login",
        exit_on_error=False,
    )

    parser.add_argument(
        "password",
        type=str,
        help="Password for the bot"
    )

    # Redirect stdout to capture the help text
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    old_stderr = sys.stderr
    sys.stderr = io.StringIO()

    help_text = ""
    login_args = argparse.Namespace()
    try:
        login_args = parser.parse_args(args)
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
    except Exception as exc:
        logging.error("Exception: %s", exc)
    finally:
        help_text += sys.stderr.getvalue()
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    if help_text != "":
        logging.debug("Help text: %s", help_text)
        for help_line in help_text.splitlines():
            connection.privmsg(talk_to, help_line)
        return
    
    if login_args.password != config.irc_admin_password:
        connection.privmsg(talk_to, "Wrong password")
        return
    
    config.set_admin(nick)
    connection.privmsg(talk_to, "Welcome, " + nick)

