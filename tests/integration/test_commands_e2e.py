"""Commands sent by a real user over TCP and answered by the bot."""

import pytest

from mentat.status import Status


@pytest.fixture
def connected(driver):
    driver.connect_and_join("#mentat")
    return driver


def test_hola_in_channel(connected, client):
    client.join("#mentat")
    client.say("#mentat", "Mentat: hola")
    assert client.expect_privmsg("Mentat", "#mentat") == "Hola, idaho"


def test_hola_in_private_with_argument(connected, client):
    client.say("Mentat", "hola -n Bob")
    assert client.expect_privmsg("Mentat", "idaho") == "Hola, Bob"


def test_unknown_command_gets_usage_in_private(connected, client):
    client.say("Mentat", "nosuch")
    assert client.expect_privmsg("Mentat", "idaho").startswith("usage: Mentat:")


def test_login_then_estado(connected, client_factory, bot_config):
    tester = client_factory("tester")
    tester.say("Mentat", "estado")
    tester.say("Mentat", "login wrong")
    assert tester.expect_privmsg("Mentat", "tester") == "Wrong password"
    tester.say("Mentat", "login admin")
    assert tester.expect_privmsg("Mentat", "tester") == "Welcome, tester"
    assert bot_config.is_admin("tester")

    tester.say("Mentat", "estado")
    assert tester.expect_privmsg("Mentat", "tester").startswith("Uptime: ")
    assert tester.expect_privmsg("Mentat", "tester") == "Channels: ['#mentat']"


def test_join_and_part_update_bot_and_config(connected, client, live_bot, bot_config, irc_server):
    client.say("Mentat", "join #other")
    connected.wait_joined("#other")
    assert bot_config.irc_channels == ["#mentat", "#other"]
    assert "#other" in irc_server.channels

    client.say("Mentat", "part #other -r bye")
    # this server cannot parse "PART #other bye" (it answers 403), so only
    # the bot side is checked here; the real-server suite sees the real PART
    connected.run_until(lambda: any(" 403 #other" in line for line in connected.raw_lines))
    assert bot_config.irc_channels == ["#mentat"]


def test_observa_bare_reports_online_watched_nicks_end_to_end(connected, client, bot_config):
    client.say("Mentat", "observa pon bob")
    connected.run_until(lambda: bot_config.has_watched_nick("bob"))

    connected.inject_line(":localhost 604 Mentat bob u h 123 :is online")
    client.say("Mentat", "observa")
    assert client.expect_privmsg("Mentat", "idaho") == "bob"


def test_dados(connected, client):
    client.say("Mentat", "dados -d 6 -n 2")
    total = client.expect_privmsg("Mentat", "idaho")
    throws = client.expect_privmsg("Mentat", "idaho")
    assert total.startswith("Total:   ")
    assert throws.startswith("Tiradas: [") and throws.count(",") == 1
    assert int(total.split()[-1]) == sum(int(x) for x in throws[len("Tiradas: ["):-1].split(","))


def test_desconectar_quits_and_marks_reconnecting(connected, client, live_bot):
    client.join("#mentat")
    client.say("Mentat", "desconectar")
    connected.run_until(lambda: not live_bot.connection.is_connected())
    assert live_bot.status.get_status() == Status.CONNECTING
    client.wait_for(lambda line: line.startswith(":Mentat!") and "QUIT :Desconectando..." in line)


def test_morir_exits_the_process(connected, client, live_bot):
    client.say("Mentat", "morir")
    with pytest.raises(SystemExit):
        connected.run_until(lambda: False, timeout=5)
    assert not live_bot.connection.is_connected()


def test_command_error_is_reported_and_bot_survives(connected, client, live_bot, monkeypatch):
    from mentat import bot as botmod  # pylint: disable=import-outside-toplevel

    monkeypatch.setitem(botmod.COMMANDS, "hola", lambda *_: 1 / 0)
    client.say("Mentat", "hola")
    assert client.expect_privmsg("Mentat", "idaho") == "Error ejecutando el comando"
    client.say("Mentat", "dados")
    assert client.expect_privmsg("Mentat", "idaho").startswith("Total:")
    assert live_bot.connection.is_connected()
