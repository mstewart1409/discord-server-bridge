import logging

from dsbridge.database import Database
from dsbridge.discord_bot import DiscordBot
from dsbridge.server import Server


class DSBridge:
    def __init__(
        self,
        discord_token: str,
        database_uri: str,
        on_change=None,
        banned_words: list[str] | None = None,
        database_echo: bool = False,
        database_pool_size: int | None = None,
        database_max_overflow: int | None = None,
    ):
        """
        Build the bridge and its dependencies.

        Args:
            discord_token: Token used to authenticate the Discord bot.
            database_uri: SQLAlchemy database URI naming an asyncio driver.
            on_change: Optional awaitable called with a payload describing every
                change that originated on Discord, so the host can broadcast it.
            banned_words: Words to strip from messages.
            database_echo: Whether SQLAlchemy should log emitted SQL.
            database_pool_size: Connections to keep open in the pool. Defaults to SQLAlchemy's.
            database_max_overflow: Connections allowed beyond the pool size. Defaults to
                SQLAlchemy's.
        """
        self.database = Database(
            database_uri,
            echo=database_echo,
            pool_size=database_pool_size,
            max_overflow=database_max_overflow,
        )
        self.server_bot = Server(session=self.database.session, on_change=on_change)
        self.discord_bot = DiscordBot(
            discord_token=discord_token,
            banned_words=banned_words,
        )

        self.server_bot.init_bot(self.discord_bot)
        self.discord_bot.init_bot(self.server_bot)

    async def start(self):
        """
        Create any missing tables and run the Discord bot until it stops.
        """
        logging.info('Starting DSBridge')

        await self.database.create_all()

        try:
            await self.discord_bot.start()
        finally:
            await self.database.dispose()
