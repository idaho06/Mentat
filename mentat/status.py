"""This module contains the class that defines the current status of the bot."""

import logging

class Status(object):
    """Class that defines the current status of the bot."""

    INIT = "INIT"
    CONNECTING = "CONNECTING"
    CONNECTING_AUTHENTICATING = "CONNECTING_AUTHENTICATING"
    CONNECTED = "CONNECTED"

    def __init__(self):
        """Initialize the status."""
        self._status = Status.INIT
        logging.debug("Status initialized to %s", self._status)

    def transition(self, action: str):
        """Change the status of the bot."""
        if action == "connect":
            if self._status == Status.INIT:
                self._status = Status.CONNECTING
                logging.debug("Status changed to %s", self._status)
            else:
                raise ValueError("Invalid action")
        elif action == "authenticate":
            if self._status == Status.CONNECTING or self._status == Status.INIT:
                self._status = Status.CONNECTING_AUTHENTICATING
                logging.debug("Status changed to %s", self._status)
            else:
                raise ValueError("Invalid action")
        elif action == "connected":
            if self._status == Status.CONNECTING_AUTHENTICATING:
                self._status = Status.CONNECTED
                logging.debug("Status changed to %s", self._status)
            else:
                raise ValueError("Invalid action")
        elif action == "disconnect":
            if self._status == Status.CONNECTED:
                self._status = Status.INIT
                logging.debug("Status changed to %s", self._status)
            else:
                raise ValueError("Invalid action")
        else:
            raise ValueError("Invalid action")

    def get_status(self) -> str:
        """Return the current status."""
        return self._status
