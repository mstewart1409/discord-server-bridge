from asyncio import current_task

from sqlalchemy.ext.asyncio import async_scoped_session
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def build_database_uri(
    name, username, password, host='localhost', port=5432, engine='postgresql+psycopg'
):
    """
    Build a SQLAlchemy database URI from its parts.

    Args:
        name: Database name.
        username: Database user.
        password: Database password.
        host: Database host.
        port: Database port.
        engine: SQLAlchemy dialect. Must name an asyncio driver.

    Returns:
        The assembled database URI.
    """
    return f'{engine}://{username}:{password}@{host}:{port}/{name}'


class Database:
    def __init__(
        self,
        database_uri: str,
        echo: bool = False,
        pool_size: int | None = None,
        max_overflow: int | None = None,
    ):
        """
        Create the async engine and session registry for the given database.

        Args:
            database_uri: SQLAlchemy database URI naming an asyncio driver,
                such as ``postgresql+psycopg://``.
            echo: Whether SQLAlchemy should log emitted SQL.
            pool_size: Connections to keep open in the pool. Defaults to SQLAlchemy's.
            max_overflow: Connections allowed beyond ``pool_size``. Defaults to SQLAlchemy's.
        """
        # Only forward pool options that were set, so dialects whose default pool
        # does not accept them (such as SQLite) keep working.
        pool_options = {}
        if pool_size is not None:
            pool_options['pool_size'] = pool_size
        if max_overflow is not None:
            pool_options['max_overflow'] = max_overflow

        self.engine = create_async_engine(
            database_uri, echo=echo, pool_pre_ping=True, **pool_options
        )
        self.session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        self.session = async_scoped_session(self.session_factory, scopefunc=current_task)

    async def create_all(self):
        """
        Create any tables that do not yet exist.
        """
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self):
        """
        Release the session registry and close every pooled connection.
        """
        await self.session.remove()
        await self.engine.dispose()
