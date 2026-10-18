"""Tests for causal C3 tabular feature extraction."""

import pytest

from components.c3_forecasting.features.tabular_features import (
    extract_tabular_features,
)


def make_step(
    time,
    value,
    *,
    observed=True,
    mode="IDLE",
    received_at=None,
):
    return {
        "time": time,
        "operating_mode": mode,
        "features": {
            "soil_moisture_pct": value,
        },
        "masks": {
            "soil_moisture_pct": observed,
        },
        "quality": {
            "imputed_flags": {
                "soil_moisture_pct": False,
            },
            "corrected_flags": {
                "soil_moisture_pct": False,
            },
        },
        "provenance": {
            "received_at": received_at or time,
        },
    }


def make_sequence(steps):
    return {
        "forecast_origin": "2026-01-01T10:30:00+00:00",
        "steps": steps,
    }


def test_latest_and_mean():
    sequence = make_sequence(
        [
            make_step("2026-01-01T10:00:00+00:00", 35.0),
            make_step("2026-01-01T10:15:00+00:00", 36.0),
            make_step("2026-01-01T10:30:00+00:00", 37.0),
        ]
    )

    result = extract_tabular_features(sequence)

    assert result["soil_moisture_pct_latest"] == 37.0
    assert result["soil_moisture_pct_mean"] == 36.0


def test_time_normalized_trend():
    sequence = make_sequence(
        [
            make_step("2026-01-01T10:00:00+00:00", 35.0),
            make_step("2026-01-01T10:30:00+00:00", 37.0),
        ]
    )

    result = extract_tabular_features(sequence)

    assert result["soil_moisture_pct_change"] == 2.0
    assert result["soil_moisture_pct_trend_per_minute"] == pytest.approx(
        2.0 / 30.0
    )


def test_missing_placeholder_is_ignored():
    sequence = make_sequence(
        [
            make_step("2026-01-01T10:00:00+00:00", 42.0),
            make_step(
                "2026-01-01T10:15:00+00:00",
                0.0,
                observed=False,
            ),
        ]
    )

    result = extract_tabular_features(sequence)

    assert result["soil_moisture_pct_latest"] == 42.0
    assert result["soil_moisture_pct_valid_count"] == 1.0
    assert result["soil_moisture_pct_valid_fraction"] == 0.5


def test_future_received_packet_is_excluded():
    sequence = make_sequence(
        [
            make_step("2026-01-01T10:00:00+00:00", 40.0),
            make_step(
                "2026-01-01T10:15:00+00:00",
                99.0,
                received_at="2026-01-01T10:35:00+00:00",
            ),
        ]
    )

    result = extract_tabular_features(sequence)

    assert result["soil_moisture_pct_latest"] == 40.0


def test_mode_one_hot_encoding():
    sequence = make_sequence(
        [
            make_step(
                "2026-01-01T10:00:00+00:00",
                40.0,
                mode="RISK",
            ),
        ]
    )

    result = extract_tabular_features(sequence)

    assert result["mode_RISK"] == 1.0
    assert result["mode_IDLE"] == 0.0


def test_no_eligible_history_raises():
    sequence = make_sequence(
        [
            make_step(
                "2026-01-01T10:40:00+00:00",
                40.0,
            ),
        ]
    )

    with pytest.raises(ValueError):
        extract_tabular_features(sequence)