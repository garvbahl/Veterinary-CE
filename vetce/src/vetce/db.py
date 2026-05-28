from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from vetce.config import settings

engine = create_engine(settings.database_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass