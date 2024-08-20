from discord.message import Message as DiscordMessage
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Boolean
from database import Base, session
from datetime import datetime


class Message(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, nullable=False)
    discord_message_id = Column(BigInteger)
    user_id = Column(Integer)
    discord_user_id = Column(BigInteger)
    text = Column(String, nullable=False)
    hidden = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __init__(self, data):
        super().__init__()
        if isinstance(data, DiscordMessage):
            self.from_discord(data)
        else:
            self.id = data['id']
            self.channel_id = data['channel_id']
            self.discord_message_id = data['discord_message_id']
            self.user_id = data['user_id']
            self.discord_user_id = data['discord_user_id']
            self.text = data['text']
            self.hidden = data['hidden']
            self.created_at = data['created_at']
            self.last_updated = data['last_updated']

    def from_discord(self, data: DiscordMessage):
        self.discord_message_id = data.id
        self.discord_user_id = data.author.id
        self.text = data.content
        self.channel_id = data.channel.id
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
    discord_id = Column(Integer, nullable=False)
    display_name = Column(String, nullable=False)

    def __repr__(self):
        return f'<User {self.id}>'
