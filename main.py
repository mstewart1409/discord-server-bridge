import logging
import threading

import discord
from discord.ext import commands
from telegram import Bot
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

# Tokens
DISCORD_TOKEN = 'discord_token'
TELEGRAM_TOKEN = 'telegram_token'

# Initialize channels
TELEGRAM_CHAT_ID = 'telegram_chat_id'
DISCORD_CHANNEL_ID = 0

# Initialize the Telegram bot
telegram_bot = Bot(token=TELEGRAM_TOKEN)

# Initialize the Discord bot
intents = discord.Intents.default()
intents.messages = True
discord_bot = commands.Bot(command_prefix='!', intents=intents)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')


# Handle Telegram messages
def handle_telegram_message(update, context):
    """
    Forwards Telegram messages to Discord.
    Args:
        update: The Telegram update object.
        context: The Telegram context object.
    """
    message = update.message.text
    channel = discord_bot.get_channel(DISCORD_CHANNEL_ID)
    discord_bot.loop.create_task(channel.send(message))
    logger.info(f'Telegram message forwarded to Discord: {message}')


# Set up the Telegram updater and dispatcher
telegram_updater = Updater(TELEGRAM_TOKEN, use_context=True)
telegram_dispatcher = telegram_updater.dispatcher

# Add Telegram message handler
telegram_dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_telegram_message))


@discord_bot.event
async def on_ready():
    logger.info(f'Logged in to Discord as {discord_bot.user.name}')


@discord_bot.event
async def on_message(message):
    """
    Forwards Discord messages to Telegram.
    Args:
        message: The Discord message object.
    Returns: None
    """
    # Ignore messages from the bot itself
    if message.author == discord_bot.user:
        return

    # Forward the message to the Telegram channel
    telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message.content)
    logger.info(f'Discord message forwarded to Telegram: {message.content}')

    # Process commands (if any)
    await discord_bot.process_commands(message)
    logger.info(f'Discord command processed: {message.content}')


def start_telegram_bot():
    logger.info('Starting Telegram bot')
    telegram_updater.start_polling()
    telegram_updater.idle()


def start_discord_bot():
    logger.info('Starting Discord bot')
    discord_bot.run(DISCORD_TOKEN)


if __name__ == '__main__':
    # Create threads for each bot
    thread1 = threading.Thread(target=start_telegram_bot)
    thread2 = threading.Thread(target=start_discord_bot)

    # Start the threads
    thread1.start()
    thread2.start()

    # Join the threads to the main thread
    thread1.join()
    thread2.join()
