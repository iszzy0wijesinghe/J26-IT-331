from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.config import GeoNexSettings, get_settings


def create_database_engine(
    settings: GeoNexSettings | None = None,
    *,
    echo: bool = False,
) -> Engine:
    """Create a GeoNex SQLAlchemy engine."""

    resolved_settings = settings or get_settings()

    return create_engine(
        resolved_settings.database_url,
        echo=echo,
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    """Create a session factory bound to the supplied engine."""

    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(
    session_factory: sessionmaker[Session],
) -> Iterator[Session]:
    """Provide transactional commit/rollback session handling."""

    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()