from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dsbridge.config import app_config
from sqlalchemy.orm import scoped_session


engine = create_engine(app_config.SQLALCHEMY_DATABASE_URI, echo=True, pool_pre_ping=True)
session_factory = sessionmaker(bind=engine)
session = scoped_session(session_factory)
Base = declarative_base()
