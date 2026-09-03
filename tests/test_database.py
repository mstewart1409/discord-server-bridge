from datetime import timezone

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine

from dsbridge.database import Database
from dsbridge.database import build_database_uri
from dsbridge.models import ChatChannels
from dsbridge.models import utcnow


def test_build_database_uri_defaults_to_an_async_driver():
    uri = build_database_uri(name='bets', username='root', password='pass')

    assert uri == 'postgresql+psycopg://root:pass@localhost:5432/bets'


def test_build_database_uri_honours_overrides():
    uri = build_database_uri(name='bets', username='root', password='pass',
                             host='db', port=6543, engine='postgresql+asyncpg')

    assert uri == 'postgresql+asyncpg://root:pass@db:6543/bets'


def test_engine_is_async():
    db = Database('postgresql+psycopg://u:p@localhost:5432/db')

    assert isinstance(db.engine, AsyncEngine)


def test_pool_options_are_forwarded():
    db = Database('postgresql+psycopg://u:p@localhost:5432/db', pool_size=7, max_overflow=3)

    assert db.engine.pool.size() == 7
    assert db.engine.pool._max_overflow == 3


def test_pool_options_default_to_sqlalchemys():
    db = Database('postgresql+psycopg://u:p@localhost:5432/db')

    assert db.engine.pool.size() == 5
    assert db.engine.pool._max_overflow == 10


async def test_create_all_creates_the_tables(database):
    async with database.engine.connect() as connection:
        tables = await connection.run_sync(lambda c: inspect(c).get_table_names())

    assert {'chat_channels', 'chat_messages', 'users'} <= set(tables)


async def test_timestamps_default_to_aware_utc(database):
    channel = ChatChannels(discord_channel_id=1)
    database.session.add(channel)
    await database.session.commit()

    assert channel.created_at.tzinfo is not None
    assert channel.created_at.utcoffset() == timezone.utc.utcoffset(None)


def test_utcnow_is_timezone_aware():
    now = utcnow()

    assert now.tzinfo is timezone.utc


async def test_dispose_replaces_the_connection_pool(tmp_path):
    db = Database(f'sqlite+aiosqlite:///{tmp_path.as_posix()}/dispose.db')
    await db.create_all()
    pool_before = db.engine.pool

    await db.dispose()

    assert db.engine.pool is not pool_before
