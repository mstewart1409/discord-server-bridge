import asyncio
import logging

from dsbridge.config import app_config
from dsbridge.database import Base
from dsbridge.database import engine
from dsbridge.discord_bot import DiscordBot
from dsbridge.server import Server


async def runner():
    logging.info('Starting DSBridge')

    loop = asyncio.get_event_loop()
    # Initialize the server bot with the current event loop
    server_bot = Server(app_config, loop=loop)

    # Initialize the Discord bot with the same event loop
    discord_bot = DiscordBot(app_config, loop=loop)

    server_bot.init_bot(discord_bot)
    discord_bot.init_bot(server_bot)

    Base.metadata.create_all(engine)

    # Start both bots concurrently
    await asyncio.gather(
        discord_bot.start(),
        server_bot.start(),
    )
