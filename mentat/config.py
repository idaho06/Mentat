from appdirs import user_config_dir, user_log_dir
import shelve
import os
import logging
import argparse


class Config(object):
    # ...
    # IRC settings
    irc_server = "proxy-irc.chathispano.com"
    irc_port = 6667
    irc_nick = "Mentat"
    irc_realname = "Piter de Vries"
    irc_ident = "mentat"
    irc_password = ""
    irc_channels = ["#mentat", "#madrid"]
    irc_admin_password = ""
    irc_admin_users = ["Idaho"]

    def __init__(self, args: argparse.Namespace):
        logging.debug("Entering Config class")
        self.configdir = user_config_dir("mentat")
        self.logdir = user_log_dir("mentat")
        if args.logdir:
            self.logdir = args.logdir
        self.configfile = f"{self.configdir}/mentat.conf"
        # checks if configdir exists, if not, creates it
        if not os.path.exists(self.configdir):
            os.makedirs(self.configdir)
        # checks if logdir exists, if not, creates it
        if not os.path.exists(self.logdir):
            os.makedirs(self.logdir)
        # if argument --reset is used, deletes configfile
        if args.reset and os.path.exists(self.configfile):
            os.remove(self.configfile)
            logging.info("Configuration file deleted.")
        # if argument --password is used, sets irc_password
        if args.password:
            self.irc_password = args.password
        if args.admin_password:
            self.irc_admin_password = args.admin_password
        # checks if configfile exists, if not, creates it
        if not os.path.exists(self.configfile):
            # open(self.configfile, "a").close()
            self.create_configfile(self.configfile)
        else:
            self.load_configfile(self.configfile)

    def create_configfile(self, configfile: str):
        logging.debug(f"Entering create_configfile function. Configfile: {configfile}")
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
        logging.debug(f"Entering load_configfile function. Configfile: {configfile}")
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
