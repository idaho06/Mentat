# -*- coding: utf-8 -*-

""" Module for the dados command. """

import logging
import random
import argparse
from irc.client import ServerConnection
from mentat.commands.common import (
    BotArgumentParser,
    parse_command_args,
    reply_target,
    send_lines,
)

MAX_DICE = 20


def _dice_count(value: str) -> int:
    """argparse type for --number: an int between 1 and MAX_DICE.

    Bounded so the reply always fits in one IRC line (512 bytes) and a
    huge count cannot block the bot for a long time.
    """
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"'{value}' no es un número") from exc
    if not 1 <= number <= MAX_DICE:
        raise argparse.ArgumentTypeError(f"debe estar entre 1 y {MAX_DICE}")
    return number


def _throw_dice(dice, number):
    """Throw the dice."""
    logging.debug("Entering _throw_dice function")
    logging.debug("Dice: %s, Number: %s", dice, number)
    total = 0
    throws = []
    for i in range(0, number):
        result = random.randint(1, dice)
        logging.debug("Throw %s: %s", i, result)
        total += result
        throws.append(result)
    logging.debug("Total: %s", total)
    return (total, throws)


def dados(connection: ServerConnection, event, args: list):
    """Function to handle the dados command."""
    logging.debug("Entering dados function")
    logging.debug("Event: %s, Args: %s", event, args)

    talk_to = reply_target(event)

    parser = BotArgumentParser(
        description="Comando de tirar dados",
        prog="dados",
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
        "-n",
        "--number",
        type=_dice_count,
        help=f"Número de dados a tirar (1-{MAX_DICE})",
        default=1,
    )

    dados_args, help_lines = parse_command_args(parser, args)
    if dados_args is None:
        send_lines(connection, talk_to, help_lines)
        return

    logging.debug("Dice: %s, Number: %s", dados_args.dice, dados_args.number)

    (total, throws) = _throw_dice(dados_args.dice, dados_args.number)
    connection.privmsg(talk_to, f"Total:   {total}")
    connection.privmsg(talk_to, f"Tiradas: {throws}")
    return
