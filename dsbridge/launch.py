import asyncio
import logging

from dsbridge.config import app_config
from dsbridge.database import Base
from dsbridge.database import engine
from dsbridge.discord_bot import DiscordBot
from dsbridge.server import Server


async def runner():
    logging.info('Starting DSBridge')

    # Initialize the server bot
    server_bot = Server(app_config)

    # Initialize the Discord bot
    discord_bot = DiscordBot(app_config)

    server_bot.init_bot(discord_bot)
    discord_bot.init_bot(server_bot)

    Base.metadata.create_all(engine)

    # Start both bots concurrently
    await asyncio.gather(
        discord_bot.start(),
        server_bot.start(),
    )
