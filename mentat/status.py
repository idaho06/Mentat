"""This module contains the class that defines the current status of the bot."""

import logging


class Status:
    """Class that defines the current status of the bot.

    The status is driven by IRC events, and the real sequence of events is
    not always the one we expect (registered nick vs free nick, server
    reconnects, ...), so an unexpected transition is logged and ignored
    rather than raised: an exception here would be raised inside an IRC
    event handler and kill the bot.
    """

    INIT = "INIT"
    CONNECTING = "CONNECTING"
    CONNECTING_AUTHENTICATING = "CONNECTING_AUTHENTICATING"
    CONNECTED = "CONNECTED"

    # action -> {current status: next status}
    TRANSITIONS = {
        "connect": {
            INIT: CONNECTING,
        },
        "authenticate": {
            CONNECTING: CONNECTING_AUTHENTICATING,
        },
        "connected": {
            # a free nick is welcomed without the 433 / authenticate step
            CONNECTING: CONNECTED,
            CONNECTING_AUTHENTICATING: CONNECTED,
        },
        # SingleServerIRCBot reconnects on its own after any disconnect
        # (without going through Mentat.start), so a disconnect means
        # "connecting again", whatever the previous status was.
        "disconnect": {
            CONNECTING: CONNECTING,
            CONNECTING_AUTHENTICATING: CONNECTING,
            CONNECTED: CONNECTING,
        },
    }

    def __init__(self):
        """Initialize the status."""
        self._status = Status.INIT
        logging.debug("Status initialized to %s", self._status)

    def transition(self, action: str) -> bool:
        """Apply ``action`` to the current status.

        Returns True if the status changed, False (and logs a warning) if
        the action is unknown or not valid from the current status.
        """
        next_status = self.TRANSITIONS.get(action, {}).get(self._status)
        if next_status is None:
            logging.warning(
                "Ignoring invalid status transition %r from %s", action, self._status
            )
            return False
        self._status = next_status
        logging.debug("Status changed to %s", self._status)
        return True

    def get_status(self) -> str:
        """Return the current status."""
        return self._status
