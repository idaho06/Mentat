"""Fixtures shared by every test: no network, everything under tmp_path."""

import logging

import pytest
from irc.client import Event, NickMask

from mentat.__main__ import build_parser
from mentat.bot import Mentat
from mentat.config import Config
from tests.helpers.driver import BotDriver, NoReconnect
from tests.helpers.fake_connection import FakeConnection
from tests.helpers.ircclient import RawIRCClient


@pytest.fixture(autouse=True)
def _restore_root_handler_filters():
    """main() adds a SecretFilter to every root handler (including pytest's
    capture handler); make sure that never leaks into the next test."""
    root = logging.getLogger()
    saved = {id(h): list(h.filters) for h in root.handlers}
    yield
    for handler in root.handlers:
        if id(handler) in saved:
            handler.filters = saved[id(handler)]


@pytest.fixture
def cli_args():
    """Parse a command line exactly as ``python -m mentat`` would."""
    def _parse(*argv: str):
        return build_parser().parse_args(list(argv))
    return _parse


@pytest.fixture
def tmp_config(tmp_path, cli_args) -> Config:
    """A Config whose config file and logs live under tmp_path."""
    config = Config(
        cli_args("-p", "nickpass", "-a", "admin"),
        configdir=str(tmp_path / "conf"),
        logdir=str(tmp_path / "logs"),
    )
    config.irc_channels = ["#mentat"]
    return config


@pytest.fixture
def fake_connection() -> FakeConnection:
    return FakeConnection()


@pytest.fixture
def make_event():
    """Build an irc.client.Event like the ones the library parser produces."""
    def _make(type="pubmsg", nick="tester", target="#mentat", text=None, arguments=None):
        if arguments is None:
            arguments = [text] if text is not None else []
        return Event(type, NickMask(f"{nick}!{nick}@localhost"), target, arguments)
    return _make


@pytest.fixture
def bot(tmp_config, fake_connection) -> Mentat:
    """An offline Mentat whose outgoing traffic goes to ``fake_connection``."""
    mentat = Mentat(tmp_config)
    mentat.recon = NoReconnect()
    mentat.connection = fake_connection
    return mentat


# Live fixtures. They need a ``bot_config`` fixture pointing at a server,
# which each integration directory defines (in-process server or the real
# one named by MENTAT_TEST_IRC).


@pytest.fixture
def live_bot(bot_config):
    """A Mentat wired to a server, never started with start()."""
    mentat = Mentat(bot_config)
    mentat.recon = NoReconnect()
    yield mentat
    if mentat.connection.is_connected():
        mentat.connection.disconnect("test over")
    for _ in range(2):
        mentat.reactor.process_once(0)


@pytest.fixture
def driver(live_bot):
    return BotDriver(live_bot)


@pytest.fixture
def client_factory(bot_config, driver):
    """Registers extra users on the server; they are closed on teardown."""
    clients = []

    def make(nick: str) -> RawIRCClient:
        client = RawIRCClient(bot_config.irc_server, bot_config.irc_port, driver=driver)
        clients.append(client)
        client.register(nick)
        return client

    yield make
    for client in clients:
        client.quit()


@pytest.fixture
def client(client_factory):
    """The admin user ``idaho`` (always admin in Config), registered."""
    return client_factory("idaho")
