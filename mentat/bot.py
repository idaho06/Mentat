import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr, ServerConnection
from mentat.config import Config
import logging


class Mentat(irc.bot.SingleServerIRCBot):
    def __init__(self, config: Config):
        self.config = config
        # self.server = self.config.irc_server
        # self.port = self.config.irc_port
        # self.nickname = self.config.irc_nick
        # self.realname = self.config.irc_realname
        # self.ident = self.config.irc_ident
        # self.password = self.config.irc_password
        # self.channels = self.config.irc_channels

        irc.bot.SingleServerIRCBot.__init__(
            self,
            [(self.config.irc_server, self.config.irc_port)],
            self.config.irc_nick,
            self.config.irc_realname,
        )

    def on_nicknameinuse(self, c: ServerConnection, e):
        logging.debug(f"Entering on_nicknameinuse function: c: {c}, e: {e}")
        # check if message contains f"El nick está registrado, tienes que indicar la contraseña para usarlo: /nick {c.get_nickname()}:contraseña"
        # if so, send password
        if e.arguments[0].startswith(
            f"El nick está registrado, tienes que indicar la contraseña para usarlo: /nick {c.get_nickname()}:contraseña"
        ):
            logging.warning(f"Nickname registered. Sending password.")
            c.nick(f"{c.get_nickname()}:{self.config.irc_password}")
        else:
            c.nick(c.get_nickname() + "_")
            logging.warning(f"Nickname in use. Changing to {c.get_nickname()}_")

    def on_welcome(self, c, e):
        logging.debug(f"Entering on_welcome function: c: {c}, e: {e}")
        # for channel in self.channels:
        #     c.join(channel)
        #     logging.info(f"Joining channel: {channel}")

    def on_endofmotd(self, c: ServerConnection, e):
        logging.debug(f"Entering on_endofmotd function: c: {c}, e: {e}")
        logging.info(f"End of MOTD received. Joining channels: {self.channels}")
        for channel in self.config.irc_channels:
            logging.info(f"Joining channel: {channel}")
            c.join(channel)
            logging.debug(f"Joined channel: {channel}")

    def on_pubmsg(self, c, e):
        logging.debug(f"Entering on_pubmsg function: c: {c}, e: {e}")
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(
            self.connection.get_nickname()
        ):
            self.do_command(e, a[1].strip())
        return

    def on_privmsg(self, c, e):
        logging.debug(f"Entering on_privmsg function: c: {c}, e: {e}")
        self.do_command(e, e.arguments[0])
        return

    def on_dccmsg(self, c, e):
        # non-chat DCC messages are raw bytes; decode as text
        text = e.arguments[0].decode("utf-8")
        c.privmsg("You said: " + text)

    def on_dccchat(self, c, e):
        if len(e.arguments) != 2:
            return
        args = e.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def do_command(self, e, cmd):
        logging.debug(f"Entering do_command function: e: {e}, cmd: {cmd}")
        nick = e.source.nick
        c = self.connection
        c.privmsg(nick, "I was told to " + cmd)
        return
