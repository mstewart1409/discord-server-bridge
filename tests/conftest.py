from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from discord.message import Message as DiscordMessage
from sqlalchemy.ext.asyncio import create_async_engine

from dsbridge.database import Database
from dsbridge.models import ChatChannels
from dsbridge.models import Message
from dsbridge.server import Server


def discord_message(message_id=111, channel_id=222, author_id=333, content='hello'):
    """Build a stand-in that still satisfies isinstance(..., DiscordMessage)."""
    message = MagicMock(spec=DiscordMessage)
    message.id = message_id
    message.content = content
    message.author.id = author_id
    message.channel.id = channel_id
    return message


def discord_channel(sent_id=999, fetched_id=888):
    channel = MagicMock()
    channel.send = AsyncMock(return_value=MagicMock(id=sent_id))
    fetched = MagicMock(id=fetched_id)
    fetched.edit = AsyncMock(return_value=MagicMock(id=fetched_id))
    fetched.delete = AsyncMock()
    channel.fetch_message = AsyncMock(return_value=fetched)
    channel.fetched = fetched
    return channel


@pytest.fixture
async def database(tmp_path):
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path.as_posix()}/test.db')
    db = Database(engine)
    await db.create_all()
    yield db
    await db.close()
    await engine.dispose()


@pytest.fixture
def bot_channel():
    return discord_channel()


@pytest.fixture
def host():
    return AsyncMock()


def changes(host):
    """The payloads the bridge reported to the host, in order."""
    return [call.args[0] for call in host.await_args_list]


@pytest.fixture
def names():
    """Stands in for the host's user directory."""
    return {7: 'Alice'}


@pytest.fixture
def server(database, bot_channel, host, names):
    """A Server wired to a recording host and a fake Discord bot."""
    instance = Server(session=database.session, on_change=host, display_name=names.get)
    instance.discord_bot = MagicMock()
    instance.discord_bot.bot.get_channel = MagicMock(return_value=bot_channel)
    return instance


@pytest.fixture
def reload(database):
    """Read a row back from the database, independent of any handler's session."""
    async def _reload(model, primary_key):
        async with database.session_factory() as session:
            return await session.get(model, primary_key)
    return _reload


@pytest.fixture
async def seeded(database):
    """A channel and a server side message already mirrored to Discord."""
    session = database.session_factory()
    channel = ChatChannels(discord_channel_id=222)
    session.add(channel)
    await session.commit()

    message = Message(discord_message(), channel)
    message.user_id = 7
    session.add(message)
    await session.commit()

    identifiers = {'channel_id': channel.id, 'user_id': message.user_id, 'message_id': message.id}
    await session.close()
    return identifiers


@pytest.fixture
async def unowned_message(database, seeded):
    """A mirrored message with no server side user, as Discord-origin rows have."""
    async with database.session_factory() as session:
        message = await session.get(Message, seeded['message_id'])
        message.user_id = None
        await session.commit()
    return seeded['message_id']


@pytest.fixture
async def edited_message(database, seeded):
    """A second message holding the edited text of the seeded one."""
    async with database.session_factory() as session:
        channel = await session.get(ChatChannels, seeded['channel_id'])
        message = Message(discord_message(message_id=112, content='edited'), channel)
        session.add(message)
        await session.commit()
        return message.id
