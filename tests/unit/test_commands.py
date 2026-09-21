"""Tests for every command, called directly with a fake connection."""

import pytest

from mentat.commands.dados import dados
from mentat.commands.desconectar import desconectar
from mentat.commands.estado import estado
from mentat.commands.hola import hola
from mentat.commands.join import join
from mentat.commands.login import login
from mentat.commands.morir import morir
from mentat.commands.op import op
from mentat.commands.part import part

ADMIN = "idaho"


# hola ---------------------------------------------------------------------

def test_hola_greets_the_caller_in_the_channel(fake_connection, tmp_config, make_event):
    hola(fake_connection, make_event("pubmsg", "tester", "#mentat"), [], tmp_config)
    assert fake_connection.privmsgs() == ["Hola, tester"]
    assert fake_connection.sent("privmsg")[0][0] == "#mentat"


def test_hola_greets_someone_else_in_private(fake_connection, tmp_config, make_event):
    hola(fake_connection, make_event("privmsg", "tester", "Mentat"), ["-n", "Bob"], tmp_config)
    assert fake_connection.sent("privmsg") == [("tester", "Hola, Bob")]


def test_hola_bad_option_returns_usage(fake_connection, tmp_config, make_event):
    hola(fake_connection, make_event(), ["--nope"], tmp_config)
    assert fake_connection.privmsgs()[0].startswith("usage: hola")


# dados --------------------------------------------------------------------

def test_dados_reports_total_and_throws(fake_connection, tmp_config, make_event, monkeypatch):
    monkeypatch.setattr("mentat.commands.dados.random.randint", lambda a, b: b)
    dados(fake_connection, make_event(), ["-d", "20", "-n", "3"], tmp_config)
    assert fake_connection.privmsgs() == ["Total:   60", "Tiradas: [20, 20, 20]"]


def test_dados_defaults_to_one_six_sided_die(fake_connection, tmp_config, make_event, monkeypatch):
    seen = []
    monkeypatch.setattr("mentat.commands.dados.random.randint", lambda a, b: seen.append((a, b)) or 1)
    dados(fake_connection, make_event(), [], tmp_config)
    assert seen == [(1, 6)]


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["-d", "7"], "invalid choice"),
        (["-n", "21"], "debe estar entre 1 y 20"),
        (["-n", "0"], "debe estar entre 1 y 20"),
        (["-n", "x"], "no es un número"),
    ],
)
def test_dados_rejects_bad_arguments(fake_connection, tmp_config, make_event, argv, expected):
    dados(fake_connection, make_event(), argv, tmp_config)
    lines = fake_connection.privmsgs()
    assert lines[0].startswith("usage: dados")
    assert any(expected in line for line in lines), lines


# login --------------------------------------------------------------------

def test_login_is_ignored_in_channels(fake_connection, tmp_config, make_event):
    login(fake_connection, make_event("pubmsg", "tester", "#mentat"), ["admin"], tmp_config)
    assert fake_connection.calls == []
    assert not tmp_config.is_admin("tester")


def test_login_with_wrong_password(fake_connection, tmp_config, make_event):
    login(fake_connection, make_event("privmsg", "tester", "Mentat"), ["nope"], tmp_config)
    assert fake_connection.sent("privmsg") == [("tester", "Wrong password")]
    assert not tmp_config.is_admin("tester")


def test_login_with_right_password_makes_admin(fake_connection, tmp_config, make_event):
    login(fake_connection, make_event("privmsg", "Tester", "Mentat"), ["admin"], tmp_config)
    assert fake_connection.sent("privmsg") == [("Tester", "Welcome, Tester")]
    assert tmp_config.is_admin("tester")


def test_login_without_password_returns_usage(fake_connection, tmp_config, make_event):
    login(fake_connection, make_event("privmsg", "tester", "Mentat"), [], tmp_config)
    assert fake_connection.privmsgs("tester")[0].startswith("usage: login")


# op -----------------------------------------------------------------------

def test_op_requires_admin(fake_connection, tmp_config, make_event):
    op(fake_connection, make_event("pubmsg", "tester", "#mentat"), [], tmp_config)
    assert fake_connection.calls == []


def test_op_without_arguments_ops_the_caller_in_the_channel(fake_connection, tmp_config, make_event):
    op(fake_connection, make_event("pubmsg", ADMIN, "#mentat"), [], tmp_config)
    assert fake_connection.sent("mode") == [("#mentat", "+o idaho")]


def test_op_without_arguments_in_private_does_nothing(fake_connection, tmp_config, make_event):
    op(fake_connection, make_event("privmsg", ADMIN, "Mentat"), [], tmp_config)
    assert fake_connection.calls == []


