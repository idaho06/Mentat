"""A stand-in for irc.client.ServerConnection that records every call."""


class FakeConnection:
    """Records the IRC commands the bot would send, instead of sending them.

    ``calls`` holds ``(method, args)`` tuples in order. It implements every
    ServerConnection method the bot and the commands use.
    """

    def __init__(self, nickname: str = "Mentat"):
        self.nickname = nickname
        self.calls: list[tuple[str, tuple]] = []

    def _record(self, method: str, *args):
        self.calls.append((method, args))

    def get_nickname(self) -> str:
        return self.nickname

    def privmsg(self, target: str, text: str):
        self._record("privmsg", target, text)

    def mode(self, target: str, command: str):
        self._record("mode", target, command)

    def join(self, channel: str, key: str = ""):
        self._record("join", channel)

    def part(self, channels, message: str = ""):
        self._record("part", channels, message)

    def nick(self, newnick: str):
        self._record("nick", newnick)
        self.nickname = newnick

    def disconnect(self, message: str = ""):
        self._record("disconnect", message)

    def sent(self, method: str) -> list[tuple]:
        """Arguments of every recorded call to ``method``."""
        return [args for name, args in self.calls if name == method]

    def privmsgs(self, target: str | None = None) -> list[str]:
        """Texts sent with privmsg, optionally only those to ``target``."""
        return [
            text for to, text in self.sent("privmsg")
            if target is None or to == target
        ]
