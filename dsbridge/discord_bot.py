import html
import logging

import discord
from discord.ext import commands
from discord.message import Message as DiscordMessage

import dsbridge.utils as utils


class DiscordBot:
    def __init__(
        self,
        discord_token: str,
        banned_words: list[str] | None = None,
        channel_ids: set[int] | None = None,
    ):
        """
        Args:
            discord_token: Token used to authenticate the Discord bot.
            banned_words: Words to strip from messages.
            channel_ids: The server channels to mirror and moderate; None for all.
                Direct messages are always mirrored.
        """
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.guilds = True
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.server_bot = None
        self.token = discord_token
        self.banned_words = banned_words or []
        self.channel_ids = channel_ids

        self.add_routes()

    def init_bot(self, server_bot):
        """
        Initialize the server bot
        Args:
            server_bot: Server bot
        """
        self.server_bot = server_bot

    def add_routes(self):
        """
        Add routes to the discord bot
        """

        @self.bot.event
        async def on_ready():
            logging.info(f'Logged in to Discord as {self.bot.user.name}')

        @self.bot.event
        @self.discord_bot_handler
        async def on_message(message: DiscordMessage):
            if not self.is_staff(message) and self.needs_removal(message.content):
                await message.delete()
                logging.info(f'Discord message deleted due to sanitization: {message.id}')
            else:
                # Forward the message to the server
                await self.server_bot.send_to_server(message)
                logging.info(f'Discord message forwarded to server: {message.id}')

        @self.bot.event
        @self.discord_bot_handler
        async def on_message_edit(before_msg: DiscordMessage, after_msg: DiscordMessage):
            await self.server_bot.edit_message_text(before_msg, after_msg)
            logging.info(
                f'Server message ID: {before_msg.id} edited following edit in Discord: {after_msg.id}'
            )

        @self.bot.event
        @self.discord_bot_handler
        async def on_message_delete(message: DiscordMessage):
            await self.server_bot.delete_message(message)
            logging.info(f'Server message deleted following deletion from Discord: {message.id}')

    def needs_removal(self, content: str) -> bool:
        """Whether sanitising changes the text; HTML escaping alone (an "&") does not count."""
        text = html.unescape(content)
        return html.unescape(utils.sanitize_input(text, self.banned_words)) != text

    @staticmethod
    def is_staff(message: DiscordMessage) -> bool:
        """The author may delete messages in this channel (the owner, an admin, a moderator)."""
        return (
            isinstance(message.author, discord.Member)
            and message.channel.permissions_for(message.author).manage_messages
        )

    def is_ignored(self, message: DiscordMessage) -> bool:
        """A message the bridge neither mirrors nor moderates.

        A bot or a webhook (the bridge's own posts among them), or a server
        channel outside ``channel_ids`` (a thread is a channel of its own).
        """
        if message.author.bot or message.webhook_id:
            return True
        return (
            self.channel_ids is not None
            and message.guild is not None
            and message.channel.id not in self.channel_ids
        )

    async def start(self):
        """
        Start the discord bot
        """
        logging.info('Starting Discord Bot')
        await self.bot.start(self.token, reconnect=True)

    # decorator for discord bot event handlers
    def discord_bot_handler(self, func):
        async def wrapper(*args, **kwargs):
            try:
                if self.is_ignored(args[0]):
                    return
                return await func(*args, **kwargs)
            except Exception as e:
                logging.error(f'Error in {func.__name__}: {e}')
                raise

        wrapper.__name__ = func.__name__

        return wrapper
