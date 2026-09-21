"""Events the in-process server cannot produce, injected as raw server lines.

They still go through the irc library parser and its own channel tracking,
so this checks Mentat's handlers together with the library's bookkeeping.
"""

import os

from mentat.status import Status

SPANISH_433 = (
    ":localhost 433 Mentat :El nick está registrado, tienes que indicar la "
    "contraseña para usarlo: /nick Mentat:contraseña"
)


def channel_log(config, channel="mentat"):
    with open(f"{config.logdir}/channel_{channel}.log", encoding="utf-8") as handle:
        return handle.read()


def test_kick_removes_the_channel_everywhere(driver, live_bot, bot_config):
    driver.connect_and_join("#mentat")
    driver.inject_line(":idaho!idaho@localhost KICK #mentat Mentat :bye")
    assert "#mentat" not in live_bot.channels
    assert not bot_config.has_channel("#mentat")
    assert "<=* idaho has kicked Mentat: bye" in channel_log(bot_config)


def test_kick_of_someone_else_is_only_logged(driver, live_bot, bot_config):
    driver.connect_and_join("#mentat")
    driver.inject_line(":bob!bob@localhost JOIN #mentat")
    driver.inject_line(":idaho!idaho@localhost KICK #mentat bob :out")
    assert "#mentat" in live_bot.channels
    assert bot_config.has_channel("#mentat")
    assert "<=* idaho has kicked bob: out" in channel_log(bot_config)


def test_channel_mode_is_logged_and_tracked(driver, live_bot, bot_config):
    driver.connect_and_join("#mentat")
    driver.inject_line(":idaho!idaho@localhost JOIN #mentat")
    driver.inject_line(":idaho!idaho@localhost MODE #mentat +o Mentat")
    assert live_bot.channels["#mentat"].is_oper("Mentat")
    assert "*** idaho sets mode: +o Mentat" in channel_log(bot_config)


def test_user_mode_is_logged(driver, bot_config):
    driver.connect_and_join("#mentat")
    driver.inject_line(":Mentat MODE Mentat :+In")
    with open(f"{bot_config.logdir}/mode_changes.log", encoding="utf-8") as handle:
        assert "*** Mentat sets mode: +In" in handle.read()


def test_registered_nick_sends_the_password_on_the_wire(driver, live_bot):
    driver.start()  # status CONNECTING, NICK/USER sent, nothing read yet
    driver.inject_line(SPANISH_433)
    assert live_bot.status.get_status() == Status.CONNECTING_AUTHENTICATING
    # the bot answered with "NICK Mentat:nickpass"; this server rejects a
    # nick with a colon (432), and the original registration stands
    driver.run_until(lambda: any(" 432 " in line for line in driver.raw_lines))
    driver.wait_status(Status.CONNECTED)
    assert live_bot.connection.get_nickname() == "Mentat"


def test_quit_of_another_user_is_logged_to_every_channel_they_were_in(driver, live_bot, bot_config):
    driver.connect_and_join("#mentat")
    nick = live_bot.connection.get_nickname()
    driver.inject_line(f":{nick}!{nick}@localhost JOIN #other")
    driver.inject_line(":bob!bob@localhost JOIN #mentat")
    driver.inject_line(":bob!bob@localhost JOIN #other")
    driver.inject_line(":bob!bob@localhost QUIT :gone fishing")
    assert "<<< bob has quit: gone fishing" in channel_log(bot_config)
    assert "<<< bob has quit: gone fishing" in channel_log(bot_config, "other")
    # the library's own bookkeeping still removes bob everywhere
    assert not live_bot.channels["#mentat"].has_user("bob")
    assert not os.path.exists(f"{bot_config.logdir}/nick_bob.log")


def test_quit_of_a_user_in_no_known_channels_writes_nothing(driver, bot_config):
    driver.connect_and_join("#mentat")
    driver.inject_line(":bob!bob@localhost QUIT :gone fishing")
    assert not os.path.exists(f"{bot_config.logdir}/nick_bob.log")
    assert "bob" not in channel_log(bot_config)


def test_away_notify_is_logged_for_a_watched_nick(driver, live_bot, bot_config):
    bot_config.add_watched_nick("bob")
    driver.connect_and_join("#mentat")
    driver.inject_line(":bob!bob@localhost AWAY :gone fishing")
    driver.inject_line(":bob!bob@localhost AWAY")
    with open(f"{bot_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        content = handle.read()
    assert "bob is away: gone fishing" in content
    assert "bob is back" in content


def test_rpl_away_301_is_not_confused_with_away_notify(driver, live_bot, bot_config):
    bot_config.add_watched_nick("bob")
    driver.connect_and_join("#mentat")
    driver.inject_line(":localhost 301 Mentat bob :gone fishing")
    assert not os.path.exists(f"{bot_config.logdir}/nick_bob.log")


def test_chghost_is_logged_for_a_watched_nick(driver, live_bot, bot_config):
    bot_config.add_watched_nick("bob")
    driver.connect_and_join("#mentat")
    driver.inject_line(":bob!bob@localhost CHGHOST newident newhost")
    with open(f"{bot_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        assert "newident@newhost" in handle.read()


def test_watch_numerics_via_injected_lines(driver, live_bot, bot_config):
    bot_config.add_watched_nick("bob")
    driver.connect_and_join("#mentat")

    driver.inject_line(":localhost 600 Mentat bob u h 123 :logged online")
    assert bot_config.is_watched_nick_online("bob")

    driver.inject_line(":localhost 601 Mentat bob u h 123 :logged offline")
    assert not bot_config.is_watched_nick_online("bob")

    driver.inject_line(":localhost 604 Mentat bob u h 123 :is online")
    assert bot_config.is_watched_nick_online("bob")

    driver.inject_line(":localhost 605 Mentat bob :is offline")
    assert not bot_config.is_watched_nick_online("bob")

    with open(f"{bot_config.logdir}/nick_bob.log", encoding="utf-8") as handle:
        content = handle.read()
    assert content.count("has connected") == 2
    assert content.count("has disconnected") == 2
