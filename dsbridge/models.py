from datetime import datetime

import pytz
from discord.message import Message as DiscordMessage
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from dsbridge.database import Base
from dsbridge.database import session


class ChatChannels(Base):
    __tablename__ = 'chat_channels'

    id = Column(Integer, primary_key=True)
    discord_channel_id = Column(BigInteger, index=True)
    public = Column(Boolean, nullable=False, default=False)
    closed = Column(Boolean, nullable=False, default=False)
    email_notifs = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    messages = relationship('Message', uselist=True, back_populates='channel', primaryjoin='ChatChannels.id==Message.channel_id')

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Message(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('chat_channels.id'), nullable=False, index=True)
    discord_message_id = Column(BigInteger, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    discord_user_id = Column(BigInteger)
    text = Column(String, nullable=False)
    hidden = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user = relationship('User', uselist=False, primaryjoin='Message.user_id==User.id')

    channel = relationship('ChatChannels', uselist=False, back_populates='messages',
                           primaryjoin='Message.channel_id==ChatChannels.id')

    __table_args__ = (
        Index('ix_channel_id_hidden', 'channel_id', 'hidden'),
    )

    def __init__(self, data, channel):
        super().__init__()
        if isinstance(data, DiscordMessage):
            self.from_discord(data, channel)
        else:
            raise ValueError('Unexpected initialization type')

    def from_discord(self, data: DiscordMessage, channel):
        self.discord_message_id = data.id
        self.discord_user_id = data.author.id
        self.text = data.content
        self.channel_id = channel.id
        self.user_id = None

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return f'<Message {self.id}>'


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    display_name = Column(String, nullable=False)

    def __repr__(self):
        return f'<User {self.id}>'
