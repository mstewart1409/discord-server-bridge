import asyncio
import logging
import threading

import discord
from discord.ext import commands
from telegram import Bot
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from config import app_config


# Initialize the Telegram bot
telegram_bot = Bot(token=app_config.TELEGRAM_TOKEN)

# Initialize the Discord bot
intents = discord.Intents.default()
intents.messages = True
intents.message_delete = True
discord_bot = commands.Bot(command_prefix='!', intents=intents)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Dictionaries to map messages between Discord and Telegram
discord_to_telegram = {}
telegram_to_discord = {}


def handle_telegram_message(update, context):
    """
    Forwards Telegram messages to Discord.
    Args:
        update: The Telegram update object.
        context: The Telegram context object.
    """
    message = update.message.text
    discord_channel = discord_bot.get_channel(app_config.DISCORD_CHANNEL_ID)
    loop = asyncio.get_event_loop()
    discord_message = loop.run_until_complete(discord_channel.send(message))
    discord_to_telegram[discord_message.id] = update.message.message_id
    telegram_to_discord[update.message.message_id] = discord_message.id
    logger.info(f'Telegram message forwarded to Discord: {message}')


def handle_telegram_message_edited(update, context):
    """
    Edits Discord messages following edit in Telegram.
    Args:
        update: The Telegram update object.
        context: The Telegram context object.

    Returns: None
    """
    edited_message = update.edited_message
    if edited_message.message_id not in telegram_to_discord:
        return

    discord_message_id = telegram_to_discord[edited_message.message_id]
    discord_channel = discord_bot.get_channel(app_config.DISCORD_CHANNEL_ID)
    loop = asyncio.get_event_loop()
    discord_message = loop.run_until_complete(discord_channel.fetch_message(discord_message_id))
    if not discord_message:
        return

    loop.run_until_complete(discord_message.edit(content=edited_message.text))
    discord_to_telegram[discord_message_id] = edited_message.message_id
    logger.info(f'Discord message ID: {discord_message_id} edited following edit in Telegram: {edited_message.text}')


def handle_telegram_message_deletion(update, context):
    """
    Deletes Discord messages following deletion from Telegram.
    Args:
        update: The Telegram update object.
        context: The Telegram context object.
    """
    telegram_message_id = update.message.message_id
    if telegram_message_id not in telegram_to_discord:
        return

    discord_message_id = telegram_to_discord[telegram_message_id]
    discord_channel = discord_bot.get_channel(app_config.DISCORD_CHANNEL_ID)
    loop = asyncio.get_event_loop()
    discord_message = loop.run_until_complete(discord_channel.fetch_message(discord_message_id))
    if not discord_message:
        return

    loop.run_until_complete(discord_message.delete())

    # Remove from dictionary as part of cleanup
    del discord_to_telegram[discord_message_id]
    del telegram_to_discord[telegram_message_id]
    logger.info(f'Discord message deleted following deletion from Telegram: {discord_message.content}')


# Set up the Telegram updater and dispatcher
telegram_updater = Updater(app_config.TELEGRAM_TOKEN, use_context=True)
telegram_dispatcher = telegram_updater.dispatcher

# Add Telegram message handler
telegram_dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_telegram_message))
telegram_dispatcher.add_handler(MessageHandler(Filters.status_update.message_deleted, handle_telegram_message_deletion))
telegram_dispatcher.add_handler(MessageHandler(Filters.update.edited_message, handle_telegram_message_edited))


# decorator for discord bot event handlers
def discord_bot_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            # Ignore messages from the bot itself
            if args[0].author == discord_bot.user:
                return
            await func(*args, **kwargs)
        except Exception as e:
            logger.error(f'Error in {func.__name__}: {e}')

    return wrapper


@discord_bot.event
async def on_ready():
    logger.info(f'Logged in to Discord as {discord_bot.user.name}')


@discord_bot.event
@discord_bot_handler
async def on_message(message):
    """
    Forwards Discord messages to Telegram.
    Args:
        message: The Discord message object.
    Returns: None
    """

    # Forward the message to the Telegram channel
    telegram_message = telegram_bot.send_message(chat_id=app_config.TELEGRAM_CHAT_ID, text=message.content)
    discord_to_telegram[message.id] = telegram_message.message_id
    telegram_to_discord[telegram_message.message_id] = message.id
    logger.info(f'Discord message forwarded to Telegram: {message.content}')

    # Process commands (if any)
    await discord_bot.process_commands(message)
    logger.info(f'Discord command processed: {message.content}')


@discord_bot.event
@discord_bot_handler
async def on_message_edit(before, after):
    if before.id in discord_to_telegram:
        telegram_message_id = discord_to_telegram[before.id]
        telegram_bot.edit_message_text(chat_id=app_config.TELEGRAM_CHAT_ID, message_id=telegram_message_id,
                                       text=after.content)
        telegram_to_discord[telegram_message_id] = after.id
        logger.info(f'Telegram message ID: {telegram_message_id} edited following edit in Discord: {after.content}')


@discord_bot.event
@discord_bot_handler
async def on_message_delete(message):
    if message.id in discord_to_telegram:
        telegram_message_id = discord_to_telegram[message.id]
        telegram_bot.delete_message(chat_id=app_config.TELEGRAM_CHAT_ID, message_id=telegram_message_id)

        # Remove from dictionary as part of cleanup
        del discord_to_telegram[message.id]
        del telegram_to_discord[telegram_message_id]
        logger.info(f'Telegram message deleted following deletion from Discord: {message.content}')


def start_telegram_bot():
    logger.info('Starting Telegram bot')
    telegram_updater.start_polling()
    telegram_updater.idle()


def start_discord_bot():
    logger.info('Starting Discord bot')
    discord_bot.run(app_config.DISCORD_TOKEN)


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
