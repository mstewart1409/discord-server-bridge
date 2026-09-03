from datetime import timezone

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from dsbridge.database import Database
from dsbridge.models import ChatChannels
from dsbridge.models import Message
from dsbridge.models import utcnow


def test_engine_is_the_one_supplied():
    engine = create_async_engine('sqlite+aiosqlite://')
    db = Database(engine)

    assert db.engine is engine


async def test_create_all_creates_the_tables(database):
    async with database.engine.connect() as connection:
        tables = await connection.run_sync(lambda c: inspect(c).get_table_names())

    assert {'chat_channels', 'chat_messages'} <= set(tables)
    assert 'users' not in tables


async def test_create_all_creates_only_the_tables_it_is_given(tmp_path):
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path.as_posix()}/scoped.db')
    db = Database(engine)

    await db.create_all([ChatChannels.__table__])

    async with engine.connect() as connection:
        tables = await connection.run_sync(lambda c: inspect(c).get_table_names())
    assert tables == ['chat_channels']
    await db.close()
    await engine.dispose()


async def test_timestamps_default_to_aware_utc(database):
    channel = ChatChannels(discord_channel_id=1)
    database.session.add(channel)
    await database.session.commit()

    assert channel.created_at.tzinfo is not None
    assert channel.created_at.utcoffset() == timezone.utc.utcoffset(None)


def test_utcnow_is_timezone_aware():
    now = utcnow()

    assert now.tzinfo is timezone.utc


async def test_close_leaves_the_caller_engine_usable(tmp_path):
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path.as_posix()}/close.db')
    db = Database(engine)
    await db.create_all([ChatChannels.__table__, Message.__table__])

    await db.close()

    async with db.engine.connect() as connection:
        tables = await connection.run_sync(lambda c: inspect(c).get_table_names())
    assert 'chat_channels' in tables
    await engine.dispose()
