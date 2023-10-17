# import io
# import sys
# import logging
# import argparse
from mentat.config import Config
from irc.client import ServerConnection


def desconectar(connection: ServerConnection, event, args, config: Config):
    """Disconnect from the server."""
    if config.is_admin(event.source.nick) == False:
        return
    # We ignore the args. To be implemented in the future.
    connection.disconnect("Desconectando...")
    