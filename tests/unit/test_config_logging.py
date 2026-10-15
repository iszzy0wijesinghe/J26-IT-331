import json
import logging

import pytest
from pydantic import ValidationError

from shared.config import GeoNexSettings
from shared.logging import (
    JsonFormatter,
    reset_component,
    reset_correlation_id,
    set_component,
    set_correlation_id,
)


def test_default_settings_are_development_safe():
    """Verify that default GeoNex settings are suitable for development."""

    settings = GeoNexSettings(_env_file=None)

    assert settings.env == "development"
    assert settings.db_host == "127.0.0.1"
    assert settings.db_port == 5433
    assert settings.db_name == "geonex"
    assert settings.log_level == "INFO"


def test_database_url_is_built_from_settings():
    """Verify that SQLAlchemy connection URLs use the configured values."""

    settings = GeoNexSettings(
        _env_file=None,
        db_host="db.internal",
        db_port=5433,
        db_name="geonex_test",
        db_user="tester",
        db_password="secret",
    )

    url = settings.database_url

    assert url.drivername == "postgresql+psycopg"
    assert url.username == "tester"
    assert url.password == "secret"
    assert url.host == "db.internal"
    assert url.port == 5433
    assert url.database == "geonex_test"

    # Credentials must not appear in normal URL rendering.
    assert "secret" not in str(url)


def test_database_url_supports_special_characters_in_password():
    """Verify that database passwords containing special characters work."""

    password = "test@pass:/#word"

    settings = GeoNexSettings(
        _env_file=None,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="geonex_test",
        db_user="tester",
        db_password=password,
    )

    url = settings.database_url

    assert url.password == password

    # Verify that SQLAlchemy can render a valid connection URL.
    assert url.render_as_string(hide_password=False).startswith("postgresql+psycopg://")

    # Credentials must remain hidden in normal string output.
    assert password not in str(url)


def test_invalid_database_port_is_rejected():
    """Verify that invalid PostgreSQL ports are rejected."""

    with pytest.raises(ValidationError):
        GeoNexSettings(
            _env_file=None,
            db_port=70000,
        )


def test_unknown_environment_is_rejected():
    """Verify that unsupported GeoNex environments are rejected."""

    with pytest.raises(ValidationError):
        GeoNexSettings(
            _env_file=None,
            env="unknown",
        )


def test_json_formatter_includes_trace_context():
    """Verify that structured logs include correlation and component IDs."""

    formatter = JsonFormatter()

    correlation_token = set_correlation_id("CORR_001")
    component_token = set_component("C3")

    try:
        record = logging.LogRecord(
            name="geonex.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="forecast generated",
            args=(),
            exc_info=None,
        )

        output = json.loads(formatter.format(record))

        assert output["level"] == "INFO"
        assert output["message"] == "forecast generated"
        assert output["correlation_id"] == "CORR_001"
        assert output["component"] == "C3"

    finally:
        reset_component(component_token)
        reset_correlation_id(correlation_token)


def test_json_formatter_preserves_structured_extra_fields():
    """Verify that structured logging preserves additional metadata."""

    formatter = JsonFormatter()

    record = logging.LogRecord(
        name="geonex.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="packet accepted",
        args=(),
        exc_info=None,
    )

    record.packet_id = "PKT_001"
    record.zone_id = "ZONE_01"

    output = json.loads(formatter.format(record))

    assert output["packet_id"] == "PKT_001"
    assert output["zone_id"] == "ZONE_01"
