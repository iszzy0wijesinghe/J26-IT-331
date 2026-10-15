from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from shared.contracts import (
    C3Forecast,
    C3TemporalSequence,
    C3TemporalStep,
    ForecastInputManifest,
)
from shared.enums import (
    DataQualityStatus,
    OperatingMode,
    ProcessingStatus,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def test_c3_temporal_step_accepts_variable_rate_features():
    step = C3TemporalStep(
        time=utc_now(),
        delta_t_seconds=60.0,
        operating_mode=OperatingMode.RISK,
        features={
            "soil_moisture": 67.4,
            "rainfall": 12.5,
        },
        masks={
            "soil_moisture": True,
            "rainfall": True,
        },
        ages_seconds={
            "soil_moisture": 0.0,
            "rainfall": 15.0,
        },
        quality={
            "soil_moisture": "GOOD",
        },
        provenance={
            "soil_moisture": "DIRECT",
        },
    )

    assert step.delta_t_seconds == 60.0


def test_c3_step_rejects_mask_for_unknown_feature():
    with pytest.raises(ValidationError):
        C3TemporalStep(
            time=utc_now(),
            delta_t_seconds=60.0,
            operating_mode=OperatingMode.RISK,
            features={"soil_moisture": 67.4},
            masks={
                "soil_moisture": True,
                "unknown_feature": False,
            },
        )


def test_c3_step_rejects_negative_feature_age():
    with pytest.raises(ValidationError):
        C3TemporalStep(
            time=utc_now(),
            delta_t_seconds=60.0,
            operating_mode=OperatingMode.RISK,
            features={"soil_moisture": 67.4},
            ages_seconds={"soil_moisture": -1.0},
        )


def test_c3_sequence_rejects_future_temporal_step():
    origin = utc_now()

    with pytest.raises(ValidationError):
        C3TemporalSequence(
            schema_version="1.0",
            zone_id="ZONE_01",
            forecast_origin=origin,
            feature_schema_version="C3FS_001",
            builder_version="C3FB_001",
            steps=[
                C3TemporalStep(
                    time=origin + timedelta(seconds=1),
                    delta_t_seconds=60.0,
                    operating_mode=OperatingMode.RISK,
                    features={"soil_moisture": 67.4},
                )
            ],
        )


def test_c3_sequence_rejects_out_of_order_steps():
    origin = utc_now()

    with pytest.raises(ValidationError):
        C3TemporalSequence(
            schema_version="1.0",
            zone_id="ZONE_01",
            forecast_origin=origin,
            feature_schema_version="C3FS_001",
            builder_version="C3FB_001",
            steps=[
                C3TemporalStep(
                    time=origin - timedelta(minutes=1),
                    delta_t_seconds=60.0,
                    operating_mode=OperatingMode.RISK,
                    features={"soil_moisture": 67.0},
                ),
                C3TemporalStep(
                    time=origin - timedelta(minutes=2),
                    delta_t_seconds=60.0,
                    operating_mode=OperatingMode.RISK,
                    features={"soil_moisture": 66.0},
                ),
            ],
        )


def test_forecast_manifest_traces_golden_inputs():
    origin = utc_now()

    manifest = ForecastInputManifest(
        schema_version="1.0",
        input_manifest_id="FIM_001",
        forecast_id="FC_001",
        zone_id="ZONE_01",
        forecast_origin=origin,
        feature_schema_version="C3FS_001",
        builder_version="C3FB_001",
        golden_observation_ids=[
            "GOBS_001",
            "GOBS_002",
        ],
        mode_history=[
            OperatingMode.IDLE,
            OperatingMode.RISK,
        ],
        quality_summary={"status": "GOOD"},
        provenance_summary={
            "DIRECT": 2,
        },
        generated_at=origin,
    )

    assert manifest.golden_observation_ids == [
        "GOBS_001",
        "GOBS_002",
    ]


def test_successful_c3_forecast_requires_probability():
    origin = utc_now()

    with pytest.raises(ValidationError):
        C3Forecast(
            schema_version="1.0",
            forecast_id="FC_001",
            zone_id="ZONE_01",
            forecast_origin=origin,
            history_start=origin - timedelta(hours=1),
            history_end=origin,
            horizon_minutes=15,
            risk_probability=None,
            risk_class=None,
            input_quality_status=DataQualityStatus.GOOD,
            processing_status=ProcessingStatus.OK,
            model_version="C3_MODEL_001",
            feature_schema_version="C3FS_001",
            input_manifest_id="FIM_001",
            generated_at=origin,
        )


def test_successful_c3_forecast_accepts_probability():
    origin = utc_now()

    forecast = C3Forecast(
        schema_version="1.0",
        forecast_id="FC_001",
        zone_id="ZONE_01",
        forecast_origin=origin,
        history_start=origin - timedelta(hours=1),
        history_end=origin,
        horizon_minutes=15,
        risk_probability=0.73,
        risk_class="HIGH",
        input_quality_status=DataQualityStatus.GOOD,
        processing_status=ProcessingStatus.OK,
        model_version="C3_MODEL_001",
        feature_schema_version="C3FS_001",
        input_manifest_id="FIM_001",
        generated_at=origin,
    )

    assert forecast.risk_probability == 0.73


def test_c3_model_unavailable_cannot_fabricate_low_risk():
    origin = utc_now()

    with pytest.raises(ValidationError):
        C3Forecast(
            schema_version="1.0",
            forecast_id="FC_002",
            zone_id="ZONE_01",
            forecast_origin=origin,
            history_start=origin - timedelta(hours=1),
            history_end=origin,
            horizon_minutes=15,
            risk_probability=0.0,
            risk_class="LOW",
            input_quality_status=DataQualityStatus.INSUFFICIENT,
            processing_status=ProcessingStatus.MODEL_UNAVAILABLE,
            model_version=None,
            feature_schema_version="C3FS_001",
            input_manifest_id="FIM_002",
            generated_at=origin,
        )


def test_c3_model_unavailable_returns_explicit_empty_prediction():
    origin = utc_now()

    forecast = C3Forecast(
        schema_version="1.0",
        forecast_id="FC_003",
        zone_id="ZONE_01",
        forecast_origin=origin,
        history_start=origin - timedelta(hours=1),
        history_end=origin,
        horizon_minutes=15,
        risk_probability=None,
        risk_class=None,
        input_quality_status=DataQualityStatus.INSUFFICIENT,
        processing_status=ProcessingStatus.MODEL_UNAVAILABLE,
        model_version=None,
        feature_schema_version="C3FS_001",
        input_manifest_id="FIM_003",
        generated_at=origin,
    )

    assert forecast.risk_probability is None
    assert forecast.risk_class is None
