#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import argparse
from mentat.config import Config
from mentat.bot import Mentat


def main(args: argparse.Namespace):
    logging.debug("Entering Main function")
    logging.info("This is Mentat, an IRC bot.")
    logging.debug(f"Args: {args}")
    config = Config(args)
    mentat = Mentat(config)
    mentat.start()

    return 0


parser = argparse.ArgumentParser(
    description="Mentat, an IRC bot.",
    epilog="Made by César (Idaho06) Rodríguez Moreno.",
)
# parser.add_argument("echo", help="echo the string you use here")
# parser.add_argument("-db", "--database", help="Database to be used.", default="/tmp/termgame.sqlite3")
parser.add_argument(
    "-p", "--password", help="Password for the nick of the bot.", default=""
)
parser.add_argument(
    "--reset", help="Reset the configuration file.", action="store_true"
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

args = parser.parse_args()


loglevel = logging.WARNING
logoutput = None


if args.debug == "DEBUG":
    loglevel = logging.DEBUG
if args.debug == "INFO":
    loglevel = logging.INFO
if args.debug == "ERROR":
    loglevel = logging.ERROR
if args.debug == "CRITICAL":
    loglevel = logging.CRITICAL


if args.erroroutput != "stderr":
    logoutput = args.erroroutput

logging.basicConfig(
    level=loglevel,
    filename=logoutput,
    format="%(asctime)s %(levelname)s: %(funcName)s: %(message)s",
)

logging.info(f"Logging level set to {logging.getLevelName(loglevel)}.")

# logging.info("Configuring database to %s" % args.database)


exit(main(args))
