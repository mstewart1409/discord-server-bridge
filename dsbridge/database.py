from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker


Base = declarative_base()


def build_database_uri(name, username, password, host='localhost', port=5432,
                       engine='postgresql'):
    """
    Build a SQLAlchemy database URI from its parts.

    Args:
        name: Database name.
        username: Database user.
        password: Database password.
        host: Database host.
        port: Database port.
        engine: SQLAlchemy dialect.

    Returns:
        The assembled database URI.
    """
    return f'{engine}://{username}:{password}@{host}:{port}/{name}'


class Database:
    def __init__(self, database_uri: str, echo: bool = False):
        """
        Create the engine and session registry for the given database.

        Args:
            database_uri: SQLAlchemy database URI.
            echo: Whether SQLAlchemy should log emitted SQL.
        """
        self.engine = create_engine(database_uri, echo=echo, pool_pre_ping=True)
        self.session_factory = sessionmaker(bind=self.engine)
        self.session = scoped_session(self.session_factory)

    def create_all(self):
        """
        Create any tables that do not yet exist.
        """
        Base.metadata.create_all(self.engine)
