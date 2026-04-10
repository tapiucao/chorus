from sqlmodel import SQLModel, create_engine, Session
from core.models import Run, Artifact, Checkpoint

# SQLite Persistence Day 0
sqlite_file_name = "chorus.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# Using echo=False to keep logs clean, can be toggled for debugging
engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    """Initializes the SQLite database schemas."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency for session management."""
    with Session(engine) as session:
        yield session
