from sqlalchemy import create_engine, text

from database.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from shared.config import GeoNexSettings


def make_test_settings() -> GeoNexSettings:
    return GeoNexSettings(
        _env_file=None,
        db_host="localhost",
        db_port=5432,
        db_name="geonex",
        db_user="geonex",
        db_password="",
    )


def test_database_url_uses_postgresql_psycopg():
    settings = make_test_settings()

    assert settings.database_url.startswith(
        "postgresql+psycopg://"
    )


def test_session_factory_configuration():
    settings = make_test_settings()

    engine = create_database_engine(settings)
    factory = create_session_factory(engine)

    assert factory.kw["autoflush"] is False
    assert factory.kw["expire_on_commit"] is False

    engine.dispose()


def test_session_scope_commits_successfully():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE test_items (
                    id INTEGER PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
        )

    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        session.execute(
            text(
                """
                INSERT INTO test_items (id, value)
                VALUES (1, 'geonex')
                """
            )
        )

    with engine.connect() as connection:
        value = connection.execute(
            text(
                """
                SELECT value
                FROM test_items
                WHERE id = 1
                """
            )
        ).scalar_one()

    assert value == "geonex"

    engine.dispose()


def test_session_scope_rolls_back_on_failure():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE test_items (
                    id INTEGER PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
        )

    factory = create_session_factory(engine)

    try:
        with session_scope(factory) as session:
            session.execute(
                text(
                    """
                    INSERT INTO test_items (id, value)
                    VALUES (1, 'should_rollback')
                    """
                )
            )

            raise RuntimeError("forced failure")

    except RuntimeError:
        pass

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM test_items")
        ).scalar_one()

    assert count == 0

    engine.dispose()