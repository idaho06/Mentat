#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Main module for Mentat. This module gets the arguments from the command line,
configures the logging and starts the bot."""

import sys
import logging
import argparse
from mentat.config import Config
from mentat.bot import Mentat
from mentat.logger import SecretFilter

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def build_parser() -> argparse.ArgumentParser:
    """Builds the command line parser."""
    parser = argparse.ArgumentParser(
        description="Mentat, an IRC bot.",
        epilog="Made by César (Idaho06) Rodríguez Moreno.",
    )
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
    return parser


def configure_logging(args: argparse.Namespace):
    """Configures the root logger from the command line arguments."""
    level = LOG_LEVELS.get(args.debug, logging.WARNING)
    filename = None if args.erroroutput == "stderr" else args.erroroutput
    logging.basicConfig(
        level=level,
        filename=filename,
        format="%(asctime)s %(levelname)s: %(funcName)s: %(message)s",
    )
    logging.info("Logging level set to %s", logging.getLevelName(level))


def main(argv: list[str] | None = None) -> int:
    """Main function for Mentat. ``argv`` defaults to the process arguments."""
    args = build_parser().parse_args(argv)
    configure_logging(args)
    logging.debug("Entering Main function")
    logging.info("This is Mentat, an IRC bot.")
    config = Config(args)
    # on the handler, not the logger, so records propagated from the irc
    # library (which logs every raw line at DEBUG) are redacted too
    for handler in logging.getLogger().handlers:
        handler.addFilter(SecretFilter(config))
    logging.debug("Args: %s", args)
    mentat = Mentat(config)
    if args.create_config_and_exit:
        return 0
    mentat.start()

    return 0


if __name__ == "__main__":
    sys.exit(main())
