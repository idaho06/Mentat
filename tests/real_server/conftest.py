"""Opt-in suite against a real IRC server (ngircd from docker-compose.test.yml).

Set ``MENTAT_TEST_IRC=host:port`` to run it; otherwise every test marked
``real_server`` is skipped. The bot, driver and client fixtures come from
the root conftest.
"""

import itertools
import os
import socket
import time

import pytest

from tests.helpers.ircclient import RawIRCClient

ENV_VAR = "MENTAT_TEST_IRC"
TEST_NICKS = ["Mentat", "Mentat_", "idaho", "tester"]
_probe_ids = itertools.count(1)


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


def wait_until_nicks_are_free(address, nicks, timeout=15.0):
    """Block until none of ``nicks`` is online, asking the server with ISON.

    A real server may keep the previous test's users registered for a
    moment after their QUIT (ngircd delays reading from a connection while
    a command penalty is pending), which would give the next bot a 433.
    """
    probe = RawIRCClient(*address)
    try:
        probe.register(f"probe{next(_probe_ids)}")
        deadline = time.monotonic() + timeout
        while True:
            probe.send_raw("ISON " + " ".join(nicks))
            reply = probe.wait_for(lambda line: " 303 " in line)
            online = reply.split(" :", 1)[1].split() if " :" in reply else []
            if not online:
                return
            if time.monotonic() > deadline:
                pytest.fail(f"nicks still online after {timeout}s: {online}")
            time.sleep(0.2)
    finally:
        probe.quit()


@pytest.fixture
def bot_config(tmp_config, real_server_address):
    wait_until_nicks_are_free(real_server_address, TEST_NICKS)
    tmp_config.irc_server, tmp_config.irc_port = real_server_address
    return tmp_config
