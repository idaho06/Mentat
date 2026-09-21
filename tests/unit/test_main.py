"""Tests for the command line entry point."""

import logging
import os

import pytest

from mentat import __main__ as entry
from mentat.logger import SecretFilter


def test_parser_defaults():
    args = entry.build_parser().parse_args([])
    assert vars(args) == {
        "password": "",
        "admin_password": "",
        "logdir": "",
        "reset": False,
        "create_config_and_exit": False,
        "debug": "WARNING",
        "erroroutput": "stderr",
    }


def test_parser_short_options():
    args = entry.build_parser().parse_args(
        ["-p", "np", "-a", "ap", "-l", "/x", "-d", "DEBUG", "-o", "/tmp/e", "--reset"]
    )
    assert (args.password, args.admin_password, args.logdir) == ("np", "ap", "/x")
    assert (args.debug, args.erroroutput, args.reset) == ("DEBUG", "/tmp/e", True)


@pytest.mark.parametrize(
    "debug, erroroutput, level, filename",
    [
        ("DEBUG", "stderr", logging.DEBUG, None),
        ("INFO", "/tmp/errors.log", logging.INFO, "/tmp/errors.log"),
        ("BOGUS", "stderr", logging.WARNING, None),
    ],
)
def test_configure_logging(monkeypatch, debug, erroroutput, level, filename):
    seen = {}
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: seen.update(kwargs))
    entry.configure_logging(entry.build_parser().parse_args(["-d", debug, "-o", erroroutput]))
    assert seen["level"] == level
    assert seen["filename"] == filename


@pytest.fixture
def user_dirs(tmp_path, monkeypatch):
    """Point appdirs at tmp_path so main() never touches the real config."""
    monkeypatch.setattr("mentat.config.user_config_dir", lambda _: str(tmp_path / "conf"))
    monkeypatch.setattr("mentat.config.user_log_dir", lambda _: str(tmp_path / "logs"))
    return tmp_path


def test_create_config_and_exit(user_dirs, monkeypatch):
    def never(_self):
        raise AssertionError("start() must not run")

    monkeypatch.setattr(entry.Mentat, "start", never)
    assert entry.main(["--create-config-and-exit", "-a", "secret"]) == 0
    assert os.path.exists(user_dirs / "conf" / "mentat.conf")
    assert os.path.isdir(user_dirs / "logs")
    assert any(
        isinstance(f, SecretFilter) for h in logging.getLogger().handlers for f in h.filters
    )


def test_main_starts_the_bot(user_dirs, monkeypatch):
    started = []
    monkeypatch.setattr(entry.Mentat, "start", lambda self: started.append(self))
    assert entry.main([]) == 0
    assert len(started) == 1
    assert started[0].config.configdir == str(user_dirs / "conf")


def test_importing_the_module_does_not_run_main():
    # the guard is the only caller of main(); importing must be side-effect free
    assert callable(entry.main)
