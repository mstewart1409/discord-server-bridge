import logging

import discord
from discord.ext import commands
from discord.message import Message as DiscordMessage

import dsbridge.utils as utils


class DiscordBot:
    def __init__(self, config):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.server_bot = None
        self.config = config

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
            sanitized_message = utils.sanitize_input(message.content, self.config.BANNED_WORDS)
            if sanitized_message != message.content:
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
            logging.info(f'Server message ID: {before_msg.id} edited following edit in Discord: {after_msg.id}')

        @self.bot.event
        @self.discord_bot_handler
        async def on_message_delete(message: DiscordMessage):
            await self.server_bot.delete_message(message)
            logging.info(f'Server message deleted following deletion from Discord: {message.id}')

    async def start(self):
        """
        Start the discord bot
        """
        logging.info('Starting Discord Bot')
        await self.bot.start(self.config.DISCORD_TOKEN, bot=True, reconnect=True)

    # decorator for discord bot event handlers
    def discord_bot_handler(self, func):
        async def wrapper(*args, **kwargs):
            try:
                # Ignore messages from the bot itself
                if args[0].author == self.bot.user:
                    return
                return await func(*args, **kwargs)
            except Exception as e:
                logging.error(f'Error in {func.__name__}: {e}')
                raise

        wrapper.__name__ = func.__name__

        return wrapper
