"""This is the desconectar command module."""

# import io
# import sys
# import logging
# import argparse
from irc.client import ServerConnection
from mentat.config import Config


def desconectar(connection: ServerConnection, event, args, config: Config):
    """Disconnect from the server."""
    if not config.is_admin(event.source.nick):
        return
    # We ignore the args. To be implemented in the future.
    connection.disconnect("Desconectando...")
