import pytz
from discord.message import Message as DiscordMessage
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Boolean, Index, ForeignKey
from dsbridge.database import Base, session
from datetime import datetime


class Message(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, nullable=False, index=True)
    discord_message_id = Column(BigInteger, index=True)
    user_id = Column(Integer, index=True)
    discord_user_id = Column(BigInteger)
    text = Column(String, nullable=False)
    hidden = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_channel_id_hidden', 'channel_id', 'hidden'),
    )

    def __init__(self, data, server_channel_id=None):
        super().__init__()
        if isinstance(data, DiscordMessage):
            if server_channel_id is None:
                raise ValueError('server_channel_id is required when creating a Message from a DiscordMessage')
            self.from_discord(data, server_channel_id)
        else:
            self.id = data['id'] if 'id' in data else None
            self.channel_id = data['channel_id']
            self.discord_message_id = data['discord_message_id'] if 'discord_message_id' in data else None
            self.user_id = data['user_id'] if 'user_id' in data else None
            self.discord_user_id = data['discord_user_id'] if 'discord_user_id' in data else None
            self.text = data['text'] if 'text' in data else ''
            self.hidden = data['hidden'] if 'hidden' in data else False
            self.created_at = data['created_at'] if 'created_at' in data else datetime.now(pytz.UTC)
            self.last_updated = data['last_updated'] if 'last_updated' in data else datetime.now(pytz.UTC)

    def from_discord(self, data: DiscordMessage, server_channel_id):
        self.discord_message_id = data.id
        self.discord_user_id = data.author.id
        self.text = data.content
        self.channel_id = server_channel_id
        self.user_id = None

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'discord_message_id': self.discord_message_id,
            'discord_user_id': self.discord_user_id,
            'hidden': self.hidden,
            'text': self.text,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
        }

    def __repr__(self):
        return f'<Message {self.id}>'


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    display_name = Column(String, nullable=False)

    def __repr__(self):
        return f'<User {self.id}>'
