import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from dsbridge.database import Database
from dsbridge.discord_bot import DiscordBot
from dsbridge.server import Server


class DSBridge:
    def __init__(
        self,
        discord_token: str,
        database_engine: AsyncEngine,
        on_change=None,
        banned_words: list[str] | None = None,
        display_name=None,
    ):
        """
        Build the bridge and its dependencies.

        Args:
            discord_token: Token used to authenticate the Discord bot.
            database_engine: An async SQLAlchemy engine owned by the host application.
                The bridge uses it for its own sessions but never disposes it.
            on_change: Optional awaitable called with a payload describing every
                change that originated on Discord, so the host can broadcast it.
            banned_words: Words to strip from messages.
            display_name: Optional callable taking a host user id and returning the
                name to show on Discord. May be a coroutine function. Users belong
                to the host application, so the bridge stores only their ids.
        """
        self.database = Database(database_engine)
        self.server_bot = Server(
            session=self.database.session, on_change=on_change, display_name=display_name
        )
        self.discord_bot = DiscordBot(
            discord_token=discord_token,
            banned_words=banned_words,
        )

        self.server_bot.init_bot(self.discord_bot)
        self.discord_bot.init_bot(self.server_bot)

    async def start(self):
        """
        Create any missing tables and run the Discord bot until it stops.

        The caller's engine is left open; only the bridge's own sessions are released.
        """
        logging.info('Starting DSBridge')

        await self.database.create_all()

        try:
            await self.discord_bot.start()
        finally:
            await self.database.close()
