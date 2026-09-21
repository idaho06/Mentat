"""Opt-in suite against a real IRC server (ngircd from docker-compose.test.yml).

Set ``MENTAT_TEST_IRC=host:port`` to run it; otherwise every test marked
``real_server`` is skipped. The bot, driver and client fixtures come from
the root conftest.
"""

import os
import socket
import time

import pytest

ENV_VAR = "MENTAT_TEST_IRC"


def pytest_collection_modifyitems(config, items):  # pylint: disable=unused-argument
    if os.environ.get(ENV_VAR):
        return
    skip = pytest.mark.skip(reason=f"set {ENV_VAR}=host:port to run real-server tests")
    for item in items:
        if "real_server" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def real_server_address():
    """(host, port) from the env var, once the port accepts connections."""
    host, _, port = os.environ[ENV_VAR].rpartition(":")
    address = (host or "127.0.0.1", int(port))
    deadline = time.monotonic() + 15
    while True:
        try:
            socket.create_connection(address, timeout=1).close()
            return address
        except OSError:
            if time.monotonic() > deadline:
                pytest.fail(f"no IRC server listening at {address[0]}:{address[1]}")
            time.sleep(0.5)


@pytest.fixture
def bot_config(tmp_config, real_server_address):
    tmp_config.irc_server, tmp_config.irc_port = real_server_address
    return tmp_config
