"""Tests for the file Logger and the SecretFilter."""

import logging
import os
import re

import pytest

from mentat.logger import Logger, SecretFilter

STAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ")


@pytest.fixture
def file_logger(tmp_config):
    return Logger(tmp_config)


def read(tmp_config, name: str) -> list[str]:
    with open(f"{tmp_config.logdir}/{name}", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    for line in lines:
        assert STAMP.match(line), line
    return [STAMP.sub("", line) for line in lines]


def make_record(msg, *args):
    return logging.LogRecord("test", logging.DEBUG, __file__, 1, msg, args, None)


def test_secret_filter_rewrites_only_records_with_secrets(tmp_config):
    secret_filter = SecretFilter(tmp_config)

    record = make_record("TO SERVER: NICK %s:%s", "Mentat", "nickpass")
    assert secret_filter.filter(record)
    assert record.getMessage() == "TO SERVER: NICK Mentat:******"
    assert record.args == ()

    clean = make_record("count %d", 3)
    assert secret_filter.filter(clean)
    assert clean.msg == "count %d"
    assert clean.args == (3,)


def test_secret_filter_on_a_handler_covers_other_loggers(tmp_config):
    handler = logging.Handler()
    seen = []
    handler.emit = seen.append
    handler.addFilter(SecretFilter(tmp_config))
    logger = logging.getLogger("irc.client")
    logger.addHandler(handler)
    try:
        logger.debug("FROM SERVER: PRIVMSG Mentat :login %s", "admin")
    finally:
        logger.removeHandler(handler)
    assert seen and seen[0].getMessage() == "FROM SERVER: PRIVMSG Mentat :login ******"


def test_pubmsg(file_logger, tmp_config, make_event):
    file_logger.pubmsg(make_event("pubmsg", "tester", "#mentat", "hello"))
    assert read(tmp_config, "channel_mentat.log") == ["::: <tester> hello"]


def test_join_and_part(file_logger, tmp_config, make_event):
    file_logger.join_part(make_event("join", "tester", "#mentat"))
    file_logger.join_part(make_event("part", "tester", "#mentat"))
    assert read(tmp_config, "channel_mentat.log") == [
        "==> tester joined the channel",
        "<== tester parted the channel",
    ]


def test_privmsg_is_redacted_in_the_file(file_logger, tmp_config, make_event):
    file_logger.privmsg(make_event("privmsg", "tester", "Mentat", "login admin"))
    file_logger.privmsg(make_event("privmsg", "tester", "Mentat", "hola"))
    assert read(tmp_config, "nick_tester.log") == ["login ******", "hola"]


def test_action(file_logger, tmp_config, make_event):
    file_logger.action(make_event("action", "tester", "#mentat", "waves"))
    assert read(tmp_config, "channel_mentat.log") == ["-*- tester waves"]


def test_kick_with_and_without_reason(file_logger, tmp_config, make_event):
    file_logger.kick(make_event("kick", "tester", "#mentat", arguments=["victim", "bye"]))
    file_logger.kick(make_event("kick", "tester", "#mentat", arguments=["victim"]))
    assert read(tmp_config, "channel_mentat.log") == [
        "<=* tester has kicked victim: bye",
        "<=* tester has kicked victim: ",
    ]


def test_nick_change(file_logger, tmp_config, make_event):
    file_logger.nick(make_event("nick", "tester", "newname"))
    assert read(tmp_config, "nick_changes.log") == ["*** tester is now known as newname"]


def test_umode(file_logger, tmp_config, make_event):
    file_logger.umode(make_event("umode", "tester", "tester", arguments=["+i"]))
    no_source = make_event("umode", "tester", "tester", arguments=["+x"])
    no_source.source = None
    file_logger.umode(no_source)
    assert read(tmp_config, "mode_changes.log") == [
        "*** tester sets mode: +i",
        "*** unknown sets mode: +x",
    ]


def test_channel_mode_joins_all_arguments(file_logger, tmp_config, make_event):
    file_logger.mode(make_event("mode", "tester", "#mentat", arguments=["+o", "bob"]))
    assert read(tmp_config, "channel_mentat.log") == ["*** tester sets mode: +o bob"]


def test_quit_with_and_without_reason(file_logger, tmp_config, make_event):
    file_logger.quit(make_event("quit", "tester", "*", "bye"), ["#mentat"])
    file_logger.quit(make_event("quit", "tester", "*"), ["#mentat"])
    assert read(tmp_config, "channel_mentat.log") == [
        "<<< tester has quit: bye",
        "<<< tester has quit: ",
    ]


def test_quit_is_logged_to_every_channel_the_nick_was_in(file_logger, tmp_config, make_event):
    file_logger.quit(make_event("quit", "tester", "*", "bye"), ["#mentat", "#other"])
    assert read(tmp_config, "channel_mentat.log") == ["<<< tester has quit: bye"]
    assert read(tmp_config, "channel_other.log") == ["<<< tester has quit: bye"]


def test_quit_with_no_channels_writes_nothing(file_logger, tmp_config, make_event):
    file_logger.quit(make_event("quit", "tester", "*", "bye"), [])
    assert not os.path.exists(f"{tmp_config.logdir}/nick_tester.log")


def test_watched_pubmsg_appends_a_single_dot_with_no_timestamp_or_newline(file_logger, tmp_config, make_event):
    file_logger.watched_pubmsg(make_event("pubmsg", "bob", "#mentat", "hi"))
    file_logger.watched_pubmsg(make_event("pubmsg", "bob", "#mentat", "again"))
    with open(f"{tmp_config.logdir}/nick_bob.log", "rb") as f:
        assert f.read() == b".."


def test_watched_pubmsg_and_privmsg_share_the_same_file(file_logger, tmp_config, make_event):
    file_logger.watched_pubmsg(make_event("pubmsg", "bob", "#mentat", "hi"))
    file_logger.privmsg(make_event("privmsg", "bob", "Mentat", "hola"))
    with open(f"{tmp_config.logdir}/nick_bob.log", encoding="utf-8") as f:
        content = f.read()
    assert content.startswith(".")
    assert content.endswith("hola\n")
