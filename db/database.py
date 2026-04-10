from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from core.config import settings

engine = create_engine(settings.db_url, echo=False)


def create_db_and_tables() -> None:
    """Initializes the SQLite database schemas."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency for session management."""
    with Session(engine) as session:
        yield session