def test_op_nick_defaults_to_the_current_channel(fake_connection, tmp_config, make_event):
    op(fake_connection, make_event("pubmsg", ADMIN, "#mentat"), ["bob"], tmp_config)
    assert fake_connection.sent("mode") == [("#mentat", "+o bob")]


def test_op_nick_and_channel(fake_connection, tmp_config, make_event):
    op(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["bob", "#other"], tmp_config)
    assert fake_connection.sent("mode") == [("#other", "+o bob")]


def test_op_with_too_many_arguments_does_nothing(fake_connection, tmp_config, make_event):
    op(fake_connection, make_event("pubmsg", ADMIN, "#mentat"), ["a", "b", "c"], tmp_config)
    assert fake_connection.calls == []


# join / part --------------------------------------------------------------

def test_join_requires_admin(fake_connection, tmp_config, make_event):
    join(fake_connection, make_event("pubmsg", "tester", "#mentat"), ["#new"], tmp_config)
    assert fake_connection.calls == []
    assert not tmp_config.has_channel("#new")


def test_join_joins_and_remembers_the_channel(fake_connection, tmp_config, make_event):
    join(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["#new"], tmp_config)
    assert fake_connection.sent("join") == [("#new",)]
    assert tmp_config.irc_channels == ["#mentat", "#new"]


def test_join_without_channel_returns_usage(fake_connection, tmp_config, make_event):
    join(fake_connection, make_event("privmsg", ADMIN, "Mentat"), [], tmp_config)
    assert fake_connection.privmsgs(ADMIN)[0].startswith("usage: join")
    assert fake_connection.sent("join") == []


def test_part_requires_admin(fake_connection, tmp_config, make_event):
    part(fake_connection, make_event("pubmsg", "tester", "#mentat"), ["#mentat"], tmp_config)
    assert fake_connection.calls == []
    assert tmp_config.has_channel("#mentat")


def test_part_with_default_reason(fake_connection, tmp_config, make_event):
    part(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["#MENTAT"], tmp_config)
    assert fake_connection.sent("part") == [("#MENTAT", "Leaving")]
    assert tmp_config.irc_channels == []


def test_part_without_channel_returns_usage(fake_connection, tmp_config, make_event):
    part(fake_connection, make_event("privmsg", ADMIN, "Mentat"), [], tmp_config)
    assert fake_connection.privmsgs(ADMIN)[0].startswith("usage: part")
    assert fake_connection.sent("part") == []


def test_part_with_reason(fake_connection, tmp_config, make_event):
    part(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["#mentat", "-r", "bye"], tmp_config)
    assert fake_connection.sent("part") == [("#mentat", "bye")]


# estado -------------------------------------------------------------------

def test_estado_requires_admin(fake_connection, tmp_config, make_event):
    estado(fake_connection, make_event("privmsg", "tester", "Mentat"), [], tmp_config)
    assert fake_connection.calls == []


def test_estado_reports_uptime_channels_and_admins(fake_connection, tmp_config, make_event):
    estado(fake_connection, make_event("privmsg", ADMIN, "Mentat"), [], tmp_config)
    lines = fake_connection.privmsgs(ADMIN)
    assert lines[0].startswith("Uptime: ")
    assert lines[1] == "Channels: ['#mentat']"
    assert lines[2] == "Admin users: {'idaho'}"


def test_estado_help(fake_connection, tmp_config, make_event):
    estado(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["-h"], tmp_config)
    assert fake_connection.privmsgs(ADMIN)[0].startswith("usage: estado")


# desconectar / morir ------------------------------------------------------

def test_desconectar_requires_admin(fake_connection, tmp_config, make_event):
    desconectar(fake_connection, make_event("privmsg", "tester", "Mentat"), [], tmp_config)
    assert fake_connection.calls == []


def test_desconectar_disconnects(fake_connection, tmp_config, make_event):
    desconectar(fake_connection, make_event("privmsg", ADMIN, "Mentat"), [], tmp_config)
    assert fake_connection.sent("disconnect") == [("Desconectando...",)]


def test_morir_requires_admin(fake_connection, tmp_config, make_event):
    morir(fake_connection, make_event("privmsg", "tester", "Mentat"), [], tmp_config)
    assert fake_connection.calls == []


def test_morir_disconnects_and_exits(fake_connection, tmp_config, make_event):
    with pytest.raises(SystemExit):
        morir(fake_connection, make_event("privmsg", ADMIN, "Mentat"), [], tmp_config)
    assert fake_connection.sent("disconnect") == [("Ouch!!",)]
