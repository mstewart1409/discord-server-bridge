import asyncio
import logging

from dsbridge.database import Database
from dsbridge.discord_bot import DiscordBot
from dsbridge.server import Server


class DSBridge:
    def __init__(self, discord_token: str, app_secret_key: str, server_namespace: str,
                 host_url: str, database_uri: str, banned_words: list[str] | None = None,
                 database_echo: bool = False):
        """
        Build the bridge and its dependencies.

        Args:
            discord_token: Token used to authenticate the Discord bot.
            app_secret_key: Shared secret used to sign requests to the server.
            server_namespace: Socket.IO namespace to join on the server.
            host_url: Host of the server, without the scheme.
            database_uri: SQLAlchemy database URI.
            banned_words: Words to strip from messages.
            database_echo: Whether SQLAlchemy should log emitted SQL.
        """
        self.database = Database(database_uri, echo=database_echo)
        self.server_bot = Server(
            namespace=server_namespace,
            host_url=host_url,
            app_secret_key=app_secret_key,
            session=self.database.session,
        )
        self.discord_bot = DiscordBot(
            discord_token=discord_token,
            banned_words=banned_words,
        )

        self.server_bot.init_bot(self.discord_bot)
        self.discord_bot.init_bot(self.server_bot)

    async def start(self):
        """
        Create any missing tables and run both bots until they stop.
        """
        logging.info('Starting DSBridge')

        self.database.create_all()

        await asyncio.gather(
            self.discord_bot.start(),
            self.server_bot.start(),
        )
