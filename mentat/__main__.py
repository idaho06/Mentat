#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Main module for Mentat. This module gets the arguments from the command line,
configures the logging and starts the bot."""

import sys
import logging
import argparse
from mentat.config import Config
from mentat.bot import Mentat


def main(args: argparse.Namespace) -> int:
    """Main function for Mentat."""
    logging.debug("Entering Main function")
    logging.info("This is Mentat, an IRC bot.")
    logging.debug("Args: %s", args)
    config = Config(args)
    mentat = Mentat(config)
    if args.create_config_and_exit:
        return 0
    mentat.start()

    return 0


parser = argparse.ArgumentParser(
    description="Mentat, an IRC bot.",
    epilog="Made by César (Idaho06) Rodríguez Moreno.",
)
# parser.add_argument("echo", help="echo the string you use here")
# parser.add_argument("-db", "--database",
#                     help="Database to be used.", default="/tmp/termgame.sqlite3")
parser.add_argument(
    "-p", "--password", help="Password for the nick of the bot.", default=""
)
parser.add_argument(
    "-a", "--admin-password", help="Password for the admin commands.", default=""
)
parser.add_argument(
    "-l", "--logdir", help="Path for the channel and private logs.", default=""
)
parser.add_argument(
    "--reset", help="Reset the configuration file.", action="store_true"
)
parser.add_argument(
    "--create-config-and-exit",
    help="Create the configuration file and exit.",
    action="store_true",
)
parser.add_argument(
    "-d",
    "--debug",
    help="Debug level: DEBUG, INFO, WARNING, ERROR or CRITICAL",
    default="WARNING",
)
parser.add_argument(
    "-o",
    "--erroroutput",
    help="File of error output. Default is stderr.",
    default="stderr",
)

main_args = parser.parse_args()


LOG_LEVEL = logging.WARNING
LOG_OUTPUT = None


if main_args.debug == "DEBUG":
    LOG_LEVEL = logging.DEBUG
if main_args.debug == "INFO":
    LOG_LEVEL = logging.INFO
if main_args.debug == "ERROR":
    LOG_LEVEL = logging.ERROR
if main_args.debug == "CRITICAL":
    LOG_LEVEL = logging.CRITICAL


if main_args.erroroutput != "stderr":
    LOG_OUTPUT = main_args.erroroutput

logging.basicConfig(
    level=LOG_LEVEL,
    filename=LOG_OUTPUT,
    format="%(asctime)s %(levelname)s: %(funcName)s: %(message)s",
)

logging.info("Logging level set to %s", logging.getLevelName(LOG_LEVEL))

# logging.info("Configuring database to %s" % args.database)


sys.exit(main(main_args))
