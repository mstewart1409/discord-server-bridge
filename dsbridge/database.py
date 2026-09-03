from asyncio import current_task

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import async_scoped_session
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Database:
    def __init__(self, engine: AsyncEngine):
        """
        Build the session registry for a caller supplied engine.

        The engine belongs to the host application: this class never creates
        nor disposes it, so the bridge shares the connection pool the host
        already uses.

        Args:
            engine: An async SQLAlchemy engine, built with ``create_async_engine``
                and an asyncio driver such as ``postgresql+psycopg://``.
        """
        self.engine = engine
        self.session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        self.session = async_scoped_session(self.session_factory, scopefunc=current_task)

    async def create_all(self, tables):
        """
        Create the given tables if they do not exist, leaving the rest of the schema alone.

        The bridge may share a registry, and therefore a ``MetaData``, with the host
        application, so only the tables it was handed are ever created.

        Args:
            tables: The ``Table`` objects to create.
        """
        tables = list(tables)
        if not tables:
            return

        async with self.engine.begin() as connection:
            await connection.run_sync(tables[0].metadata.create_all, tables=tables)

    async def close(self):
        """
        Release the session registry, leaving the caller's engine open.
        """
        await self.session.remove()
