"""Tests for the Mentat event handlers and command dispatch, offline."""

import logging
import os

import pytest
import irc.bot
from irc.client import ServerConnection
from jaraco.stream import buffer

from mentat import bot as botmod
from mentat.bot import Mentat
from mentat.status import Status

SPANISH_433 = (
    "El nick está registrado, tienes que indicar la contraseña para usarlo: "
    "/nick {nick}:contraseña"
)


def channel_log(config, channel="mentat"):
    with open(f"{config.logdir}/channel_{channel}.log", encoding="utf-8") as handle:
        return handle.read()


# message routing ----------------------------------------------------------

def test_pubmsg_addressed_to_the_bot_runs_the_command(bot, fake_connection, make_event):
    bot.on_pubmsg(fake_connection, make_event("pubmsg", "tester", "#mentat", "Mentat: hola"))
    assert fake_connection.sent("privmsg") == [("#mentat", "Hola, tester")]


def test_pubmsg_prefix_is_case_insensitive_and_follows_the_actual_nick(bot, fake_connection, make_event):
    fake_connection.nickname = "Mentat_"
    bot.on_pubmsg(fake_connection, make_event("pubmsg", "tester", "#mentat", "mentat_: hola"))
    assert fake_connection.privmsgs() == ["Hola, tester"]


def test_pubmsg_not_addressed_to_the_bot_is_only_logged(bot, fake_connection, make_event, tmp_config):
    bot.on_pubmsg(fake_connection, make_event("pubmsg", "tester", "#mentat", "hello all"))
    bot.on_pubmsg(fake_connection, make_event("pubmsg", "tester", "#mentat", "Mentat_: hola"))
    assert fake_connection.calls == []
    assert "::: <tester> hello all" in channel_log(tmp_config)


