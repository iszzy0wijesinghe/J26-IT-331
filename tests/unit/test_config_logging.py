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
    settings = GeoNexSettings(_env_file=None)

    assert settings.env == "development"
    assert settings.db_host == "localhost"
    assert settings.db_port == 5432
    assert settings.db_name == "geonex"
    assert settings.log_level == "INFO"


def test_database_url_is_built_from_settings():
    settings = GeoNexSettings(
        _env_file=None,
        db_host="db.internal",
        db_port=5433,
        db_name="geonex_test",
        db_user="tester",
        db_password="secret",
    )

    assert settings.database_url == (
        "postgresql+psycopg://tester:secret"
        "@db.internal:5433/geonex_test"
    )


def test_invalid_database_port_is_rejected():
    with pytest.raises(ValidationError):
        GeoNexSettings(
            _env_file=None,
            db_port=70000,
        )


def test_unknown_environment_is_rejected():
    with pytest.raises(ValidationError):
        GeoNexSettings(
            _env_file=None,
            env="unknown",
        )


def test_json_formatter_includes_trace_context():
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