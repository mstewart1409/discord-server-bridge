import asyncio
import logging
import threading

from dsbridge.config import app_config
from dsbridge.database import Base
from dsbridge.database import engine
from dsbridge.discord_bot import DiscordBot
from dsbridge.server import Server

# Initialize the server bot
server_bot = Server(app_config, loop=asyncio.get_event_loop())

# Initialize the Discord bot
discord_bot = DiscordBot(app_config, loop=server_bot.loop)

server_bot.init_bot(discord_bot)
discord_bot.init_bot(server_bot)

Base.metadata.create_all(engine)


def start_server_bot():
    logging.info('Starting Server bot')
    server_bot.start()


def start_discord_bot():
    logging.info('Starting Discord bot')
    discord_bot.start()


def run():
    # Create threads for each bot
    thread1 = threading.Thread(target=start_server_bot)
    thread2 = threading.Thread(target=start_discord_bot)

    # Start the threads
    thread2.start()
    thread1.start()

    # Join the threads to the main thread
    thread2.join()
    thread1.join()
