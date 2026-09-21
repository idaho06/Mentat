"""Connection life cycle against the in-process server."""

import logging

from mentat.status import Status


def channel_log(config, channel="mentat"):
    with open(f"{config.logdir}/channel_{channel}.log", encoding="utf-8") as handle:
        return handle.read()


def test_connects_registers_and_joins_configured_channels(driver, live_bot, bot_config, caplog):
    with caplog.at_level(logging.ERROR):
        driver.start()
        assert live_bot.status.get_status() == Status.CONNECTING
        driver.wait_status(Status.CONNECTED)
        driver.wait_joined("#mentat")
    assert live_bot.connection.get_nickname() == "Mentat"
    assert "==> Mentat joined the channel" in channel_log(bot_config)
    assert "failed" not in caplog.text


def test_unknown_umode_command_from_server_is_tolerated(driver, live_bot, caplog):
    # the bot sends "MODE Mentat +In" after the MOTD; this server answers 421
    with caplog.at_level(logging.ERROR):
        driver.connect_and_join()
        driver.run_until(lambda: any(" 421 " in line for line in driver.raw_lines))
    assert live_bot.connection.is_connected()
    assert "failed" not in caplog.text


def test_nick_in_use_falls_back_to_underscore(client_factory, driver, live_bot):
    client_factory("Mentat")  # takes the bot's nick first
    driver.start()
    driver.wait_status(Status.CONNECTED)
    assert live_bot.connection.get_nickname() == "Mentat_"
    driver.wait_joined("#mentat")


def test_other_users_joining_and_leaving_are_logged(driver, client, bot_config):
    driver.connect_and_join()
    client.join("#mentat")
    driver.run_until(lambda: "idaho" in live_users(driver))
    client.send_raw("PART #mentat")
    driver.run_until(lambda: "idaho" not in live_users(driver))
    log = channel_log(bot_config)
    assert "==> idaho joined the channel" in log
    assert "<== idaho parted the channel" in log


def live_users(driver):
    channel = driver.bot.channels.get("#mentat")
    return set(channel.users()) if channel else set()
