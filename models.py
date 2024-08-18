from discord.message import Message as DiscordMessage
from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from database import Base, session
from datetime import datetime


class Message(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, nullable=False)
    user_id = Column(Integer)
    discord_id = Column(BigInteger)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __init__(self, data):
        super().__init__()
        self.session = session
        if isinstance(data, DiscordMessage):
            self.from_discord(data)
        else:
            self.user_id = data['user_id']
            self.discord_id = data['discord_id']
            self.text = data['text']

    def from_discord(self, data: DiscordMessage):
        self.discord_id = data.id
        self.text = data.content
        self.channel_id = data.channel.id
        self.user_id = None

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'discord_id': self.discord_id,
            'text': self.text,
            'created_at': self.created_at,
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
