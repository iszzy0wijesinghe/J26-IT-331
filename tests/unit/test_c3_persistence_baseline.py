"""Tests for the C3 strict persistence baseline."""


from components.c3_forecasting.persistence_baseline import (
    predict_persistence,
)


def make_step(
    observed_at,
    received_at,
    value,
    *,
    observed=True,
    imputed=False,
    corrected=False,
):
    return {
        "time": observed_at,
        "features": {
            "soil_moisture_pct": value,
        },
        "masks": {
            "soil_moisture_pct": observed,
        },
        "quality": {
            "imputed_flags": {
                "soil_moisture_pct": imputed,
            },
            "corrected_flags": {
                "soil_moisture_pct": corrected,
            },
        },
        "provenance": {
            "received_at": received_at,
        },
    }


def make_sequence(steps):
    return {
        "forecast_origin": "2026-01-01T10:20:00+00:00",
        "steps": steps,
    }


def test_uses_latest_valid_observation():
    sequence = make_sequence(
        [
            make_step(
                "2026-01-01T10:00:00+00:00",
                "2026-01-01T10:00:01+00:00",
                42.5,
            ),
            make_step(
                "2026-01-01T10:15:00+00:00",
                "2026-01-01T10:15:01+00:00",
                44.2,
            ),
        ]
    )

    result = predict_persistence(sequence)

    assert result.prediction == 44.2
    assert result.source_age_seconds == 300.0


def test_ignores_unobserved_placeholder():
    sequence = make_sequence(
        [
            make_step(
                "2026-01-01T10:00:00+00:00",
                "2026-01-01T10:00:01+00:00",
                42.5,
            ),
            make_step(
                "2026-01-01T10:15:00+00:00",
                "2026-01-01T10:15:01+00:00",
                0.0,
                observed=False,
            ),
        ]
    )

    result = predict_persistence(sequence)

    assert result.prediction == 42.5


def test_rejects_future_received_packet():
    sequence = make_sequence(
        [
            make_step(
                "2026-01-01T10:00:00+00:00",
                "2026-01-01T10:00:01+00:00",
                42.5,
            ),
            make_step(
                "2026-01-01T10:15:00+00:00",
                "2026-01-01T10:25:00+00:00",
                99.0,
            ),
        ]
    )

    result = predict_persistence(sequence)

    assert result.prediction == 42.5


def test_rejects_imputed_measurement():
    sequence = make_sequence(
        [
            make_step(
                "2026-01-01T10:00:00+00:00",
                "2026-01-01T10:00:01+00:00",
                42.5,
            ),
            make_step(
                "2026-01-01T10:15:00+00:00",
                "2026-01-01T10:15:01+00:00",
                50.0,
                imputed=True,
            ),
        ]
    )

    result = predict_persistence(sequence)

    assert result.prediction == 42.5


def test_rejects_corrected_measurement():
    sequence = make_sequence(
        [
            make_step(
                "2026-01-01T10:00:00+00:00",
                "2026-01-01T10:00:01+00:00",
                42.5,
            ),
            make_step(
                "2026-01-01T10:15:00+00:00",
                "2026-01-01T10:15:01+00:00",
                50.0,
                corrected=True,
            ),
        ]
    )

    result = predict_persistence(sequence)

    assert result.prediction == 42.5


def test_returns_unavailable_without_valid_history():
    sequence = make_sequence(
        [
            make_step(
                "2026-01-01T10:15:00+00:00",
                "2026-01-01T10:15:01+00:00",
                0.0,
                observed=False,
            ),
        ]
    )

    result = predict_persistence(sequence)

    assert result.prediction is None
    assert (
        result.unavailable_reason
        == "NO_VALID_HISTORICAL_OBSERVATION"
    )