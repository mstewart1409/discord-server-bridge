import logging

import discord
from discord.ext import commands
from discord.message import Message as DiscordMessage


class DiscordBot:
    def __init__(self, config):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.server_bot = None
        self.token = config.DISCORD_TOKEN

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
            # Forward the message to the server
            self.server_bot.send_to_server(message)
            logging.info(f'Discord message forwarded to server: {message.id}')

        @self.bot.event
        @self.discord_bot_handler
        async def on_message_edit(before_msg: DiscordMessage, after_msg: DiscordMessage):
            self.server_bot.edit_message_text(before_msg, after_msg)
            logging.info(f'Server message ID: {before_msg.id} edited following edit in Discord: {after_msg.id}')

        @self.bot.event
        @self.discord_bot_handler
        async def on_message_delete(message: DiscordMessage):
            self.server_bot.delete_message(message)
            logging.info(f'Server message deleted following deletion from Discord: {message.id}')

    def get_channel(self, channel_id):
        return self.bot.get_channel(channel_id)

    def start(self):
        """
        Start the discord bot
        """
        self.bot.run(self.token, reconnect=True)

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
