"""
core/database.py
────────────────
SQLAlchemy database engine, session factory, and Base class.
All models inherit from Base.  get_db() is used as a FastAPI dependency.
"""


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings


engine = create_engine(
    settings.DATABASE_URL, 
    connect_args = { "check_same_thread": False }
    )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All ORM models inherit from this."""
    pass


def init_db():
    from backend.models import users, document
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        