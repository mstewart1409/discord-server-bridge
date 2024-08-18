from discord.ext import commands
import discord
import logging


# decorator for discord bot event handlers
def discord_bot_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            # Ignore messages from the bot itself
            if args[0].author == discord_bot.user:
                return
            return await func(*args, **kwargs)
        except Exception as e:
            logging.error(f'Error in {func.__name__}: {e}')
            raise

    wrapper.__name__ = func.__name__

    return wrapper


class DiscordBot:
    def __init__(self, config):
        self.bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
        self.server_bot = None
        self.token = config.DISCORD_TOKEN

        self.add_routes()

    def init_bot(self, server_bot):
        self.server_bot = server_bot

    def add_routes(self):
        @self.bot.event
        async def on_ready():
            logging.info(f'Logged in to Discord as {self.bot.user.name}')

        @self.bot.event
        @discord_bot_handler
        async def on_message(message):
            # Forward the message to the server
            self.server_bot.send_to_server(message)
            logging.info(f'Discord message forwarded to server: {message.text}')

        @self.bot.event
        @discord_bot_handler
        async def on_message_edit(before_msg, after_msg):
            self.server_bot.edit_message_text(before_msg, after_msg)
            logging.info(f'Server message ID: {before_msg.id} edited following edit in Discord: {after_msg.text}')

        @self.bot.event
        @discord_bot_handler
        async def on_message_delete(message):
            self.server_bot.delete_message(message)
            logging.info(f'Server message deleted following deletion from Discord: {message.text}')

    def start(self):
        self.bot.run(self.token)
