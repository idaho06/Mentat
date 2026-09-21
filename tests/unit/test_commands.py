"""Tests for every command, called directly with a fake connection."""

import pytest

from mentat.commands.dados import dados
from mentat.commands.desconectar import desconectar
from mentat.commands.estado import estado
from mentat.commands.hola import hola
from mentat.commands.join import join
from mentat.commands.login import login
from mentat.commands.morir import morir
from mentat.commands.observa import observa
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


# observa --------------------------------------------------------------------

def test_observa_requires_admin(fake_connection, tmp_config, make_event):
    observa(fake_connection, make_event("privmsg", "tester", "Mentat"), ["pon", "bob"], tmp_config)
    assert fake_connection.calls == []
    assert tmp_config.observa_nicks == []


def test_observa_pon_adds_the_nick_and_sends_watch(fake_connection, tmp_config, make_event):
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["pon", "bob"], tmp_config)
    assert tmp_config.observa_nicks == ["bob"]
    assert fake_connection.sent("send_raw") == [("WATCH +bob",)]


def test_observa_pon_missing_nick_shows_usage(fake_connection, tmp_config, make_event):
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["pon"], tmp_config)
    assert fake_connection.privmsgs(ADMIN)[0].startswith("usage: observa pon")
    assert fake_connection.sent("send_raw") == []


def test_observa_pon_refuses_past_the_cap_and_replies(fake_connection, tmp_config, make_event):
    for i in range(30):
        observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["pon", f"n{i}"], tmp_config)
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["pon", "one-too-many"], tmp_config)
    assert len(tmp_config.observa_nicks) == 30
    assert "one-too-many" not in tmp_config.observa_nicks
    assert ("WATCH +one-too-many",) not in fake_connection.sent("send_raw")
    assert "30" in fake_connection.privmsgs(ADMIN)[-1]


def test_observa_quita_removes_the_nick_and_unwatches(fake_connection, tmp_config, make_event):
    tmp_config.add_watched_nick("bob")
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["quita", "bob"], tmp_config)
    assert tmp_config.observa_nicks == []
    assert ("WATCH -bob",) in fake_connection.sent("send_raw")


def test_observa_quita_of_an_absent_nick_still_sends_watch_minus(fake_connection, tmp_config, make_event):
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["quita", "nosuchnick"], tmp_config)
    assert fake_connection.sent("send_raw") == [("WATCH -nosuchnick",)]


def test_observa_quita_missing_nick_shows_usage(fake_connection, tmp_config, make_event):
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["quita"], tmp_config)
    assert fake_connection.privmsgs(ADMIN)[0].startswith("usage: observa quita")
    assert fake_connection.sent("send_raw") == []


def test_observa_unknown_subcommand_replies_an_error(fake_connection, tmp_config, make_event):
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["nope"], tmp_config)
    assert fake_connection.privmsgs(ADMIN) == ["Subcomando desconocido: nope"]
    assert fake_connection.sent("send_raw") == []


def test_observa_dash_h_shows_usage_instead_of_unknown_subcommand(fake_connection, tmp_config, make_event):
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["-h"], tmp_config)
    assert fake_connection.privmsgs(ADMIN)[0].startswith("usage: observa")
    assert fake_connection.sent("send_raw") == []


def test_observa_dash_dash_help_shows_usage_instead_of_unknown_subcommand(fake_connection, tmp_config, make_event):
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["--help"], tmp_config)
    assert fake_connection.privmsgs(ADMIN)[0].startswith("usage: observa")
    assert fake_connection.sent("send_raw") == []


def test_observa_lista_shows_the_full_configured_list(fake_connection, tmp_config, make_event):
    tmp_config.add_watched_nick("bob")
    tmp_config.add_watched_nick("alice")
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["lista"], tmp_config)
    assert fake_connection.privmsgs(ADMIN) == ["bob, alice"]


def test_observa_lista_when_empty(fake_connection, tmp_config, make_event):
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), ["lista"], tmp_config)
    assert fake_connection.privmsgs(ADMIN) == ["No hay nicks vigilados"]


def test_observa_bare_shows_only_online_watched_nicks(fake_connection, tmp_config, make_event):
    tmp_config.add_watched_nick("bob")
    tmp_config.add_watched_nick("alice")
    tmp_config.mark_watched_nick_online("bob")
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), [], tmp_config)
    assert fake_connection.privmsgs(ADMIN) == ["bob"]


def test_observa_bare_when_none_online(fake_connection, tmp_config, make_event):
    tmp_config.add_watched_nick("bob")
    observa(fake_connection, make_event("privmsg", ADMIN, "Mentat"), [], tmp_config)
    assert fake_connection.privmsgs(ADMIN) == ["Ningún nick vigilado está conectado"]
