import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta, date

import pytz
import socketio
from discord.message import Message as DiscordMessage
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
        self.connected = False
        self.endpoint = config.SERVER_ENDPOINT
        self.key = config.SERVER_KEY
        self.config = config
        self.discord_bot = None
        self.discord_channel = None
        self.loop = asyncio.get_event_loop()

        self.add_routes()
        self.session.create_all()

    def init_bot(self, discord_bot: DiscordBot):
        """
        Initialize the discord bot
        Args:
            discord_bot: Discord bot
        """
        self.discord_bot = discord_bot
        self.discord_channel = self.discord_bot.bot.get_channel(self.config.DISCORD_CHANNEL_ID)

    def add_routes(self):
        """
        Add routes to the socket
        """
        @self.socketio.on('chat-message', namespace='/feed')
        def on_message(data):
            data = json.loads(data)
            if data['type'] == 'new-message':
                self.handle_server_message(data)
            elif data['type'] == 'edit-message':
                self.handle_server_message_edited(data)
            elif data['type'] == 'delete-message':
                self.handle_server_message_deletion(data)
            else:
                logging.error(f'Unknown message type: {data["type"]}')

    def handle_server_message(self, data: dict):
        """
        Forward the message to discord
        Args:
            data: Payload from server
        """
        message = Message(data['message'])
        user = self.session.query(User).filter_by(id=message.user_id).first()
        discord_message = self.loop.run_until_complete(self.discord_channel.send(
            f'{user.display_name}: {message.text}'))

        logging.info(f'Server message forwarded to Discord: {message.text}')

        # Update discord_id on server
        self.update_server_data(message.id, discord_message.id)

    def handle_server_message_edited(self, data: dict):
        """
        Edit the message on discord
        Args:
            data: Payload from server
        """
        before_message = Message(data['before_message'])
        after_message = Message(data['after_message'])
        user = self.session.query(User).filter_by(id=before_message.user_id).first()

        discord_message = self.loop.run_until_complete(self.discord_channel.fetch_message(before_message.discord_id))

        edited_message = self.loop.run_until_complete(discord_message.edit(
            content=f'{user.display_name}: {after_message.text}'))

        # Update discord_id on server
        self.update_server_data(before_message.id, edited_message.id)

        logging.info(
            f'Discord message ID: {discord_message.id} edited following edit in server: {edited_message.text}')

    def handle_server_message_deletion(self, data: dict):
        """
        Delete the message from discord
        Args:
            data: Payload from server
        """
        try:
            server_message = Message(data['message'])
            discord_message = self.loop.run_until_complete(self.discord_channel.fetch_message(server_message.discord_id))

            self.loop.run_until_complete(discord_message.delete())

            # Remove from server
            self.session.delete(server_message)
            self.session.commit()

            logging.info(f'Discord message deleted following deletion from server: {discord_message.content}')
        except SQLAlchemyError:
            self.session.rollback()

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

    def update_server_data(self, msg_id: int, discord_id: int):
        """
        Update the discord_id on the server
        Args:
            msg_id: Server message ID
            discord_id: Discord message ID
        """
        try:
            msg = self.session.query(Message).filter_by(id=msg_id).first()
            msg.discord_id = discord_id
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()

    def send_to_server(self, data: DiscordMessage):
        """
        Send the message to the server
        Args:
            data: DiscordMessage
        """
        # Send the message to the server
        try:
            msg = Message(data)
            self.session.add(msg)
            self.session.commit()

            self.socketio.emit('chat-message', {'type': 'new-message', 'message': msg}, self.namespace)
        except SQLAlchemyError:
            self.session.rollback()

    def edit_message_text(self, before_msg: DiscordMessage, after_msg: DiscordMessage):
        """
        Edit the message on the server
        Args:
            before_msg: DiscordMessage
            after_msg: DiscordMessage
        """
        # Edit the message on the server
        try:
            server_msg = self.session.query(Message).filter_by(discord_id=before_msg.id).first()
            server_msg.discord_id = after_msg.id
            server_msg.text = after_msg.content
            self.session.commit()

            self.socketio.emit('chat-message', {'type': 'edit-message', 'message': server_msg}, self.namespace)
        except SQLAlchemyError:
            self.session.rollback()

    def delete_message(self, message: DiscordMessage):
        """
        Delete the message on the server
        Args:
            message: DiscordMessage
        """
        # Delete the message on the server
        try:
            server_msg = self.session.query(Message).filter_by(discord_id=message.id).first()
            self.session.delete(server_msg)
            self.session.commit()

            self.socketio.emit('chat-message', {'type': 'delete-message', 'message': server_msg}, self.namespace)
        except SQLAlchemyError:
            self.session.rollback()
