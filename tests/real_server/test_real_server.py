"""What only a real server can exercise: MODE, KICK, PART, 433, bad bytes."""

import logging

import pytest

from mentat.status import Status

pytestmark = pytest.mark.real_server


def channel_log(config, channel="mentat"):
    with open(f"{config.logdir}/channel_{channel}.log", encoding="utf-8") as handle:
        return handle.read()


def test_connects_and_joins_without_handler_errors(driver, live_bot, caplog):
    with caplog.at_level(logging.ERROR):
        driver.connect_and_join("#mentat")
    assert live_bot.connection.is_connected()
    assert "failed" not in caplog.text


def test_op_end_to_end(driver, live_bot, client, bot_config):
    driver.connect_and_join("#mentat")  # channel creator, so the bot is +o
    client.join("#mentat")
    client.say("#mentat", "Mentat: op")
    client.wait_for(lambda line: line.startswith(":Mentat!") and "MODE #mentat +o idaho" in line)
    driver.run_until(lambda: live_bot.channels["#mentat"].is_oper("idaho"))
    assert "*** Mentat sets mode: +o idaho" in channel_log(bot_config)


def test_real_kick_forgets_the_channel(driver, live_bot, client, bot_config):
    driver.connect_and_join("#mentat")
    client.join("#mentat")
    client.say("#mentat", "Mentat: op")
    driver.run_until(lambda: live_bot.channels["#mentat"].is_oper("idaho"))
    client.send_raw("KICK #mentat Mentat :bye")
    driver.run_until(lambda: "#mentat" not in live_bot.channels)
    assert not bot_config.has_channel("#mentat")
    assert "<=* idaho has kicked Mentat: bye" in channel_log(bot_config)


def test_real_part_with_reason(driver, live_bot, client, bot_config):
    driver.connect_and_join("#mentat")
    client.say("Mentat", "join #other")
    driver.wait_joined("#other")
    client.say("Mentat", "part #other -r bye")
    driver.run_until(lambda: "#other" not in live_bot.channels)
    assert bot_config.irc_channels == ["#mentat"]


def test_nick_in_use_falls_back_to_underscore(client_factory, driver, live_bot):
    client_factory("Mentat")
    driver.start()
    driver.wait_status(Status.CONNECTED)
    assert live_bot.connection.get_nickname() == "Mentat_"
    driver.wait_joined("#mentat")


def test_invalid_utf8_from_a_user_does_not_kill_the_bot(driver, live_bot, client):
    driver.connect_and_join("#mentat")
    client.join("#mentat")
    client.send_bytes(b"PRIVMSG #mentat :Mentat: hola -n Jos\xe9")
    reply = client.expect_privmsg("Mentat", "#mentat")
    assert reply.startswith("Hola, Jos")
    assert live_bot.connection.is_connected()


def test_desconectar_is_seen_as_a_quit(driver, live_bot, client):
    driver.connect_and_join("#mentat")
    client.join("#mentat")
    client.say("Mentat", "desconectar")
    driver.run_until(lambda: not live_bot.connection.is_connected())
    assert live_bot.status.get_status() == Status.CONNECTING
    client.wait_for(lambda line: line.startswith(":Mentat!") and "QUIT" in line)
