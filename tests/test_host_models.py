"""The bridge maps onto the host application's own models, in the host's own registry."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import configure_mappers
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

from dsbridge.database import Database
from dsbridge.models import ChatChannelsMixin
from dsbridge.models import MessageMixin
from dsbridge.server import Server
from tests.conftest import discord_channel
from tests.conftest import discord_message

HostBase = declarative_base()


class User(HostBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class HostChannel(ChatChannelsMixin, HostBase):
    __tablename__ = 'chat_channels'

    tawk_channel_id = Column(String)


class HostMessage(MessageMixin, HostBase):
    __tablename__ = 'chat_messages'

    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    read = Column(Integer, nullable=False, default=0)

    user = relationship('User', uselist=False)


@pytest.fixture
async def host_database(tmp_path):
    configure_mappers()
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path.as_posix()}/host.db')
    db = Database(engine)
    await db.create_all(HostBase.metadata.sorted_tables)
    yield db
    await db.close()
    await engine.dispose()


@pytest.fixture
def host_server(host_database):
    server = Server(
        session=host_database.session,
        on_change=AsyncMock(),
        display_name={7: 'Alice'}.get,
        message_model=HostMessage,
        channel_model=HostChannel,
    )
    server.discord_bot = MagicMock()
    server.discord_bot.bot.get_channel = MagicMock(return_value=discord_channel())
    return server


def test_the_host_owns_the_mapping():
    assert HostMessage.__table__.metadata is HostBase.metadata
    assert HostMessage.user_id.property.columns[0].foreign_keys
    assert 'tawk_channel_id' in HostChannel.__table__.columns


async def test_discord_message_is_written_to_the_host_model(host_server, host_database):
    await host_server.send_to_server(discord_message(message_id=500, channel_id=777))

    async with host_database.session_factory() as session:
        message = (await session.execute(select(HostMessage))).scalar_one()
        assert message.discord_message_id == 500
        assert message.user_id is None
        assert message.read == 0

        channel = await session.get(HostChannel, message.channel_id)
        assert channel.discord_channel_id == 777


async def test_host_message_is_mirrored_onto_discord(host_server, host_database):
    async with host_database.session_factory() as session:
        session.add(User(id=7, name='Alice'))
        channel = HostChannel(discord_channel_id=222)
        session.add(channel)
        await session.commit()

        message = HostMessage.from_discord(discord_message(), channel)
        message.user_id = 7
        session.add(message)
        await session.commit()
        message_id = message.id

    await host_server.handle_server_message(message_id)

    embed = host_server.discord_bot.bot.get_channel().send.await_args.kwargs['embed']
    assert embed.title == 'Alice'