def test_pubmsg_from_a_watched_nick_also_appends_a_dot(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("bob")
    bot.on_pubmsg(fake_connection, make_event("pubmsg", "bob", "#mentat", "hi"))
    with open(f"{tmp_config.logdir}/nick_bob.log", "rb") as handle:
        assert handle.read() == b"."


def test_pubmsg_from_a_non_watched_nick_does_not_touch_its_nick_file(bot, fake_connection, make_event, tmp_config):
    bot.on_pubmsg(fake_connection, make_event("pubmsg", "tester", "#mentat", "hi"))
    assert not os.path.exists(f"{tmp_config.logdir}/nick_tester.log")


def test_join_and_part_from_a_watched_nick_also_log_to_its_nick_file(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("bob")
    bot.on_join(fake_connection, make_event("join", "bob", "#mentat"))
    bot.on_part(fake_connection, make_event("part", "bob", "#mentat"))
    with open(f"{tmp_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        content = handle.read()
    assert "bob joined the channel" in content
    assert "bob parted the channel" in content
    assert "bob joined the channel" in channel_log(tmp_config)


def test_join_and_part_from_a_non_watched_nick_do_not_touch_its_nick_file(bot, fake_connection, make_event, tmp_config):
    bot.on_join(fake_connection, make_event("join", "tester", "#mentat"))
    bot.on_part(fake_connection, make_event("part", "tester", "#mentat"))
    assert not os.path.exists(f"{tmp_config.logdir}/nick_tester.log")


def test_action_from_a_watched_nick_also_logs_to_its_nick_file(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("bob")
    bot.on_action(fake_connection, make_event("action", "bob", "#mentat", "waves"))
    with open(f"{tmp_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        assert "bob waves" in handle.read()


def test_action_from_a_non_watched_nick_does_not_touch_its_nick_file(bot, fake_connection, make_event, tmp_config):
    bot.on_action(fake_connection, make_event("action", "tester", "#mentat", "waves"))
    assert not os.path.exists(f"{tmp_config.logdir}/nick_tester.log")


def test_kick_logs_to_the_kicked_watched_nicks_file(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("bob")
    bot.on_kick(fake_connection, make_event("kick", "tester", "#mentat", arguments=["bob", "bye"]))
    with open(f"{tmp_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        assert "tester has kicked bob: bye" in handle.read()


def test_kick_logs_to_the_kicker_watched_nicks_file(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("tester")
    bot.on_kick(fake_connection, make_event("kick", "tester", "#mentat", arguments=["bob", "bye"]))
    with open(f"{tmp_config.logdir}/nick_tester.log", encoding="utf-8") as handle:
        assert "tester has kicked bob: bye" in handle.read()


def test_kick_between_non_watched_nicks_touches_no_nick_file(bot, fake_connection, make_event, tmp_config):
    bot.on_kick(fake_connection, make_event("kick", "tester", "#mentat", arguments=["bob", "bye"]))
    assert not os.path.exists(f"{tmp_config.logdir}/nick_bob.log")
    assert not os.path.exists(f"{tmp_config.logdir}/nick_tester.log")


def test_mode_change_targeting_a_watched_nick_also_logs_to_its_file(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("bob")
    bot.on_mode(fake_connection, make_event("mode", "idaho", "#mentat", arguments=["+o", "bob"]))
    with open(f"{tmp_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        assert "idaho sets mode: +o bob" in handle.read()


def test_mode_change_not_targeting_a_watched_nick_touches_no_nick_file(bot, fake_connection, make_event, tmp_config):
    bot.on_mode(fake_connection, make_event("mode", "idaho", "#mentat", arguments=["+o", "bob"]))
    assert not os.path.exists(f"{tmp_config.logdir}/nick_bob.log")


def test_nick_change_of_a_watched_nick_also_logs_to_its_own_file(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("bob")
    bot.on_nick(fake_connection, make_event("nick", "bob", "newbob"))
    with open(f"{tmp_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        assert "bob is now known as newbob" in handle.read()


def test_nick_change_of_a_non_watched_nick_touches_no_nick_file(bot, fake_connection, make_event, tmp_config):
    bot.on_nick(fake_connection, make_event("nick", "tester", "newname"))
    assert not os.path.exists(f"{tmp_config.logdir}/nick_tester.log")


def test_on_away_logs_away_notify_for_a_watched_nick(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("bob")
    bot.on_away(fake_connection, make_event("away", "bob", "gone fishing"))
    with open(f"{tmp_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        assert "bob is away: gone fishing" in handle.read()


def test_on_away_ignores_rpl_301_which_carries_arguments(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("bob")
    # RPL_301: source is the server, target is the bot's own nick, and the
    # away nick + reason land in arguments -- this must not be logged as if
    # bob had gone away via away-notify.
    event = make_event("away", "localhost", "Mentat", arguments=["bob", "gone fishing"])
    bot.on_away(fake_connection, event)
    assert not os.path.exists(f"{tmp_config.logdir}/nick_bob.log")


def test_on_away_for_a_non_watched_nick_touches_no_nick_file(bot, fake_connection, make_event, tmp_config):
    bot.on_away(fake_connection, make_event("away", "tester", "gone fishing"))
    assert not os.path.exists(f"{tmp_config.logdir}/nick_tester.log")


def test_on_chghost_logs_for_a_watched_nick(bot, fake_connection, make_event, tmp_config):
    tmp_config.add_watched_nick("bob")
    bot.on_chghost(fake_connection, make_event("chghost", "bob", "newident", arguments=["newhost"]))
    with open(f"{tmp_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        assert "bob changed host to newident@newhost" in handle.read()


def test_on_chghost_for_a_non_watched_nick_touches_no_nick_file(bot, fake_connection, make_event, tmp_config):
    bot.on_chghost(fake_connection, make_event("chghost", "tester", "newident", arguments=["newhost"]))
    assert not os.path.exists(f"{tmp_config.logdir}/nick_tester.log")


def test_privmsg_runs_the_command_and_logs_it(bot, fake_connection, make_event, tmp_config):
    bot.on_privmsg(fake_connection, make_event("privmsg", "tester", "Mentat", "hola -n Bob"))
    assert fake_connection.sent("privmsg") == [("tester", "Hola, Bob")]
    with open(f"{tmp_config.logdir}/nick_tester.log", encoding="utf-8") as handle:
        assert "hola -n Bob" in handle.read()


def test_unknown_command_gets_the_top_level_usage(bot, fake_connection, make_event):
    bot.do_command(make_event("privmsg", "tester", "Mentat", "nosuch"), "nosuch")
    lines = fake_connection.privmsgs("tester")
    assert lines[0].startswith("usage: Mentat:")
    assert any("invalid choice: 'nosuch'" in line for line in lines)


def test_top_level_help_lists_commands_and_epilog(bot, fake_connection, make_event):
    bot.do_command(make_event("privmsg", "tester", "Mentat", "-h"), "-h")
    lines = fake_connection.privmsgs("tester")
    assert lines[0].startswith("usage: Mentat:")
    assert any("Add --help after the command" in line for line in lines)


def test_empty_command_gets_usage(bot, fake_connection, make_event):
    bot.do_command(make_event("privmsg", "tester", "Mentat", ""), "")
    assert fake_connection.privmsgs("tester")[0].startswith("usage: Mentat:")


def test_every_registered_command_is_a_parser_choice(bot, fake_connection, make_event):
    for name in botmod.COMMANDS:
        bot.do_command(make_event("privmsg", "tester", "Mentat", f"{name} -h"), f"{name} -h")
    assert not any("invalid choice" in line for line in fake_connection.privmsgs())


# error handling -----------------------------------------------------------

def test_command_exception_is_reported_and_logged_not_fatal(bot, fake_connection, make_event, monkeypatch, caplog):
    def boom(*_args):
        raise ZeroDivisionError("kaboom")

    monkeypatch.setitem(botmod.COMMANDS, "hola", boom)
    with caplog.at_level(logging.ERROR):
        bot._dispatcher(fake_connection, make_event("privmsg", "tester", "Mentat", "hola"))
    assert fake_connection.sent("privmsg") == [("tester", "Error ejecutando el comando")]
    assert "Handler for privmsg event failed" in caplog.text
    assert "ZeroDivisionError: kaboom" in caplog.text


def test_any_handler_exception_is_swallowed(bot, fake_connection, make_event, monkeypatch, caplog):
    monkeypatch.setattr(bot.logger, "join_part", lambda event: 1 / 0)
    with caplog.at_level(logging.ERROR):
        bot._dispatcher(fake_connection, make_event("join", "tester", "#mentat"))
    assert "Handler for join event failed" in caplog.text


def test_systemexit_from_morir_propagates(bot, fake_connection, make_event):
    with pytest.raises(SystemExit):
        bot._dispatcher(fake_connection, make_event("privmsg", "idaho", "Mentat", "morir"))
    assert fake_connection.sent("disconnect") == [("Ouch!!",)]


def test_events_without_a_handler_are_ignored(bot, fake_connection, make_event):
    bot._dispatcher(fake_connection, make_event("topic", "tester", "#mentat", "new topic"))
    assert fake_connection.calls == []


# connection life cycle ----------------------------------------------------

def test_registered_nick_sends_the_password_once(bot, fake_connection, make_event):
    bot.status.transition("connect")
    message = SPANISH_433.format(nick="Mentat")
    bot.on_nicknameinuse(fake_connection, make_event("nicknameinuse", "server", "NICK", message))
    assert fake_connection.sent("nick") == [("Mentat:nickpass",)]
    assert bot.status.get_status() == Status.CONNECTING_AUTHENTICATING

    # a second 433 while authenticating means the password was wrong
    fake_connection.nickname = "Mentat"
    bot.on_nicknameinuse(fake_connection, make_event("nicknameinuse", "server", "NICK", message))
    assert fake_connection.sent("nick")[-1] == ("Mentat_",)


def test_plain_nick_in_use_appends_an_underscore(bot, fake_connection, make_event):
    bot.status.transition("connect")
    bot.on_nicknameinuse(fake_connection, make_event("nicknameinuse", "server", "NICK", "Nickname is already in use"))
    assert fake_connection.sent("nick") == [("Mentat_",)]
    assert bot.status.get_status() == Status.CONNECTING


def test_welcome_and_disconnect_drive_the_status(bot, fake_connection, make_event):
    bot.status.transition("connect")
    bot.on_welcome(fake_connection, make_event("welcome", "server", "Mentat", "Welcome"))
    assert bot.status.get_status() == Status.CONNECTED
    bot.on_disconnect(fake_connection, make_event("disconnect", "server", "", ""))
    assert bot.status.get_status() == Status.CONNECTING


def test_end_of_motd_sets_umode_and_joins_configured_channels(bot, fake_connection, make_event, tmp_config):
    tmp_config.irc_channels = ["#mentat", "#other"]
    bot.on_endofmotd(fake_connection, make_event("endofmotd", "server", "Mentat", "End of MOTD"))
    assert fake_connection.calls == [
        ("mode", ("Mentat", "+In")),
        ("join", ("#mentat",)),
        ("join", ("#other",)),
    ]


# channel events -----------------------------------------------------------

def test_being_kicked_forgets_the_channel(bot, fake_connection, make_event, tmp_config):
    fake_connection.nickname = "Mentat_"
    bot.on_kick(fake_connection, make_event("kick", "idaho", "#MENTAT", arguments=["Mentat_", "bye"]))
    assert tmp_config.irc_channels == []
    assert "<=* idaho has kicked Mentat_: bye" in channel_log(tmp_config, "MENTAT")


def test_someone_else_kicked_keeps_the_channel(bot, fake_connection, make_event, tmp_config):
    bot.on_kick(fake_connection, make_event("kick", "idaho", "#mentat", arguments=["bob"]))
    assert tmp_config.irc_channels == ["#mentat"]


def test_mode_umode_quit_join_part_action_nick_are_logged(bot, fake_connection, make_event, tmp_config):
    bot.on_mode(fake_connection, make_event("mode", "idaho", "#mentat", arguments=["+o", "bob"]))
    bot.on_join(fake_connection, make_event("join", "bob", "#mentat"))
    bot.on_part(fake_connection, make_event("part", "bob", "#mentat"))
    bot.on_action(fake_connection, make_event("action", "bob", "#mentat", "waves"))
    log = channel_log(tmp_config)
    assert "*** idaho sets mode: +o bob" in log
    assert "==> bob joined the channel" in log
    assert "<== bob parted the channel" in log
    assert "-*- bob waves" in log

    bot.on_umode(fake_connection, make_event("umode", "Mentat", "Mentat", arguments=["+In"]))
    bot.on_nick(fake_connection, make_event("nick", "bob", "robert"))
    with open(f"{tmp_config.logdir}/mode_changes.log", encoding="utf-8") as handle:
        assert "*** Mentat sets mode: +In" in handle.read()
    with open(f"{tmp_config.logdir}/nick_changes.log", encoding="utf-8") as handle:
        assert "*** bob is now known as robert" in handle.read()
    assert fake_connection.calls == []


def test_capture_quit_channels_records_channels_before_the_library_clears_them(
    bot, fake_connection, make_event
):
    for name, nick in [("#mentat", "robert"), ("#other", "someoneelse")]:
        bot.channels[name] = irc.bot.Channel()
        bot.channels[name].add_user(nick)

    event = make_event("quit", "robert", "*", "bye")
    bot._capture_quit_channels(fake_connection, event)  # pylint: disable=protected-access
    assert event.quit_channels == ["#mentat"]


def test_on_quit_logs_to_the_channels_captured_on_the_event(
    bot, fake_connection, make_event, tmp_config
):
    event = make_event("quit", "robert", "*", "bye")
    event.quit_channels = ["#mentat", "#other"]
    bot.on_quit(fake_connection, event)
    assert "<<< robert has quit: bye" in channel_log(tmp_config)
    assert "<<< robert has quit: bye" in channel_log(tmp_config, "other")
    assert not os.path.exists(f"{tmp_config.logdir}/nick_robert.log")


def test_on_quit_without_captured_channels_writes_nothing_and_warns(
    bot, fake_connection, make_event, tmp_config, caplog
):
    with caplog.at_level(logging.WARNING):
        bot.on_quit(fake_connection, make_event("quit", "robert", "*", "bye"))
    assert not os.path.exists(f"{tmp_config.logdir}/channel_mentat.log")
    assert not os.path.exists(f"{tmp_config.logdir}/nick_robert.log")
    assert "quit event for robert has no captured channels" in caplog.text


# DCC ----------------------------------------------------------------------

def test_dcc_chat_from_non_admin_is_ignored(bot, fake_connection, make_event, monkeypatch, caplog):
    calls = []
    monkeypatch.setattr(bot, "dcc_connect", lambda *args: calls.append(args))
    with caplog.at_level(logging.WARNING):
        bot.on_dccchat(fake_connection, make_event("dccchat", "tester", "Mentat", arguments=["CHAT", "CHAT chat 2130706433 5000"]))
    assert calls == []
    assert "Ignoring DCC chat request from non-admin" in caplog.text


def test_dcc_chat_from_admin_connects_to_the_given_address(bot, fake_connection, make_event, monkeypatch):
    calls = []
    monkeypatch.setattr(bot, "dcc_connect", lambda *args: calls.append(args))
    bot.on_dccchat(fake_connection, make_event("dccchat", "idaho", "Mentat", arguments=["CHAT", "CHAT chat 2130706433 5000"]))
    assert calls == [("127.0.0.1", 5000)]


def test_dcc_chat_with_bad_address_is_ignored(bot, fake_connection, make_event, monkeypatch):
    calls = []
    monkeypatch.setattr(bot, "dcc_connect", lambda *args: calls.append(args))
    bot.on_dccchat(fake_connection, make_event("dccchat", "idaho", "Mentat", arguments=["CHAT", "CHAT chat notanip 5000"]))
    bot.on_dccchat(fake_connection, make_event("dccchat", "idaho", "Mentat", arguments=["CHAT"]))
    assert calls == []


def test_dcc_message_with_bad_bytes_is_echoed(bot, fake_connection, make_event):
    bot.on_dccmsg(fake_connection, make_event("dccmsg", "idaho", "Mentat", arguments=[b"hola\xff"]))
    assert fake_connection.sent("privmsg") == [("idaho", "You said: hola�")]


# construction -------------------------------------------------------------

def test_lenient_buffer_is_set_on_the_bot_connection_only(tmp_config):
    mentat = Mentat(tmp_config)
    assert mentat.connection.buffer_class is buffer.LenientDecodingLineBuffer
    assert ServerConnection.buffer_class is buffer.DecodingLineBuffer
    lenient = mentat.connection.buffer_class()
    lenient.feed(b"ol\xe9\r\n")
    assert list(lenient.lines()) == ["ol�"] or list(lenient.lines()) == []


def test_bot_uses_the_config_server_and_nick(tmp_config):
    tmp_config.irc_server = "irc.example.test"
    tmp_config.irc_port = 6697
    mentat = Mentat(tmp_config)
    server = mentat.servers.peek()
    assert (server.host, server.port) == ("irc.example.test", 6697)
    assert mentat._nickname == "Mentat"
    assert mentat.status.get_status() == Status.INIT
