"""Tests for Config: file round trip, CLI precedence, channels, admins, redaction."""

import os

from mentat.config import Config


def make(tmp_path, cli_args, *argv):
    return Config(
        cli_args(*argv),
        configdir=str(tmp_path / "conf"),
        logdir=str(tmp_path / "logs"),
    )


def test_first_run_creates_dirs_and_config_file(tmp_path, cli_args):
    config = make(tmp_path, cli_args, "-p", "nickpass", "-a", "admin")
    assert os.path.isdir(config.configdir)
    assert os.path.isdir(config.logdir)
    # Config.__init__ decides between create and load by this exact path
    assert os.path.exists(config.configfile)
    assert config.irc_password == "nickpass"
    assert config.irc_admin_password == "admin"


def test_first_run_stores_cli_values_and_later_runs_load_them(tmp_path, cli_args):
    make(tmp_path, cli_args, "-p", "nickpass", "-a", "admin")
    reloaded = make(tmp_path, cli_args)
    assert reloaded.irc_password == "nickpass"
    assert reloaded.irc_admin_password == "admin"


def test_cli_overrides_stored_values_without_persisting_them(tmp_path, cli_args):
    make(tmp_path, cli_args, "-a", "admin")
    overridden = make(tmp_path, cli_args, "-a", "other")
    assert overridden.irc_admin_password == "other"
    assert make(tmp_path, cli_args).irc_admin_password == "admin"


def test_reset_recreates_the_config_file(tmp_path, cli_args):
    make(tmp_path, cli_args, "-a", "admin")
    reset = make(tmp_path, cli_args, "--reset", "-a", "new")
    assert reset.irc_admin_password == "new"
    assert make(tmp_path, cli_args).irc_admin_password == "new"


def test_logdir_from_cli_is_created_and_stored(tmp_path, cli_args):
    custom = tmp_path / "custom-logs"
    config = make(tmp_path, cli_args, "-l", str(custom))
    assert config.logdir == str(custom)
    assert custom.is_dir()
    assert make(tmp_path, cli_args).logdir == str(custom)


def test_defaults_when_nothing_is_given(tmp_path, cli_args):
    config = make(tmp_path, cli_args)
    assert config.irc_nick == "Mentat"
    assert config.irc_channels == ["#mentat", "#malos"]
    assert config.irc_password == ""
    assert config.irc_admin_password == ""


def test_instances_do_not_share_mutable_state(tmp_path, cli_args):
    first = make(tmp_path, cli_args)
    second = make(tmp_path, cli_args)
    first.add_channel("#extra")
    first.set_admin("bob")
    assert "#extra" not in second.irc_channels
    assert not second.is_admin("bob")


def test_channel_helpers_fold_irc_case(tmp_config):
    tmp_config.irc_channels = ["#Mentat", "#malos"]
    assert tmp_config.has_channel("#MENTAT")
    assert not tmp_config.has_channel("#nope")

    tmp_config.add_channel("#mentat")
    assert tmp_config.irc_channels == ["#Mentat", "#malos"]
    tmp_config.add_channel("#new")
    assert tmp_config.irc_channels == ["#Mentat", "#malos", "#new"]

    tmp_config.remove_channel("#MALOS")
    tmp_config.remove_channel("#absent")
    assert tmp_config.irc_channels == ["#Mentat", "#new"]
    # plain str is what gets written to the shelve file
    assert all(type(channel) is str for channel in tmp_config.irc_channels)


def test_idaho_is_always_admin_case_insensitively(tmp_config):
    assert tmp_config.is_admin("idaho")
    assert tmp_config.is_admin("IDAHO")
    assert not tmp_config.is_admin("bob")


def test_set_admin_folds_case(tmp_config):
    tmp_config.set_admin("Bob")
    assert tmp_config.is_admin("bob")
    assert tmp_config.is_admin("BOB")


def test_redact_replaces_every_secret(tmp_config):
    text = "NICK Mentat:nickpass and PRIVMSG :login admin"
    assert tmp_config.redact(text) == "NICK Mentat:****** and PRIVMSG :login ******"


def test_redact_ignores_empty_secrets(tmp_path, cli_args):
    config = make(tmp_path, cli_args)
    assert config.redact("nothing to hide") == "nothing to hide"


def test_observa_nicks_defaults_to_empty_list(tmp_path, cli_args):
    config = make(tmp_path, cli_args)
    assert config.observa_nicks == []


def test_add_watched_nick_persists_across_restart(tmp_path, cli_args):
    config = make(tmp_path, cli_args)
    config.add_watched_nick("bob")
    assert make(tmp_path, cli_args).observa_nicks == ["bob"]


def test_add_watched_nick_is_case_insensitive_and_dedups(tmp_config):
    tmp_config.add_watched_nick("Bob")
    tmp_config.add_watched_nick("BOB")
    assert tmp_config.observa_nicks == ["Bob"]


def test_add_watched_nick_refuses_past_the_cap(tmp_config):
    for i in range(30):
        assert tmp_config.add_watched_nick(f"n{i}") is True
    assert tmp_config.add_watched_nick("one-too-many") is False
    assert len(tmp_config.observa_nicks) == 30
    assert "one-too-many" not in tmp_config.observa_nicks


def test_remove_watched_nick_removes_case_insensitively_and_persists(tmp_path, cli_args):
    config = make(tmp_path, cli_args)
    config.add_watched_nick("Bob")
    config.remove_watched_nick("BOB")
    assert config.observa_nicks == []
    assert make(tmp_path, cli_args).observa_nicks == []
    # no-op if absent, must not raise
    config.remove_watched_nick("nosuchnick")


def test_has_watched_nick_is_case_insensitive(tmp_config):
    tmp_config.add_watched_nick("Bob")
    assert tmp_config.has_watched_nick("bob")
    assert tmp_config.has_watched_nick("BOB")
    assert not tmp_config.has_watched_nick("alice")


def test_loading_an_old_configfile_without_observa_nicks_key_does_not_raise(tmp_path, cli_args):
    import shelve

    config = make(tmp_path, cli_args)
    with shelve.open(config.configfile) as db:
        del db["OBSERVA_NICKS"]
    reloaded = make(tmp_path, cli_args)
    assert reloaded.observa_nicks == []


def test_new_config_has_no_nicks_online(tmp_config):
    assert not tmp_config.is_watched_nick_online("bob")


def test_mark_watched_nick_online_then_offline_round_trips(tmp_config):
    tmp_config.mark_watched_nick_online("Bob")
    assert tmp_config.is_watched_nick_online("bob")
    assert tmp_config.is_watched_nick_online("BOB")

    tmp_config.mark_watched_nick_offline("BOB")
    assert not tmp_config.is_watched_nick_online("bob")


def test_clear_watched_nicks_online_empties_the_set(tmp_config):
    tmp_config.mark_watched_nick_online("bob")
    tmp_config.mark_watched_nick_online("alice")
    tmp_config.clear_watched_nicks_online()
    assert not tmp_config.is_watched_nick_online("bob")
    assert not tmp_config.is_watched_nick_online("alice")


def test_watched_nicks_online_is_never_persisted(tmp_path, cli_args):
    config = make(tmp_path, cli_args)
    config.mark_watched_nick_online("bob")
    reloaded = make(tmp_path, cli_args)
    assert not reloaded.is_watched_nick_online("bob")
