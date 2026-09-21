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
