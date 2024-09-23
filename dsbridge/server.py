import asyncio
import json
import logging
import re
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from functools import wraps

import psycopg2
import pytz
import socketio
from discord import Embed
from discord.message import Message as DiscordMessage
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from dsbridge.database import session
from dsbridge.discord_bot import DiscordBot
from dsbridge.models import ChatChannels
from dsbridge.models import Message


class CustomJSONEncodeDecode:
    @staticmethod
    def dumps(obj, **kwargs):
        return json.dumps(obj, **kwargs, default=CustomJSONEncodeDecode.object_jsonify)

    @staticmethod
    def loads(s, **kwargs):
        return json.loads(s, **kwargs, object_hook=CustomJSONEncodeDecode.datetime_parser)

    @staticmethod
    def object_jsonify(o):
        if callable(getattr(o, 'to_dict', None)):
            return o.to_dict()
        elif isinstance(o, (datetime, date, timedelta)):
            return o.isoformat()

    @staticmethod
    def datetime_parser(obj):
        iso_datetime_pattern = re.compile(
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2})?$'
        )
        for k, v in obj.items():
            if isinstance(v, str) and iso_datetime_pattern.match(v):
                obj[k] = datetime.fromisoformat(v)
        return obj


class Server:
    def __init__(self, config, loop=None):
        self.socketio = socketio.Client(reconnection=False, logger=False, engineio_logger=False,
                                        json=CustomJSONEncodeDecode)
        self.session = session
        self.namespace = config.SERVER_NAMESPACE
        self.connected = False
        self.endpoint = config.HOST_URL
        self.key = config.SERVER_SECRET_KEY
        self.config = config
        self.discord_bot = None
        self.loop = asyncio.get_event_loop() if loop is None else loop

        self.add_routes()

    def init_bot(self, discord_bot: DiscordBot):
        """
        Initialize the discord bot
        Args:
            discord_bot: Discord bot
        """
        self.discord_bot = discord_bot
        print('f')

    def add_routes(self):
        """
        Add routes to the socket
        """
        @self.socketio.on('chat-message', namespace=self.namespace)
        def on_message(data):
            if data['type'] == 'new-message':
                self.handle_server_message(data['message_id'])
            elif data['type'] == 'edit-message':
                self.handle_server_message_edited(data['message_id'])
            elif data['type'] == 'delete-message':
                self.handle_server_message_deletion(data['message_id'])
            else:
                logging.error(f'Unknown message type: {data["type"]}')

    @staticmethod
    def handle_connection_error(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            self = args[0]
            retries = 0
            error = ValueError('Connection error')
            while retries < 3:
                try:
                    return f(*args, **kwargs)
                except SQLAlchemyError as e:
                    error = e
                    self.session.rollback()
                    retries += 1
                except psycopg2.OperationalError as e:
                    error = e
                    self.session.rollback()
                    retries += 1
                except BaseException as e:
                    error = e
                    self.session.rollback()
                    retries += 1

            raise error
        return wrap

    @staticmethod
    def create_embed(title, description):
        return Embed(
            title=title,
            description=description,
        )

    @handle_connection_error
    def handle_server_message(self, message_id: int):
        """
        Forward the message to discord
        Args:
            message_id: Message ID from server
        """
        message = self.session.query(Message).filter_by(id=message_id).first()

        if message.channel.discord_channel_id is not None:
            discord_channel = self.discord_bot.get_channel(message.channel.discord_channel_id)
            discord_message = self.loop.run_until_complete(discord_channel.send(
                embed=self.create_embed(message.user.display_name, message.text)))

            # Update discord response on server
            message.discord_message_id = discord_message.id
            message.last_updated = datetime.now(pytz.UTC)
            self.session.commit()

        self.socketio.emit('chat-message', {'type': 'new-message', 'message_id': message_id},
                           self.namespace)

        logging.info(f'Server message forwarded to Discord: {message.id}')

    @handle_connection_error
    def handle_server_message_edited(self, before_message_id: int, after_message_id: int):
        """
        Edit the message on discord
        Args:
            before_message_id: Before message ID from server
            after_message_id: After message ID from server
        """
        before_message = self.session.query(Message).filter_by(id=before_message_id).first()
        after_message = self.session.query(Message).filter_by(id=after_message_id).first()

        if before_message.channel.discord_channel_id is not None:
            discord_channel = self.discord_bot.get_channel(before_message.channel.discord_channel_id)
            discord_message = self.loop.run_until_complete(discord_channel.fetch_message(before_message.discord_message_id))

            edited_message = self.loop.run_until_complete(discord_message.edit(
                embed=self.create_embed(before_message.user.display_name, after_message.text)))

            # Update discord response on server
            before_message.hidden = True
            before_message.last_updated = datetime.now(pytz.UTC)

            after_message.discord_message_id = edited_message.id
            after_message.last_updated = datetime.now(pytz.UTC)
            self.session.commit()

        self.socketio.emit('chat-message', {'type': 'edit-message',
                                            'before_message_id': before_message_id,
                                            'after_message_id': after_message_id},
                           self.namespace)

        logging.info(
            f'Discord message ID: {discord_message.id} edited following edit in server: {edited_message.id}')

    @handle_connection_error
    def handle_server_message_deletion(self, message_id: int):
        """
        Delete the message from discord
        Args:
            message_id: Message ID from server
        """
        message = self.session.query(Message).filter_by(id=message_id).first()

        if message.channel.discord_channel_id is not None:
            discord_channel = self.discord_bot.get_channel(message.channel.discord_channel_id)
            discord_message = self.loop.run_until_complete(discord_channel.fetch_message(message.discord_message_id))

            self.loop.run_until_complete(discord_message.delete())

            # Remove from server
            message.hidden = True
            message.last_updated = datetime.now(pytz.UTC)
            self.session.commit()

        self.socketio.emit('chat-message', {'type': 'delete-message', 'message_id': message_id},
                           self.namespace)

        logging.info(f'Discord message deleted following deletion from server: {discord_message.id}')

    async def start(self):
        """
        Start the connection to the server
        """
        logging.info('Starting Server Bot')

        timestamp = str(datetime.now(pytz.UTC).timestamp())
        hash_k = generate_password_hash(self.config.SERVER_SECRET_KEY + timestamp, method='pbkdf2')
        headers = {'Authorization': hash_k, 'Timestamp': timestamp}
        while True:
            try:
                self.socketio.connect('https://' + self.endpoint, headers=headers, namespaces=[self.namespace])
                logging.info('Connected to Server')
                self.connected = True
                self.socketio.wait()
                self.connected = False
                logging.info('Disconnected from Server')
            except Exception as e:
                self.connected = False
                logging.error('Error in connection to Server..')
                logging.error(repr(e))
            finally:
                await asyncio.sleep(2)

    @handle_connection_error
    def send_to_server(self, data: DiscordMessage):
        """
        Send the message to the server
        Args:
            data: DiscordMessage
        """
        # Send the message to the server
        channel = self.session.query(ChatChannels).filter_by(discord_channel_id=data.channel.id).first()
        if channel is None:
            channel = ChatChannels(discord_channel_id=data.channel.id)
            self.session.add(channel)
            self.session.commit()

        message = Message(data, channel)
        self.session.add(message)
        self.session.commit()

        self.socketio.emit('chat-message', {'type': 'new-message', 'message_id': message.id},
                           self.namespace)

    @handle_connection_error
    def edit_message_text(self, before_msg: DiscordMessage, after_msg: DiscordMessage):
        """
        Edit the message on the server
        Args:
            before_msg: DiscordMessage
            after_msg: DiscordMessage
        """
        # Edit the message on the server
        channel = self.session.query(ChatChannels).filter_by(discord_channel_id=before_msg.channel.id).first()
        before_server_message = self.session.query(Message).filter_by(discord_message_id=before_msg.id, hidden=False).first()
        before_server_message.hidden = True
        before_server_message.last_updated = datetime.now(pytz.UTC)

        after_server_message = Message(after_msg, channel)
        after_server_message.user_id = before_server_message.user_id
        after_server_message.created_at = before_server_message.created_at
        self.session.add(after_server_message)
        self.session.commit()

        self.socketio.emit('chat-message', {'type': 'edit-message',
                                            'before_message_id': before_server_message.id,
                                            'after_message_id': after_server_message.id},
                           self.namespace)

    @handle_connection_error
    def delete_message(self, message: DiscordMessage):
        """
        Delete the message on the server
        Args:
            message: DiscordMessage
        """
        # Delete the message on the server
        server_msg = self.session.query(Message).filter_by(discord_message_id=message.id, hidden=False).first()
        server_msg.hidden = True
        server_msg.last_updated = datetime.now(pytz.UTC)
        self.session.commit()

        self.socketio.emit('chat-message', {'type': 'delete-message', 'message_id': server_msg.id},
                           self.namespace)
