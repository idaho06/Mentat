"""Bot module for Mentat. This module contains the class for the bot."""

import logging
import re
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
from mentat.commands.op import op
from mentat.commands.observa import observa
from mentat.commands.common import BotArgumentParser, parse_or_reply, reply_target
from mentat.config import Config
from mentat.logger import Logger
from mentat.status import Status

# command name -> handler(connection, event, args, config)
COMMANDS = {
    "login": login,
    "hola": hola,
    "op": op,
    "dados": dados,
    "desconectar": desconectar,
    "morir": morir,
    "join": join,
    "part": part,
    "estado": estado,
    "observa": observa,
}


class Mentat(irc.bot.SingleServerIRCBot):
    """Class for the bot."""

    def __init__(self, config: Config):
        """Constructor for the bot."""
        self.config = config
        self.logger = Logger(self.config)
        self.status = Status()  # first status is INIT

        irc.bot.SingleServerIRCBot.__init__(
            self,
            [(self.config.irc_server, self.config.irc_port)],
            self.config.irc_nick,
            self.config.irc_realname,
        )
        # Tolerate bad bytes from the server. Set on this connection only:
        # connect() instantiates self.buffer_class, so an instance attribute
        # is enough and other ServerConnections in the process are untouched.
        self.connection.buffer_class = buffer.LenientDecodingLineBuffer

        # The library's own "quit" handler (priority -20, registered by
        # SingleServerIRCBot.__init__ above) removes the quitting nick from
        # self.channels before on_quit (priority -10) ever runs. Hook in
        # ahead of it to record which channels the nick was still in.
        self.connection.add_global_handler(
            "quit", self._capture_quit_channels, -25
        )

    def start(self):
        """Starts the bot."""
        logging.debug("Entering start function")
        logging.info("Starting bot.")
        self.status.transition("connect")
        irc.bot.SingleServerIRCBot.start(self)

    def _dispatcher(self, connection: ServerConnection, event):
        """Dispatches every IRC event to its on_<type> handler.

        This is the irc library's single dispatch point and nothing above
        it catches exceptions, so one bad event would end the whole
        process. Handlers run on network input; anything unexpected is
        logged and the bot keeps going. SystemExit (used by "morir") is not
        an Exception and still propagates.
        """
        try:
            super()._dispatcher(connection, event)
        except Exception:  # pylint: disable=broad-exception-caught
            logging.exception("Handler for %s event failed: %s", event.type, event)

    def on_nicknameinuse(self, connection: ServerConnection, event):
        """Function to handle the nickname in use error."""
        logging.debug(
            "Entering on_nicknameinuse function: c: %s, e: %s", connection, event
        )
        if (
            event.arguments[0].startswith(
                "El nick está registrado, tienes que indicar la contraseña "
                f"para usarlo: /nick {connection.get_nickname()}:contraseña"
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
        self.config.clear_watched_nicks_online()
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
        for nick in self.config.observa_nicks:
            logging.info("Resubscribing WATCH for %s", nick)
            connection.send_raw(f"WATCH +{nick}")

    def on_pubmsg(self, connection: ServerConnection, event):
        """Function to handle public messages."""
        logging.debug("Entering on_pubmsg function: c: %s, e: %s",
                      connection, event)
        self.logger.pubmsg(event)
        if self.config.has_watched_nick(event.source.nick):
            self.logger.watched_pubmsg(event)
        for nick in self._mentioned_watched_nicks(event.arguments[0], event.source.nick):
            self.logger.watched_mention(event, nick)
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
        if self.config.has_watched_nick(event.source.nick):
            self.logger.watched_join_part(event)

    def on_part(self, connection: ServerConnection, event):
        """Function to handle part messages."""
        logging.debug("Entering on_part function: c: %s, e: %s",
                      connection, event)
        self.logger.join_part(event)
        if self.config.has_watched_nick(event.source.nick):
            self.logger.watched_join_part(event)

    def on_dccmsg(self, connection: ServerConnection, event):
        """Function to handle DCC messages."""
        # non-chat DCC messages are raw bytes; decode as text, and never
        # raise on invalid bytes (an exception here would kill the bot)
        text = event.arguments[0].decode("utf-8", errors="replace")
        connection.privmsg(event.source.nick, "You said: " + text)

    def on_dccchat(self, connection: ServerConnection, event):
        """Function to handle DCC chat requests.

        Accepting a DCC CHAT makes the bot open a TCP connection to the
        address the requester chooses, so only admins may ask for it.
        """
        if not self.config.is_admin(event.source.nick):
            logging.warning(
                "Ignoring DCC chat request from non-admin %s", event.source)
            return
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
        if self.config.has_watched_nick(event.source.nick):
            self.logger.watched_action(event)
        for nick in self._mentioned_watched_nicks(event.arguments[0], event.source.nick):
            self.logger.watched_mention(event, nick)

    def on_kick(self, connection: ServerConnection, event):
        """Function to handle kicks."""
        logging.debug("Entering on_kick function: c: %s, e: %s",
                      connection, event)
        self.logger.kick(event)
        kicked = event.arguments[0]
        kicker = event.source.nick
        if self.config.has_watched_nick(kicked):
            self.logger.watched_kick(event, kicked)
        if self.config.has_watched_nick(kicker):
            self.logger.watched_kick(event, kicker)
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
        if self.config.has_watched_nick(event.source.nick):
            self.logger.watched_nick(event)

    def on_umode(self, connection: ServerConnection, event):
        """Function to handle user modes."""
        logging.debug("Entering on_umode function: c: %s, e: %s",
                      connection, event)
        self.logger.umode(event)

    def on_mode(self, connection: ServerConnection, event):
        """Function to handle channel mode changes."""
        logging.debug("Entering on_mode function: c: %s, e: %s",
                      connection, event)
        self.logger.mode(event)
        for nick in event.arguments[1:]:
            if self.config.has_watched_nick(nick):
                self.logger.watched_mode(event, nick)

    def on_away(self, connection: ServerConnection, event):
        """Function to handle away-notify status changes.

        RPL_AWAY (numeric 301, a reply to messaging an away user) is also
        named "away" by the irc library, but always carries arguments (the
        away nick and reason); real away-notify never does. Only the latter
        is a real watched-nick status change worth logging.
        """
        if event.arguments:
            return
        if self.config.has_watched_nick(event.source.nick):
            self.logger.watched_away(event)

    def on_chghost(self, connection: ServerConnection, event):
        """Function to handle CHGHOST (host change) for a watched nick."""
        if self.config.has_watched_nick(event.source.nick):
            self.logger.watched_chghost(event)

    def on_600(self, connection: ServerConnection, event):
        """Function to handle RPL_LOGON: a watched nick just connected."""
        nick = event.arguments[0]
        self.config.mark_watched_nick_online(nick)
        self.logger.watched_connect(event)

    def on_601(self, connection: ServerConnection, event):
        """Function to handle RPL_LOGOFF: a watched nick just disconnected."""
        nick = event.arguments[0]
        self.config.mark_watched_nick_offline(nick)
        self.logger.watched_disconnect(event)

    def on_604(self, connection: ServerConnection, event):
        """Function to handle RPL_NOWON: a watched nick is online (initial state)."""
        nick = event.arguments[0]
        self.config.mark_watched_nick_online(nick)
        self.logger.watched_connect(event)

    def on_605(self, connection: ServerConnection, event):
        """Function to handle RPL_NOWOFF: a watched nick is offline (initial state)."""
        nick = event.arguments[0]
        self.config.mark_watched_nick_offline(nick)
        self.logger.watched_disconnect(event)

    def _mentioned_watched_nicks(self, text: str, exclude_nick: str) -> list:
        """Watched nicks mentioned by name in ``text``, excluding ``exclude_nick``.

        Matches case-insensitively on a word boundary (so "Qetu:" or "hey
        QETU" match but "asqetuas" doesn't); relies on Python's regex \\b,
        which assumes the nick starts/ends with a word character — a nick
        with a leading/trailing symbol (e.g. "[bot]") wouldn't match
        reliably, not a concern for the currently configured nicks.
        """
        mentioned = []
        for nick in self.config.observa_nicks:
            if irc.strings.lower(nick) == irc.strings.lower(exclude_nick):
                continue
            if re.search(r"\b" + re.escape(nick) + r"\b", text, re.IGNORECASE):
                mentioned.append(nick)
        return mentioned

    def _capture_quit_channels(self, connection: ServerConnection, event):
        """Records which channels a quitting nick was in.

        Runs before the library's own "quit" handler clears that nick
        from self.channels, so on_quit still knows where to log it.
        """
        nick = event.source.nick
        event.quit_channels = [
            channel
            for channel, info in self.channels.items()
            if info.has_user(nick)
        ]

    def on_quit(self, connection: ServerConnection, event):
        """Function to handle quit messages."""
        logging.debug("Entering on_quit function: c: %s, e: %s",
                      connection, event)
        if not hasattr(event, "quit_channels"):
            # Should be set by _capture_quit_channels, registered ahead of
            # on_quit specifically so this always runs first. Its absence
            # means that ordering broke, so warn instead of silently
            # logging nothing.
            logging.warning(
                "quit event for %s has no captured channels; ordering with "
                "_capture_quit_channels may be broken", event.source.nick
            )
        self.logger.quit(event, getattr(event, "quit_channels", []))

    def do_command(self, event, cmd: str):
        """Function to handle commands."""
        logging.debug(
            "Entering do_command function: e: %s, cmd: %s", event, cmd)
        talk_to = reply_target(event)
        connection = self.connection

        parser = BotArgumentParser(
            description="Mentat IRC bot",
            prog="Mentat:",
            epilog="Add --help after the command to get help about the command",
        )
        parser.add_argument("cmd", choices=list(COMMANDS), help="Command to execute")

        cmd_list = cmd.split()
        parsed = parse_or_reply(parser, cmd_list[:1], connection, talk_to)
        if parsed is None:
            return

        logging.debug("Command: %s", parsed.cmd)
        try:
            COMMANDS[parsed.cmd](connection, event, cmd_list[1:], self.config)
        except Exception:
            # tell the user; _dispatcher logs the traceback
            connection.privmsg(talk_to, "Error ejecutando el comando")
            raise
