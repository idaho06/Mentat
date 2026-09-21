"""Bot module for Mentat. This module contains the class for the bot."""

import logging
import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ServerConnection
from jaraco.stream import buffer
from mentat.commands.dados import dados
from mentat.commands.hola import hola
from mentat.commands.login import login
from mentat.commands.desconectar import desconectar
from mentat.commands.morir import morir
from mentat.commands.join import join
from mentat.commands.part import part
from mentat.commands.estado import estado
from mentat.commands.common import (
    BotArgumentParser,
    parse_command_args,
    reply_target,
    send_lines,
)
from mentat.config import Config
from mentat.logger import Logger
from mentat.status import Status


class Mentat(irc.bot.SingleServerIRCBot):
    """Class for the bot."""

    def __init__(self, config: Config):
        """Constructor for the bot."""
        self.config = config
        self.logger = Logger(self.config)
        self.status = Status()  # first status is INIT

        # ServerConnection.buffer_class.errors = "replace"
        ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer

        irc.bot.SingleServerIRCBot.__init__(
            self,
            [(self.config.irc_server, self.config.irc_port)],
            self.config.irc_nick,
            self.config.irc_realname,
        )

    def start(self):
        """Starts the bot."""
        logging.debug("Entering start function")
        logging.info("Starting bot.")
        self.status.transition("connect")
        irc.bot.SingleServerIRCBot.start(self)

    def on_nicknameinuse(self, connection: ServerConnection, event):
        """Function to handle the nickname in use error."""
        logging.debug(
            "Entering on_nicknameinuse function: c: %s, e: %s", connection, event
        )
        if (
            event.arguments[0].startswith(
                f"El nick está registrado, tienes que indicar la contraseña para usarlo: /nick {connection.get_nickname()}:contraseña"
            )
            and self.status.get_status() != Status.CONNECTING_AUTHENTICATING
        ):
            logging.warning("Nickname registered. Sending password.")
            self.status.transition(
                "authenticate"
            )  # change status to Status.CONNECTING_AUTHENTICATING
            connection.nick(f"{connection.get_nickname()}:{self.config.irc_password}")
        else:
            logging.error(
                "Nickname in use or wrong password. Changing to %s_",
                connection.get_nickname(),
            )
            connection.nick(connection.get_nickname() + "_")

    def on_welcome(self, connection: ServerConnection, event):
        """Function to handle the welcome message."""
        logging.debug(
            "Entering on_welcome function: c: %s, e: %s", connection, event)
        # change status to Status.CONNECTED
        self.status.transition("connected")
        # for channel in self.channels:
        #     c.join(channel)
        #     logging.info(f"Joining channel: {channel}")

    def on_disconnect(self, connection: ServerConnection, event):
        """Function to handle disconnections.

        SingleServerIRCBot schedules a reconnect by itself, so the status
        goes back to CONNECTING (not INIT) and Mentat.start is not called
        again.
        """
        logging.debug(
            "Entering on_disconnect function: c: %s, e: %s", connection, event)
        logging.warning("Disconnected from server: %s", event.arguments)
        self.status.transition("disconnect")

    def on_endofmotd(self, connection: ServerConnection, event):
        """Function to handle the end of MOTD."""
        logging.debug(
            "Entering on_endofmotd function: c: %s, e: %s", connection, event)
        logging.info("End of MOTD received. Setting mode +In")
        connection.mode(connection.get_nickname(), "+In")
        logging.info(
            "End of MOTD received. Joining channels: %s", self.config.irc_channels)
        for channel in self.config.irc_channels:
            logging.info("Joining channel: %s", channel)
            connection.join(channel)
            logging.debug("Joined channel: %s", channel)

    def on_pubmsg(self, connection: ServerConnection, event):
        """Function to handle public messages."""
        logging.debug("Entering on_pubmsg function: c: %s, e: %s",
                      connection, event)
        self.logger.pubmsg(event)
        subject = event.arguments[0].split(":", 1)
        if len(subject) > 1 and irc.strings.lower(subject[0]) == irc.strings.lower(
            self.connection.get_nickname()
        ):
            self.do_command(event, subject[1].strip())

    def on_privmsg(self, connection: ServerConnection, event):
        """Function to handle private messages."""
        logging.debug(
            "Entering on_privmsg function: c: %s, e: %s", connection, event)
        self.logger.privmsg(event)
        self.do_command(event, event.arguments[0])

    def on_join(self, connection: ServerConnection, event):
        """Function to handle join messages."""
        logging.debug("Entering on_join function: c: %s, e: %s",
                      connection, event)
        self.logger.join_part(event)

    def on_part(self, connection: ServerConnection, event):
        """Function to handle part messages."""
        logging.debug("Entering on_part function: c: %s, e: %s",
                      connection, event)
        self.logger.join_part(event)

    def on_dccmsg(self, connection: ServerConnection, event):
        """Function to handle DCC messages."""
        # non-chat DCC messages are raw bytes; decode as text
        text = event.arguments[0].decode("utf-8")
        connection.privmsg(event.source.nick, "You said: " + text)

    def on_dccchat(self, connection: ServerConnection, event):
        """Function to handle DCC chat requests."""
        if len(event.arguments) != 2:
            return
        args = event.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def on_action(self, connection: ServerConnection, event):
        """Function to handle actions."""
        logging.debug("Entering on_action function: c: %s, e: %s",
                      connection, event)
        self.logger.action(event)

    def on_kick(self, connection: ServerConnection, event):
        """Function to handle kicks."""
        logging.debug("Entering on_kick function: c: %s, e: %s",
                      connection, event)
        self.logger.kick(event)
        # check if the bot was kicked (compare with the nick we actually
        # got, which may differ from the configured one, e.g. "Mentat_")
        if event.arguments[0] == connection.get_nickname():
            # connection.join(event.target)
            # TODO: add an auto-rejoin feature to the config.

            # remove the channel from the list of channels
            self.config.remove_channel(event.target)

    def on_nick(self, connection: ServerConnection, event):
        """Function to handle nick changes."""
        logging.debug("Entering on_nick function: c: %s, e: %s",
                      connection, event)
        self.logger.nick(event)
    
    def on_umode(self, connection: ServerConnection, event):
        """Function to handle user modes."""
        logging.debug("Entering on_umode function: c: %s, e: %s",
                      connection, event)
        self.logger.umode(event)

    def do_command(self, event, cmd: str):
        """Function to handle commands."""
        logging.debug(
            "Entering do_command function: e: %s, cmd: %s", event, cmd)
        nick = event.source.nick
        talk_to = reply_target(event)

        connection = self.connection

        parser = BotArgumentParser(
            description="Mentat IRC bot",
            prog="Mentat:",
            epilog="Add --help after the command to get help about the command",
        )

        parser.add_argument(
            "cmd", 
            choices=["login", "hola", "op", "dados", "desconectar", "morir", "join", "part", "estado"], 
            help="Command to execute"
        )

        cmd_list = cmd.split()

        parsed, help_lines = parse_command_args(parser, cmd_list[:1])
        if parsed is None:
            send_lines(connection, talk_to, help_lines)
            return
        command = parsed.cmd

        if command == "hola":
            logging.debug("Command: hola")
            hola(connection, event, cmd_list[1:])
            # connection.privmsg(talk_to, "Hola, " + nick)
        elif command == "login":
            logging.debug("Command: login")
            login(connection, event, cmd_list[1:], self.config)
        elif command == "op":
            if not self.config.is_admin(nick):
                return
            logging.debug("Command: op")
            if len(cmd_list) > 1 and len(cmd_list) < 4:
                nick_to_op = cmd_list[1]
                channel = ""
                try:
                    channel = cmd_list[2]
                except IndexError:
                    channel = talk_to
                logging.debug("Channel: %s, Nick to op: %s",
                              channel, nick_to_op)
                connection.mode(channel, f"+o {nick_to_op}")
            elif len(cmd_list) == 1 and event.type != "privmsg":
                connection.mode(talk_to, f"+o {nick}")
        elif command == "dados":
            logging.debug("Command: dados")
            dados(connection, event, cmd_list[1:])
        elif command == "desconectar":
            logging.debug("Command: desconectar")
            desconectar(connection, event, cmd_list[1:], self.config)
        elif command == "morir":
            logging.debug("Command: morir")
            morir(connection, event, cmd_list[1:], self.config)
        elif command == "join":
            logging.debug("Command: join")
            join(connection, event, cmd_list[1:], self.config)
        elif command == "part":
            logging.debug("Command: part")
            part(connection, event, cmd_list[1:], self.config)
        elif command == "estado":
            logging.debug("Command: estado")
            estado(connection, event, cmd_list[1:], self.config)
