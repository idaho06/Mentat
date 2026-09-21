"""Integration fixtures: a real bot talking TCP to an in-process IRC server.

The server is the irc library's own ``irc.server`` (used by its test suite).
It speaks enough IRC for registration, channels and messages; MODE and KICK
are answered with 421 and are injected with ``driver.inject_line`` instead.
The bot, driver and client fixtures come from the root conftest and only
need ``bot_config`` to point at this server.
"""

import threading

import irc.server
import pytest



@pytest.fixture
def irc_server():
    """An IRC server on an ephemeral localhost port, fresh for every test."""
    server = irc.server.IRCServer(("127.0.0.1", 0), irc.server.IRCClient)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def bot_config(tmp_config, irc_server):
    tmp_config.irc_server, tmp_config.irc_port = irc_server.server_address
    return tmp_config
