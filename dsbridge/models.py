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
from sqlalchemy.orm import declared_attr
from sqlalchemy.orm import relationship

from dsbridge.database import Base


def utcnow():
    """The current time as a timezone aware UTC datetime."""
    return datetime.now(timezone.utc)


class ChatChannelsMixin:
    """
    The columns the bridge needs on a channel model.

    Mix it into a class of your own declarative base to keep the mapping, and any
    relationship to your own tables, in your application's registry. Declaring an
    attribute of the same name on the concrete class overrides any of these.
    """

    id = Column(Integer, primary_key=True)
    discord_channel_id = Column(BigInteger, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class MessageMixin:
    """
    The columns the bridge needs on a message model.

    ``user_id`` deliberately carries no foreign key: users belong to the host
    application, so the concrete class is where that column gains its constraint and
    its relationship. Set ``__chat_channels_tablename__`` when the channel table is
    not named ``chat_channels``.
    """

    __chat_channels_tablename__ = 'chat_channels'

    id = Column(Integer, primary_key=True)
    discord_message_id = Column(BigInteger, index=True)
    user_id = Column(Integer, index=True)
    """Identifies the author in the host application; None for Discord-origin messages."""
    discord_user_id = Column(BigInteger)
    text = Column(String, nullable=False)
    hidden = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    @declared_attr
    def channel_id(cls):  # noqa: N805
        # A column carrying a foreign key must be built per concrete class.
        return Column(
            Integer,
            ForeignKey(f'{cls.__chat_channels_tablename__}.id'),
            nullable=False,
            index=True,
        )

    @classmethod
    def from_discord(cls, data: DiscordMessage, channel):
        """
        Build an unsaved row from a message as Discord delivered it.

        Args:
            data: The Discord message.
            channel: The channel row the message belongs to.

        Returns:
            A new instance of the concrete message model.
        """
        return cls(
            discord_message_id=data.id,
            discord_user_id=data.author.id,
            text=data.content,
            channel_id=channel.id,
            user_id=None,
        )

    def __repr__(self):
        return f'<{type(self).__name__} {self.id}>'


class ChatChannels(ChatChannelsMixin, Base):
    """The default channel model, for hosts that map none of their own."""

    __tablename__ = 'chat_channels'

    public = Column(Boolean, nullable=False, default=False)
    closed = Column(Boolean, nullable=False, default=False)

    messages = relationship(
        'Message',
        uselist=True,
        back_populates='channel',
        primaryjoin='ChatChannels.id==Message.channel_id',
    )


class Message(MessageMixin, Base):
    """The default message model, for hosts that map none of their own."""

    __tablename__ = 'chat_messages'

    channel = relationship(
        'ChatChannels',
        uselist=False,
        back_populates='messages',
        primaryjoin='Message.channel_id==ChatChannels.id',
    )

    __table_args__ = (Index('ix_channel_id_hidden', 'channel_id', 'hidden'),)
