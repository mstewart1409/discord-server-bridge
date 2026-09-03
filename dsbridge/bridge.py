import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from dsbridge.database import Database
from dsbridge.discord_bot import DiscordBot
from dsbridge.models import ChatChannels
from dsbridge.models import Message
from dsbridge.server import Server


class DSBridge:
    def __init__(
        self,
        discord_token: str,
        database_engine: AsyncEngine,
        on_change=None,
        banned_words: list[str] | None = None,
        display_name=None,
        message_model=Message,
        channel_model=ChatChannels,
        create_tables: bool = True,
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
            message_model: The mapped class holding the messages, built from
                ``MessageMixin``. Pass your own to keep the mapping in your
                application's registry; defaults to the bridge's own model.
            channel_model: The mapped class holding the channels, built from
                ``ChatChannelsMixin``. Defaults to the bridge's own model.
            create_tables: Whether ``start`` should create the two tables when they do
                not exist. Turn it off when your own migrations own the schema.
        """
        self.message_model = message_model
        self.channel_model = channel_model
        self.create_tables = create_tables

        self.database = Database(database_engine)
        self.server_bot = Server(
            session=self.database.session,
            on_change=on_change,
            display_name=display_name,
            message_model=message_model,
            channel_model=channel_model,
        )
        self.discord_bot = DiscordBot(
            discord_token=discord_token,
            banned_words=banned_words,
        )

        self.server_bot.init_bot(self.discord_bot)
        self.discord_bot.init_bot(self.server_bot)

    async def start(self):
        """
        Create the bridge's own tables if asked to, then run the Discord bot until it stops.

        The caller's engine is left open; only the bridge's own sessions are released.
        """
        logging.info('Starting DSBridge')

        if self.create_tables:
            await self.database.create_all(
                [self.channel_model.__table__, self.message_model.__table__]
            )

        try:
            await self.discord_bot.start()
        finally:
            await self.database.close()
