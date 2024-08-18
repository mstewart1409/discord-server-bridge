import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, date

import pytz
import socketio
from discord.message import Message as DiscordMessage
from werkzeug.security import generate_password_hash

from database import session
from models import Message


class CustomJSONEncodeDecode:
    @staticmethod
    def dumps(obj, **kwargs):
        return json.dumps(obj, **kwargs, default=CustomJSONEncodeDecode.datetime_jsonify)

    @staticmethod
    def loads(s, **kwargs):
        return json.loads(s, **kwargs, object_hook=CustomJSONEncodeDecode.datetime_parser)

    @staticmethod
    def datetime_jsonify(o):
        if isinstance(o, (datetime, date, timedelta)):
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
        self.endpoint = config.SERVER_ENDPOINT
        self.key = config.SERVER_KEY
        self.config = config
        self.discord_bot = None
        self.discord_channel = None
        self.loop = asyncio.get_event_loop()

        self.add_routes()
        """with self.app.app_context():
            db.create_all()"""

    def init_bot(self, discord_bot):
        self.discord_bot = discord_bot
        self.discord_channel = self.discord_bot.get_channel(self.config.DISCORD_CHANNEL_ID)

    def add_routes(self):
        @self.socketio.on('connect', namespace='/feed')
        def connect():
            logging.info('Connected to Server')

        @self.socketio.on('disconnect', namespace='/feed')
        def disconnect():
            logging.info('Disconnected from Server')

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

    def handle_server_message(self, data):
        message = Message(data['message'])
        loop = asyncio.get_event_loop()
        discord_message = loop.run_until_complete(self.discord_channel.send(message))

        logging.info(f'Server message forwarded to Discord: {message.text}')

        # Update discord_id on server
        self.update_server_data(message.id, discord_message.id)

    def handle_server_message_edited(self, data):
        before_message = Message(data['before_message'])
        after_message = Message(data['after_message'])

        discord_message = self.loop.run_until_complete(self.discord_channel.fetch_message(before_message.discord_id))

        edited_message = self.loop.run_until_complete(discord_message.edit(content=after_message.text))

        # Update discord_id on server
        self.update_server_data(before_message.id, edited_message.id)

        logging.info(
            f'Discord message ID: {discord_message.id} edited following edit in server: {edited_message.text}')

    def handle_server_message_deletion(self, data):
        server_message = Message(data['message'])

        discord_message = self.loop.run_until_complete(self.discord_channel.fetch_message(server_message.discord_id))

        self.loop.run_until_complete(discord_message.delete())
        logging.info(f'Discord message deleted following deletion from server: {discord_message.content}')

    def start(self):
        timestamp = str(datetime.now(pytz.UTC).timestamp())
        hash_k = generate_password_hash(self.config.SERVER_KEY + timestamp, method='pbkdf2')
        headers = {'Authorization': hash_k, 'Timestamp': timestamp}
        while True:
            self.socketio.connect(self.endpoint, headers=headers, namespaces=['/feed'])
            self.socketio.wait()

    def update_server_data(self, msg_id: int, discord_id: int):
        msg = self.session.query(Message).filter_by(id=msg_id).first()
        msg.discord_id = discord_id
        self.session.commit()

    def send_to_server(self, message: DiscordMessage):
        # Send the message to the server
        self.socketio.send('chat-message', {'type': 'new-message', 'message': Message(message)})

    def edit_message_text(self, before_msg: DiscordMessage, after_msg: DiscordMessage):
        # Edit the message on the server
        self.socketio.send('chat-message', {'type': 'edit-message',
                                            'before_message': Message(before_msg),
                                            'after_message': Message(after_msg)})
        with self.app.app_context():
            server_msg = Message.query.filter_by(discord_id=before_msg.id).first()
            server_msg.discord_id = after_msg.id
            server_msg.text = after_msg.content
            self.db.session.commit()

    def delete_message(self, message: DiscordMessage):
        # Delete the message on the server
        with self.app.app_context():
            server_msg = Message.query.filter_by(discord_id=message.id).first()
            self.db.session.delete(server_msg)
            self.db.session.commit()
