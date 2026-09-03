import logging
from functools import wraps
from inspect import isawaitable

from discord.message import Message as DiscordMessage
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

import dsbridge.utils as utils
from dsbridge.discord_bot import DiscordBot
from dsbridge.models import ChatChannels
from dsbridge.models import Message
from dsbridge.models import utcnow

UNKNOWN_DISPLAY_NAME = 'Unknown user'


async def _noop(payload):
    pass


class Server:
    def __init__(
        self,
        session,
        on_change=None,
        display_name=None,
        message_model=Message,
        channel_model=ChatChannels,
    ):
        """
        The server side half of the bridge, driven by the host application.

        Args:
            session: SQLAlchemy session registry to query the database with.
            on_change: Optional awaitable called with a payload describing every
                change that originated on Discord, so the host can broadcast it.
            display_name: Optional callable taking a host user id and returning the
                name to show on Discord. May be a coroutine function. Users belong
                to the host application, so the bridge stores only their ids.
            message_model: The mapped class holding the messages, built from
                ``MessageMixin``. Defaults to the bridge's own model.
            channel_model: The mapped class holding the channels, built from
                ``ChatChannelsMixin``. Defaults to the bridge's own model.
        """
        self.session = session
        self.on_change = on_change or _noop
        self.resolve_display_name = display_name
        self.message_model = message_model
        self.channel_model = channel_model
        self.discord_bot = None

    def init_bot(self, discord_bot: DiscordBot):
        """
        Initialize the discord bot
        Args:
            discord_bot: Discord bot
        """
        self.discord_bot = discord_bot

    @staticmethod
    def session_scope(f):
        """
        Roll back and release the task's session once the handler is done.

        Stale connections are already handled by the engine's ``pool_pre_ping``.
        """

        @wraps(f)
        async def wrap(self, *args, **kwargs):
            try:
                return await f(self, *args, **kwargs)
            except SQLAlchemyError:
                await self.session.rollback()
                raise
            finally:
                # Sessions are scoped to the current task, so release this one
                # instead of leaking a connection per handled event.
                await self.session.remove()

        return wrap

    async def get_message(self, message_id: int):
        """
        Load a message by its primary key.

        Args:
            message_id: Message ID from server.

        Returns:
            The message, or None when no such message exists.
        """
        return await self.session.get(self.message_model, message_id)

    async def display_name(self, message) -> str:
        """The author's display name, or a placeholder when the host cannot name them."""
        if message.user_id is None or self.resolve_display_name is None:
            return UNKNOWN_DISPLAY_NAME

        name = self.resolve_display_name(message.user_id)
        if isawaitable(name):
            name = await name
        return name or UNKNOWN_DISPLAY_NAME

    async def get_discord_channel(self, message):
        """
        Resolve the Discord channel a message should be mirrored into.

        The channel is loaded by an explicit query rather than through a relationship,
        because the host owns the mapping and need not relate the two models at all.

        Args:
            message: Message whose channel should be resolved.

        Returns:
            The Discord channel to mirror into, or None when the message is not
            mirrored or the bot cannot see the channel.
        """
        channel = await self.session.get(self.channel_model, message.channel_id)
        if channel is None or channel.discord_channel_id is None:
            return None

        discord_channel = self.discord_bot.bot.get_channel(channel.discord_channel_id)
        if discord_channel is None:
            logging.error(f'Discord channel not found: {channel.discord_channel_id}')
        return discord_channel

    @session_scope
    async def handle_server_message(self, message_id: int):
        """
        Forward the message to discord
        Args:
            message_id: Message ID from server
        """
        message = await self.get_message(message_id)
        if message is None:
            logging.error(f'Server message not found: {message_id}')
            return

        discord_channel = await self.get_discord_channel(message)
        if discord_channel is None:
            return

        discord_message = await discord_channel.send(
            embed=utils.create_embed(await self.display_name(message), message.text)
        )

        # Update discord response on server
        message.discord_message_id = discord_message.id
        message.last_updated = utcnow()
        await self.session.commit()

        logging.info(f'Server message forwarded to Discord: {message.id}')

    @session_scope
    async def handle_server_message_edited(self, before_message_id: int, after_message_id: int):
        """
        Edit the message on discord
        Args:
            before_message_id: Before message ID from server
            after_message_id: After message ID from server
        """
        before_message = await self.get_message(before_message_id)
        after_message = await self.get_message(after_message_id)
        if before_message is None or after_message is None:
            logging.error(
                f'Server messages not found for edit: {before_message_id} -> {after_message_id}'
            )
            return

        discord_channel = await self.get_discord_channel(before_message)
        if discord_channel is None:
            return

        if before_message.discord_message_id is None:
            logging.error(f'Server message was never mirrored to Discord: {before_message_id}')
            return

        discord_message = await discord_channel.fetch_message(before_message.discord_message_id)

        edited_message = await discord_message.edit(
            embed=utils.create_embed(await self.display_name(before_message), after_message.text)
        )

        # Update discord response on server
        before_message.hidden = True
        before_message.last_updated = utcnow()

        after_message.discord_message_id = edited_message.id
        after_message.last_updated = utcnow()
        await self.session.commit()

        logging.info(
            f'Discord message ID: {discord_message.id} edited following edit in server: {edited_message.id}'
        )

    @session_scope
    async def handle_server_message_deletion(self, message_id: int):
        """
        Delete the message from discord
        Args:
            message_id: Message ID from server
        """
        message = await self.get_message(message_id)
        if message is None:
            logging.error(f'Server message not found: {message_id}')
            return

        discord_channel = await self.get_discord_channel(message)
        if discord_channel is not None and message.discord_message_id is not None:
            discord_message = await discord_channel.fetch_message(message.discord_message_id)

            await discord_message.delete()
            logging.info(f'Discord message deleted following deletion from server: {message.id}')

        # Remove from server
        message.hidden = True
        message.last_updated = utcnow()
        await self.session.commit()

    @session_scope
    async def send_to_server(self, data: DiscordMessage):
        """
        Send the message to the server
        Args:
            data: DiscordMessage
        """
        # Send the message to the server
        result = await self.session.execute(
            select(self.channel_model).filter_by(discord_channel_id=data.channel.id)
        )
        channel = result.scalar_one_or_none()
        if channel is None:
            channel = self.channel_model(discord_channel_id=data.channel.id)
            self.session.add(channel)
            await self.session.commit()

        message = self.message_model.from_discord(data, channel)
        self.session.add(message)
        await self.session.commit()

        await self.on_change({'type': 'new-message', 'message_id': message.id})

    @session_scope
    async def edit_message_text(self, before_msg: DiscordMessage, after_msg: DiscordMessage):
        """
        Edit the message on the server
        Args:
            before_msg: DiscordMessage
            after_msg: DiscordMessage
        """
        # Edit the message on the server
        result = await self.session.execute(
            select(self.channel_model).filter_by(discord_channel_id=before_msg.channel.id)
        )
        channel = result.scalar_one_or_none()

        result = await self.session.execute(
            select(self.message_model).filter_by(discord_message_id=before_msg.id, hidden=False)
        )
        before_server_message = result.scalars().first()

        if channel is None or before_server_message is None:
            logging.error(f'Discord message is not mirrored on the server: {before_msg.id}')
            return

        before_server_message.hidden = True
        before_server_message.last_updated = utcnow()

        after_server_message = self.message_model.from_discord(after_msg, channel)
        after_server_message.user_id = before_server_message.user_id
        after_server_message.created_at = before_server_message.created_at
        self.session.add(after_server_message)
        await self.session.commit()

        await self.on_change(
            {
                'type': 'edit-message',
                'before_message_id': before_server_message.id,
                'after_message_id': after_server_message.id,
            }
        )

    @session_scope
    async def delete_message(self, message: DiscordMessage):
        """
        Delete the message on the server
        Args:
            message: DiscordMessage
        """
        # Delete the message on the server
        result = await self.session.execute(
            select(self.message_model).filter_by(discord_message_id=message.id, hidden=False)
        )
        server_msg = result.scalars().first()
        if server_msg is None:
            logging.error(f'Discord message is not mirrored on the server: {message.id}')
            return

        server_msg.hidden = True
        server_msg.last_updated = utcnow()
        await self.session.commit()

        await self.on_change({'type': 'delete-message', 'message_id': server_msg.id})
