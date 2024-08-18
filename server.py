import hmac
import logging
import asyncio
from hashlib import sha1
from flask import Flask
from flask import request
from functools import wraps
from discord.message import Message as DiscordMessage
from config import app_config
from models import Message


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
            logging.error(f'Error in {func.__name__}: {e}')
            raise

    return wrap


class Server:
    def __init__(self, config, db):
        self.app = Flask(__name__)
        self.app.config.from_object(config)
        self.app.config.update(
            SESSION_SQLALCHEMY=db,
        )

        db.init_app(self.app)
        self.endpoint = config.SERVER_ENDPOINT
        self.key = config.SERVER_KEY
        self.db = db
        self.discord_bot = None

        self.add_routes()
        """with self.app.app_context():
            db.create_all()"""

    def init_bot(self, discord_bot):
        self.discord_bot = discord_bot

    def add_routes(self):
        @self.app.route('/new-message', methods=['POST'])
        @server_bot_auth
        def handle_server_message():
            data = request.get_json()
            message = data['message']['text']
            discord_channel = self.discord_bot.get_channel(app_config.DISCORD_CHANNEL_ID)
            loop = asyncio.get_event_loop()
            discord_message = loop.run_until_complete(discord_channel.send(message))
            discord_to_server[discord_message.id] = data['message']['message_id']
            server_to_discord[data['message']['message_id']] = discord_message.id
            logging.info(f'Server message forwarded to Discord: {message}')
            return '', 200


        @self.app.route('/edit-message', methods=['POST'])
        @server_bot_auth
        def handle_server_message_edited():
            data = request.get_json()
            edited_message = data['edited_message']
            if edited_message.message_id not in server_to_discord:
                return '', 400

            discord_message_id = server_to_discord[edited_message.message_id]
            discord_channel = self.discord_bot.get_channel(app_config.DISCORD_CHANNEL_ID)
            loop = asyncio.get_event_loop()
            discord_message = loop.run_until_complete(discord_channel.fetch_message(discord_message_id))
            if not discord_message:
                return '', 400

            loop.run_until_complete(discord_message.edit(content=edited_message.text))
            discord_to_server[discord_message_id] = edited_message.message_id
            logging.info(f'Discord message ID: {discord_message_id} edited following edit in server: {edited_message.text}')
            return '', 200


        @self.app.route('/delete-message', methods=['POST'])
        @server_bot_auth
        def handle_server_message_deletion():
            data = request.get_json()
            server_message_id = data['message']['message_id']

            discord_message_id = server_to_discord[server_message_id]
            discord_channel = self.discord_bot.get_channel(app_config.DISCORD_CHANNEL_ID)
            loop = asyncio.get_event_loop()
            discord_message = loop.run_until_complete(discord_channel.fetch_message(discord_message_id))

            loop.run_until_complete(discord_message.delete())
            logging.info(f'Discord message deleted following deletion from server: {discord_message.content}')
            return '', 200

    def start(self):
        self.app.run()

    def send_to_server(self, message: DiscordMessage):
        # Send the message to the server
        with self.app.app_context():
            msg = Message(message)
            self.db.session.add(msg)
            self.db.session.commit()

    def edit_message_text(self, before_msg: DiscordMessage, after_msg: DiscordMessage):
        # Edit the message on the server
        server_msg = Message.query.filter_by(discord_id=before_msg.id).first()
        server_msg.discord_id = after_msg.id
        server_msg.text = after_msg.content
        self.db.session.commit()

    def delete_message(self, message: DiscordMessage):
        # Delete the message on the server
        server_msg = Message.query.filter_by(discord_id=message.id).first()
        self.db.session.delete(server_msg)
        self.db.session.commit()
