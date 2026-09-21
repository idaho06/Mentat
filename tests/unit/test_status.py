"""Tests for the Status transition table."""

import logging

from mentat.status import Status


def test_initial_status_is_init():
    assert Status().get_status() == Status.INIT


def test_registered_nick_path():
    status = Status()
    assert status.transition("connect")
    assert status.get_status() == Status.CONNECTING
    assert status.transition("authenticate")
    assert status.get_status() == Status.CONNECTING_AUTHENTICATING
    assert status.transition("connected")
    assert status.get_status() == Status.CONNECTED


def test_free_nick_is_welcomed_without_authenticating():
    status = Status()
    status.transition("connect")
    assert status.transition("connected")
    assert status.get_status() == Status.CONNECTED


def test_disconnect_goes_back_to_connecting_from_any_live_state():
    for path in (["connect"], ["connect", "authenticate"], ["connect", "connected"]):
        status = Status()
        for action in path:
            status.transition(action)
        assert status.transition("disconnect"), path
        assert status.get_status() == Status.CONNECTING


def test_invalid_transition_is_ignored_and_logged(caplog):
    status = Status()
    with caplog.at_level(logging.WARNING):
        assert not status.transition("connected")
        assert not status.transition("no-such-action")
    assert status.get_status() == Status.INIT
    assert "Ignoring invalid status transition 'connected' from INIT" in caplog.text
    assert "'no-such-action'" in caplog.text


def test_authenticate_twice_is_invalid():
    status = Status()
    status.transition("connect")
    status.transition("authenticate")
    assert not status.transition("authenticate")
    assert status.get_status() == Status.CONNECTING_AUTHENTICATING
