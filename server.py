import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta, date

import psycopg2
import pytz
import socketio
from discord.message import Message as DiscordMessage
from discord import Embed
from functools import wraps
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
from discord_bot import DiscordBot

from database import session
from models import Message
from models import User


class CustomJSONEncodeDecode:
    @staticmethod
    def dumps(obj, **kwargs):
        return json.dumps(obj, **kwargs, default=CustomJSONEncodeDecode.object_jsonify)

    @staticmethod
    def loads(s, **kwargs):
        return json.loads(s, **kwargs, object_hook=CustomJSONEncodeDecode.datetime_parser)

    @staticmethod
    def object_jsonify(o):
        if isinstance(o, Message):
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
    def __init__(self, config):
        self.socketio = socketio.Client(reconnection=False, logger=False, engineio_logger=False,
                                        json=CustomJSONEncodeDecode)
        self.session = session
        self.namespace = '/feed'
        self.channel_id = config.SERVER_CHANNEL_ID
        self.connected = False
        self.endpoint = config.SERVER_ENDPOINT
        self.key = config.SERVER_KEY
        self.config = config
        self.discord_bot = None
        self.loop = asyncio.get_event_loop()

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
                self.handle_server_message(data)
            elif data['type'] == 'edit-message':
                self.handle_server_message_edited(data)
            elif data['type'] == 'delete-message':
                self.handle_server_message_deletion(data)
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
            raise error
        return wrap

    @staticmethod
    def create_embed(title, description):
        return Embed(
            title=title,
            description=description,
        )

    @handle_connection_error
    def handle_server_message(self, data: dict):
        """
        Forward the message to discord
        Args:
            data: Payload from server
        """
        message = Message(data['message'])
        user = self.session.query(User).filter_by(id=message.user_id).first()

        discord_message = self.loop.run_until_complete(self.discord_bot.discord_channel.send(
            embed=self.create_embed(user.display_name, message.text)))

        # Update discord response on server
        message.discord_message_id = discord_message.id
        message.discord_user_id = discord_message.author.id
        self.session.add(message)
        self.session.commit()

        self.socketio.emit('chat-message', {'type': 'new-message',
                                            'channel_id': self.channel_id,
                                            'message': message}, self.namespace)

        logging.info(f'Server message forwarded to Discord: {message.text}')

    @handle_connection_error
    def handle_server_message_edited(self, data: dict):
        """
        Edit the message on discord
        Args:
            data: Payload from server
        """
        before_message = self.session.query(Message).filter_by(id=data['before_message']['id']).first()
        after_message = Message(data['after_message'])
        user = self.session.query(User).filter_by(id=before_message.user_id).first()

        discord_message = self.loop.run_until_complete(self.discord_bot.discord_channel.fetch_message(
            before_message.discord_message_id))

        edited_message = self.loop.run_until_complete(discord_message.edit(
            embed=self.create_embed(user.display_name, after_message.text)))

        # Update discord response on server
        before_message.hidden = True
        before_message.last_updated = datetime.now(pytz.UTC)

        after_message.discord_message_id = edited_message.id
        after_message.created_at = before_message.created_at
        self.session.add(after_message)
        self.session.commit()

        self.socketio.emit('chat-message', {'type': 'edit-message', 'channel_id': self.channel_id,
                                            'before_message': before_message,
                                            'after_message': after_message}, self.namespace)

        logging.info(
            f'Discord message ID: {discord_message.id} edited following edit in server: {edited_message.id}')

    @handle_connection_error
    def handle_server_message_deletion(self, data: dict):
        """
        Delete the message from discord
        Args:
            data: Payload from server
        """
        server_message = self.session.query(Message).filter_by(id=data['message']['id']).first()
        discord_message = self.loop.run_until_complete(self.discord_bot.discord_channel.fetch_message(
            server_message.discord_message_id))

        self.loop.run_until_complete(discord_message.delete())

        # Remove from server
        server_message.hidden = True
        self.session.commit()

        self.socketio.emit('chat-message', {'type': 'delete-message',
                                            'channel_id': self.channel_id,
                                            'message': server_message}, self.namespace)

        logging.info(f'Discord message deleted following deletion from server: {discord_message.id}')

    def start(self):
        """
        Start the connection to the server
        """
        timestamp = str(datetime.now(pytz.UTC).timestamp())
        hash_k = generate_password_hash(self.config.SERVER_KEY + timestamp, method='pbkdf2')
        headers = {'Authorization': hash_k, 'Timestamp': timestamp}
        while True:
            try:
                self.socketio.connect(self.endpoint, headers=headers, namespaces=[self.namespace])
                logging.info('Connected to Server')
                self.connected = True
                self.socketio.wait()
                self.connected = False
                logging.info('Disconnected from Server')
                time.sleep(2)
            except Exception as e:
                self.connected = False
                logging.error('Error in connection to Server..')
                logging.error(repr(e))

    @handle_connection_error
    def send_to_server(self, data: DiscordMessage):
        """
        Send the message to the server
        Args:
            data: DiscordMessage
        """
        # Send the message to the server
        msg = Message(data, self.channel_id)
        self.session.add(msg)
        self.session.commit()

        self.socketio.emit('chat-message', {'type': 'new-message',
                                            'channel_id': self.channel_id, 'message': msg}, self.namespace)

    @handle_connection_error
    def edit_message_text(self, before_msg: DiscordMessage, after_msg: DiscordMessage):
        """
        Edit the message on the server
        Args:
            before_msg: DiscordMessage
            after_msg: DiscordMessage
        """
        # Edit the message on the server
        server_msg = self.session.query(Message).filter_by(discord_message_id=before_msg.id, hidden=False).first()
        server_msg.hidden = True
        server_msg.last_updated = datetime.now(pytz.UTC)

        new_server_msg = Message(after_msg, self.channel_id)
        new_server_msg.user_id = server_msg.user_id
        new_server_msg.created_at = server_msg.created_at
        self.session.add(new_server_msg)
        self.session.commit()

        self.socketio.emit('chat-message', {'type': 'edit-message', 'channel_id': self.channel_id,
                                            'before_message': server_msg,
                                            'after_message': new_server_msg}, self.namespace)

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
        self.session.commit()

        self.socketio.emit('chat-message', {'type': 'delete-message',
                                            'channel_id': self.channel_id,
                                            'message': server_msg}, self.namespace)
