import uuid

from sqlalchemy import Column, String, Boolean, JSON, Uuid
from sqlalchemy.orm import DeclarativeBase

from src.db.conn import engine
from src.logging.logging import get_logger

logger = get_logger(__name__)

class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(String)
    name = Column(String)
    installed = Column(Boolean)

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String)
    data = Column(JSON)

class FactSheet(Base):
    __tablename__ = "fact_sheets"

    fact_sheet_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(Uuid(as_uuid=True))
    fact_sheet_name = Column(String)
    manifest_file_url = Column(String)

class AiDiscoveryData(Base):
    __tablename__ = "ai_discovery_data"
    fact_sheet_id = Column(Uuid(as_uuid=True), primary_key=True)
    languages = Column(JSON)
    teams = Column(JSON)
    contributors = Column(JSON)
    tech_stacks = Column(JSON)


def create_db_and_tables():
    """Create database tables if they don't exist."""
    Base.metadata.create_all(engine)


def init_db():
    """Initialize the database - create all tables."""
    create_db_and_tables()
    logger.info("Database initialized with SQLModel.")