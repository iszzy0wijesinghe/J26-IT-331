from datetime import datetime, timedelta, timezone

import numpy as np

from components.c3_forecasting.preprocessing.m5_dataset import (
    M5DatasetConfig,
    build_m5_training_samples,
    pad_m5_samples,
)


def make_observations(
    device_id="PIPE_A_01",
    episode_id="EP001",
):

    start = datetime(
        2026, 10, 21, 0, 0,
        tzinfo=timezone.utc,
    )

    observations = []

    for index in range(20):

        timestamp = start + timedelta(
            minutes=index * 5
        )

        observations.append({
            "dataset_id": "DATASET_01",
            "device_id": device_id,
            "episode_id": episode_id,
            "timestamp": timestamp.isoformat(),
            "operating_mode": "IDLE",
            "soil_moisture_pct": 40 + index,
            "rainfall_proxy_counts": index,
            "tilt_deg": 1.0 + index * 0.1,
            "vibration_g": 0.01 + index * 0.001,
            "fsr_adc": 1000 + index * 10,
            "air_temperature_c": 28.0,
            "humidity_pct": 70 + index * 0.2,
        })

    return observations


def test_training_samples_created():

    samples = build_m5_training_samples(
        make_observations()
    )

    assert len(samples) > 0


def test_target_dimensions():

    samples = build_m5_training_samples(
        make_observations()
    )

    sample = samples[0]

    assert sample.targets.shape == (3, 7)

    assert sample.target_mask.shape == (3, 7)


def test_no_future_input_leakage():

    observations = make_observations()

    samples = build_m5_training_samples(
        observations
    )

    for sample in samples:

        origin = datetime.fromisoformat(
            sample.forecast_origin
        )

        assert sample.sequence_length <= 32

        assert origin <= datetime.fromisoformat(
            observations[-1]["timestamp"]
        )


def test_device_isolation():

    observations = (
        make_observations("PIPE_A_01")
        + make_observations("PIPE_B_01")
    )

    samples = build_m5_training_samples(
        observations
    )

    device_ids = {
        sample.device_id
        for sample in samples
    }

    assert device_ids == {
        "PIPE_A_01",
        "PIPE_B_01",
    }


def test_episode_isolation():

    observations = (
        make_observations(
            episode_id="EP001"
        )
        + make_observations(
            episode_id="EP002"
        )
    )

    samples = build_m5_training_samples(
        observations
    )

    episode_ids = {
        sample.episode_id
        for sample in samples
    }

    assert episode_ids == {
        "EP001",
        "EP002",
    }


def test_padding():

    samples = build_m5_training_samples(
        make_observations()
    )

    batch = pad_m5_samples(
        samples[:4]
    )

    assert batch["features"].shape[0] == 4

    assert batch["targets"].shape[1:] == (3, 7)

    assert batch["lengths"].shape == (4,)


def test_missing_target_mask():

    observations = make_observations()

    observations[5]["humidity_pct"] = None

    samples = build_m5_training_samples(
        observations
    )

    assert len(samples) > 0

    assert all(
        np.isfinite(sample.targets).all()
        for sample in samples
    )


def test_target_alignment():

    observations = make_observations()

    samples = build_m5_training_samples(
        observations,
        M5DatasetConfig(
            target_tolerance_minutes=0,
        ),
    )

    first_sample = samples[0]

    # The first origin is index 2 (00:10).
    # The 15-minute target is index 5 (00:25).
    assert first_sample.targets[0, 0] == 45.0