import hmac
from hashlib import sha1
import asyncio
import logging
import threading
import discord
from discord.ext import commands
from functools import wraps
from flask import request
from server import Server
from config import app_config


# Initialize the server bot
server_bot = Server(app_config.SERVER_ENDPOINT, app_config.SERVER_KEY)

# Initialize the Discord bot
intents = discord.Intents.default()
intents.messages = True
discord_bot = commands.Bot(command_prefix='!', intents=intents)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Dictionaries to map messages between Discord and Server
discord_to_server = {}
server_to_discord = {}


# decorator for server bot authorization
def server_bot_auth(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        try:
            # Authorize requests
            signature = request.headers['x-discord-signature']
            hsh = hmac.new(bytes(app_config.SERVER_KEY, 'UTF-8'), request.data, sha1).hexdigest()
            if hsh != signature:
                return '', 401
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f'Error in {func.__name__}: {e}')
            raise

    return wrap


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
            raise

    return wrapper


@server_bot.app.route('/new-message', methods=['POST'])
@server_bot_auth
def handle_server_message():
    data = request.get_json()
    message = data['message']['text']
    discord_channel = discord_bot.get_channel(app_config.DISCORD_CHANNEL_ID)
    loop = asyncio.get_event_loop()
    discord_message = loop.run_until_complete(discord_channel.send(message))
    discord_to_server[discord_message.id] = data['message']['message_id']
    server_to_discord[data['message']['message_id']] = discord_message.id
    logger.info(f'Server message forwarded to Discord: {message}')
    return '', 200


@server_bot.app.route('/edit-message', methods=['POST'])
@server_bot_auth
def handle_server_message_edited():
    data = request.get_json()
    edited_message = data['edited_message']
    if edited_message.message_id not in server_to_discord:
        return '', 400

    discord_message_id = server_to_discord[edited_message.message_id]
    discord_channel = discord_bot.get_channel(app_config.DISCORD_CHANNEL_ID)
    loop = asyncio.get_event_loop()
    discord_message = loop.run_until_complete(discord_channel.fetch_message(discord_message_id))
    if not discord_message:
        return '', 400

    loop.run_until_complete(discord_message.edit(content=edited_message.text))
    discord_to_server[discord_message_id] = edited_message.message_id
    logger.info(f'Discord message ID: {discord_message_id} edited following edit in server: {edited_message.text}')
    return '', 200


@server_bot.app.route('/delete-message', methods=['POST'])
@server_bot_auth
def handle_server_message_deletion():
    data = request.get_json()
    server_message_id = data['message']['message_id']
    if server_message_id not in server_to_discord:
        return '', 400

    discord_message_id = server_to_discord[server_message_id]
    discord_channel = discord_bot.get_channel(app_config.DISCORD_CHANNEL_ID)
    loop = asyncio.get_event_loop()
    discord_message = loop.run_until_complete(discord_channel.fetch_message(discord_message_id))
    if not discord_message:
        return '', 400

    loop.run_until_complete(discord_message.delete())

    # Remove from dictionary as part of cleanup
    del discord_to_server[discord_message_id]
    del server_to_discord[server_message_id]
    logger.info(f'Discord message deleted following deletion from server: {discord_message.content}')
    return '', 200


@discord_bot.event
async def on_ready():
    logger.info(f'Logged in to Discord as {discord_bot.user.name}')


@discord_bot.event
@discord_bot_handler
async def on_message(message):
    """
    Forwards Discord messages to Server.
    Args:
        message: The Discord message object.
    Returns: None
    """

    # Forward the message to the server
    server_message = server_bot.send_to_server(message.content)
    discord_to_server[message.id] = server_message['message_id']
    server_to_discord[server_message['message_id']] = message.id
    logger.info(f'Discord message forwarded to server: {message.content}')

    # Process commands (if any)
    await discord_bot.process_commands(message)
    logger.info(f'Discord command processed: {message.content}')


@discord_bot.event
@discord_bot_handler
async def on_message_edit(before, after):
    if before.id in discord_to_server:
        server_message_id = discord_to_server[before.id]
        server_bot.edit_message_text(server_message_id, after.content)
        server_to_discord[server_message_id] = after.id
        logger.info(f'Server message ID: {server_message_id} edited following edit in Discord: {after.content}')


@discord_bot.event
@discord_bot_handler
async def on_message_delete(message):
    if message.id in discord_to_server:
        server_message_id = discord_to_server[message.id]
        server_bot.delete_message(server_message_id)

        # Remove from dictionary as part of cleanup
        del discord_to_server[message.id]
        del server_to_discord[server_message_id]
        logger.info(f'Server message deleted following deletion from Discord: {message.content}')


def start_server_bot():
    logger.info('Starting Server bot')
    server_bot.start()


def start_discord_bot():
    logger.info('Starting Discord bot')
    discord_bot.run(app_config.DISCORD_TOKEN)


if __name__ == '__main__':
    # Create threads for each bot
    thread1 = threading.Thread(target=start_server_bot)
    thread2 = threading.Thread(target=start_discord_bot)

    # Start the threads
    thread1.start()
    thread2.start()

    # Join the threads to the main thread
    thread1.join()
    thread2.join()
