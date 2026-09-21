"""Configuration module for Mentat. 
The class stores the initial configuration of the bot and controls the configuration file."""


from datetime import datetime
import shelve
import os
import logging
import argparse
from appdirs import user_config_dir, user_log_dir
import irc.strings
from irc.strings import IRCFoldedCase


class Config:  # pylint: disable=too-many-instance-attributes
    """Class for the configuration of the bot."""

    def __init__(
        self,
        args: argparse.Namespace,
        configdir: str | None = None,
        logdir: str | None = None,
    ):
        """``configdir`` and ``logdir`` default to the platform user dirs;
        tests (or embedders) can point both at a temporary directory."""
        logging.debug("Entering Config class")
        # IRC settings (defaults; overridden by the config file and the
        # command line). Instance attributes, so two Config objects never
        # share the same channel list or admin set.
        self.irc_server = "proxy-irc.chathispano.com"
        self.irc_port = 6667
        self.irc_nick = "Mentat"
        self.irc_realname = "Piter de Vries"
        self.irc_ident = "mentat"
        self.irc_password = ""
        self.irc_channels = ["#mentat", "#malos"]
        self.irc_admin_password = ""
        self.irc_admin_users = set()

        self.configdir = configdir if configdir is not None else user_config_dir("mentat")
        self.logdir = logdir if logdir is not None else user_log_dir("mentat")
        self.start_time = datetime.now()
        self.configfile = f"{self.configdir}/mentat.conf"
        os.makedirs(self.configdir, exist_ok=True)
        # if argument --reset is used, deletes configfile
        if args.reset and os.path.exists(self.configfile):
            os.remove(self.configfile)
            logging.info("Configuration file deleted.")
        self.irc_admin_users.add("idaho")  # Idaho is always admin
        # checks if configfile exists, if not, creates it
        if not os.path.exists(self.configfile):
            # the command line values are stored in the new config file
            self._apply_args(args)
            self.create_configfile(self.configfile)
        else:
            # the command line overrides the stored values for this run
            self.load_configfile(self.configfile)
            self._apply_args(args)
        # after the final value of logdir is known
        os.makedirs(self.logdir, exist_ok=True)

    def _apply_args(self, args: argparse.Namespace):
        """Applies the command line arguments that override the config."""
        if args.password:
            self.irc_password = args.password
        if args.admin_password:
            self.irc_admin_password = args.admin_password
        if args.logdir:
            self.logdir = args.logdir

    def set_admin(self, admin: str):
        """Adds an admin to the admin list."""
        logging.debug("Entering set_admin function. Admin: %s", admin)
        self.irc_admin_users.add(irc.strings.lower(admin))

    def is_admin(self, admin: str) -> bool:
        """Checks if a user is admin."""
        logging.debug("Entering is_admin function. Admin: %s", admin)
        return irc.strings.lower(admin) in self.irc_admin_users

    def has_channel(self, channel: str) -> bool:
        """Checks if a channel is in the channel list (case-insensitive)."""
        return IRCFoldedCase(channel) in self.irc_channels

    def add_channel(self, channel: str):
        """Adds a channel to the channel list, unless it is already there."""
        logging.debug("Entering add_channel function. Channel: %s", channel)
        if not self.has_channel(channel):
            self.irc_channels.append(channel)

    def remove_channel(self, channel: str):
        """Removes a channel from the channel list; no-op if it is not there.

        IRC channel names are case-insensitive and the server may echo them
        with a different case than the one we configured.
        """
        logging.debug("Entering remove_channel function. Channel: %s", channel)
        if self.has_channel(channel):
            self.irc_channels.remove(IRCFoldedCase(channel))

    def redact(self, text: str) -> str:
        """Replaces the configured passwords in ``text`` with asterisks."""
        for secret in (self.irc_password, self.irc_admin_password):
            if secret:
                text = text.replace(secret, "******")
        return text

    def create_configfile(self, configfile: str):
        """Creates the configuration file."""
        logging.debug(
            "Entering create_configfile function. Configfile: %s", configfile)
        with shelve.open(configfile) as db:
            db["IRC_SERVER"] = self.irc_server
            db["IRC_PORT"] = self.irc_port
            db["IRC_NICK"] = self.irc_nick
            db["IRC_REALNAME"] = self.irc_realname
            db["IRC_IDENT"] = self.irc_ident
            db["IRC_PASSWORD"] = self.irc_password
            db["IRC_CHANNELS"] = self.irc_channels
            db["IRC_ADMIN_PASSWORD"] = self.irc_admin_password
            db["LOGDIR"] = self.logdir

    def load_configfile(self, configfile: str):
        """Loads the configuration file."""
        logging.debug(
            "Entering load_configfile function. Configfile: %s", configfile)
        with shelve.open(configfile) as db:
            self.irc_server = db["IRC_SERVER"]
            self.irc_port = db["IRC_PORT"]
            self.irc_nick = db["IRC_NICK"]
            self.irc_realname = db["IRC_REALNAME"]
            self.irc_ident = db["IRC_IDENT"]
            self.irc_password = db["IRC_PASSWORD"]
            self.irc_channels = db["IRC_CHANNELS"]
            self.irc_admin_password = db["IRC_ADMIN_PASSWORD"]
            self.logdir = db["LOGDIR"]
