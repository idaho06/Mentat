# -*- coding: utf-8 -*-

""" Module for the dados command. """

import io
import sys
import logging
import argparse
import random
from irc.client import ServerConnection


def _throw_dice(dice, number):
    logging.debug("Entering _throw_dice function")
    logging.debug("Dice: %s, Number: %s" % (dice, number))
    total = 0
    throws = []
    for i in range(0, number):
        result = random.randint(1, dice)
        logging.debug("Throw %s: %s" % (i, result))
        total += result
        throws.append(result)
    logging.debug("Total: %s" % total)
    return (total, throws)


def dados(connection: ServerConnection, event, args: list):
    """Function to handle the dados command."""
    logging.debug("Entering dados function")
    logging.debug("Event: %s, Args: %s" % (event, args))

    nick = event.source.nick
    talk_to = None
    if event.type == "privmsg":
        talk_to = nick
    else:
        talk_to = event.target

    parser = argparse.ArgumentParser(
        description="Comando de tirar dados",
        prog="dados",
        exit_on_error=False,
    )
    parser.add_argument(
        "-d",
        "--dice",
        help="Tipos de dados a tirar. Por defecto de 6 caras.",
        default=6,
        type=int,
        choices=[6, 8, 10, 12, 20, 100],
    )
    parser.add_argument(
        "-n", "--number", type=int, help="Número de dados a tirar", default=1
    )

    # Redirect stdout to capture the help text
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    help_text = ""
    dados_args = argparse.Namespace()
    try:
        dados_args = parser.parse_args(args)
    except SystemExit:
        help_text = sys.stdout.getvalue()
    except argparse.ArgumentError as exc:
        # Get the help text
        help_text = sys.stdout.getvalue()
        # Add the error message to the help text
        help_text += f"\n{exc}"
    finally:
        sys.stdout = old_stdout

    if help_text != "":
        logging.debug("Help text: %s", help_text)
        for help_line in help_text.splitlines():
            connection.privmsg(talk_to, help_line)
        return

    logging.debug("Dice: %s, Number: %s" % (dados_args.dice, dados_args.number))

    random.seed()

    (total, throws) = _throw_dice(dados_args.dice, dados_args.number)
    connection.privmsg(talk_to, "Total:   %s" % total)
    connection.privmsg(talk_to, "Tiradas: %s" % throws)
    return
