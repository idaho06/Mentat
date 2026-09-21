"""Tests for the argparse helpers shared by the commands."""

import argparse

import pytest

from mentat.commands.common import BotArgumentParser, parse_or_reply, reply_target


@pytest.fixture
def parser():
    result = BotArgumentParser(description="Test command", prog="cmd")
    result.add_argument("name", choices=["a", "b"])
    result.add_argument("-n", type=int, default=1)
    return result


def test_valid_arguments_return_a_namespace(parser, fake_connection):
    namespace = parse_or_reply(parser, ["a", "-n", "3"], fake_connection, "#c")
    assert namespace == argparse.Namespace(name="a", n=3)
    assert fake_connection.calls == []


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["zz"], "invalid choice"),
        ([], "the following arguments are required"),
        (["a", "-n", "x"], "invalid int value"),
        (["a", "--bogus"], "unrecognized arguments"),
    ],
)
def test_errors_are_sent_back_line_by_line(parser, fake_connection, capsys, argv, expected):
    assert parse_or_reply(parser, argv, fake_connection, "#c") is None
    lines = fake_connection.privmsgs("#c")
    assert lines[0].startswith("usage: cmd")
    assert any(expected in line for line in lines), lines
    assert all(line.strip() for line in lines)  # no blank PRIVMSGs
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_help_is_sent_back_and_never_exits(parser, fake_connection, capsys):
    assert parse_or_reply(parser, ["-h"], fake_connection, "#c") is None
    lines = fake_connection.privmsgs("#c")
    assert lines[0].startswith("usage: cmd")
    assert "Test command" in lines
    assert capsys.readouterr() == ("", "")


def test_custom_type_error_message_is_reported(fake_connection):
    def positive(value):
        raise argparse.ArgumentTypeError("debe ser positivo")

    parser = BotArgumentParser(prog="p")
    parser.add_argument("n", type=positive)
    assert parse_or_reply(parser, ["-1"], fake_connection, "u") is None
    assert any("debe ser positivo" in line for line in fake_connection.privmsgs("u"))


def test_reply_target(make_event):
    assert reply_target(make_event("privmsg", "tester", "Mentat", "hi")) == "tester"
    assert reply_target(make_event("pubmsg", "tester", "#mentat", "hi")) == "#mentat"
