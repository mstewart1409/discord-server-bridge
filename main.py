import logging
import threading

from config import app_config
from discord_bot import DiscordBot
from server import Server
from database import Base, engine

# Initialize the server bot
server_bot = Server(app_config)

# Initialize the Discord bot
discord_bot = DiscordBot(app_config)

server_bot.init_bot(discord_bot)
discord_bot.init_bot(server_bot)

Base.metadata.create_all(engine)

# Set up logging
logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('root').setLevel(logging.INFO)
logging.getLogger(__name__).setLevel(logging.INFO)


def start_server_bot():
    logging.info('Starting Server bot')
    server_bot.start()


def start_discord_bot():
    logging.info('Starting Discord bot')
    discord_bot.start()


if __name__ == '__main__':
    # Create threads for each bot
    thread1 = threading.Thread(target=start_server_bot)
    thread2 = threading.Thread(target=start_discord_bot)

    # Start the threads
    thread2.start()
    thread1.start()

    # Join the threads to the main thread
    thread2.join()
    thread1.join()
