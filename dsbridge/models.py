from datetime import datetime
from datetime import timezone

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


def utcnow():
    """The current time as a timezone aware UTC datetime."""
    return datetime.now(timezone.utc)


class ChatChannels(Base):
    __tablename__ = 'chat_channels'

    id = Column(Integer, primary_key=True)
    discord_channel_id = Column(BigInteger, index=True)
    public = Column(Boolean, nullable=False, default=False)
    closed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    messages = relationship(
        'Message',
        uselist=True,
        back_populates='channel',
        primaryjoin='ChatChannels.id==Message.channel_id',
    )

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Message(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('chat_channels.id'), nullable=False, index=True)
    discord_message_id = Column(BigInteger, index=True)
    user_id = Column(Integer, index=True)
    """Identifies the author in the host application; None for Discord-origin messages."""
    discord_user_id = Column(BigInteger)
    text = Column(String, nullable=False)
    hidden = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    channel = relationship(
        'ChatChannels',
        uselist=False,
        back_populates='messages',
        primaryjoin='Message.channel_id==ChatChannels.id',
    )

    __table_args__ = (Index('ix_channel_id_hidden', 'channel_id', 'hidden'),)

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
