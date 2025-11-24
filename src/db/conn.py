from sqlalchemy import create_engine
from sqlalchemy.orm.session import sessionmaker

from src.config import config

engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def get_session():
    """
    Returns a context-managed SQLAlchemy session instance.
    Usage:
        with get_session() as session:
            # use session here
    """
    return SessionLocal()
