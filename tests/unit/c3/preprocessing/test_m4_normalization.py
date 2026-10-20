"""Unit tests for GeoNex C3 M4 normalization."""

from __future__ import annotations

import numpy as np
import pytest

from components.c3_forecasting.preprocessing.gru_dataset import (
    SENSOR_NAMES,
)
from components.c3_forecasting.preprocessing.m4_features import (
    M4_INPUT_FEATURE_COUNT,
)
from components.c3_forecasting.preprocessing.m4_normalization import (
    M4Normalizer,
)


@pytest.fixture
def training_examples() -> list[dict]:
    """Create small synthetic M4 training examples."""

    examples = []

    for sensor_value, interval in [
        (10.0, 60.0),
        (20.0, 300.0),
        (30.0, 900.0),
    ]:
        sequence = np.zeros(
            (2, M4_INPUT_FEATURE_COUNT),
            dtype=np.float32,
        )

        # Seven observed sensor measurements.
        sequence[:, :7] = sensor_value

        # Seven observation-validity masks.
        sequence[:, 7:14] = 1.0

        # First interval is unknown.
        sequence[0, 14] = 0.0
        sequence[0, 15] = 0.0

        # Second interval is known.
        sequence[1, 14] = np.log1p(interval)
        sequence[1, 15] = 1.0

        # Operating mode.
        sequence[:, 16] = 1.0

        examples.append(
            {
                "sequence": sequence,
            }
        )

    return examples


def test_fit_returns_valid_normalizer(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    assert np.isfinite(normalizer.time_mean)
    assert np.isfinite(normalizer.time_std)
    assert normalizer.time_std > 0


def test_fit_uses_known_intervals_only(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    expected = np.log1p(
        np.array(
            [60.0, 300.0, 900.0],
            dtype=np.float32,
        )
    )

    assert normalizer.time_mean == pytest.approx(
        float(expected.mean()),
        abs=1e-5,
    )

    assert normalizer.time_std == pytest.approx(
        float(expected.std()),
        abs=1e-5,
    )


def test_sensor_normalization(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    transformed = normalizer.transform(training_examples[0]["sequence"])

    assert np.isfinite(transformed[:, :7]).all()

    # Sensor value 10 is below the training mean of 20.
    assert np.all(transformed[:, :7] < 0)


def test_sensor_masks_preserved(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    original = training_examples[0]["sequence"]

    transformed = normalizer.transform(original)

    np.testing.assert_array_equal(
        transformed[:, 7:14],
        original[:, 7:14],
    )


def test_unknown_interval_remains_zero(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    transformed = normalizer.transform(training_examples[0]["sequence"])

    assert transformed[0, 14] == 0.0
    assert transformed[0, 15] == 0.0


def test_known_interval_standardization(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    original = training_examples[0]["sequence"]

    transformed = normalizer.transform(original)

    expected = (original[1, 14] - normalizer.time_mean) / normalizer.time_std

    assert transformed[1, 14] == pytest.approx(expected)


def test_mode_features_preserved(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    original = training_examples[0]["sequence"]

    transformed = normalizer.transform(original)

    np.testing.assert_array_equal(
        transformed[:, 16:20],
        original[:, 16:20],
    )


@pytest.mark.parametrize(
    ("include_time", "include_mode"),
    [
        (True, False),
        (False, True),
        (True, True),
    ],
)
def test_ablation_configuration(
    training_examples: list[dict],
    include_time: bool,
    include_mode: bool,
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    transformed = normalizer.transform(
        training_examples[0]["sequence"],
        include_time=include_time,
        include_mode=include_mode,
    )

    if not include_time:
        assert np.all(transformed[:, 14:16] == 0)

    if not include_mode:
        assert np.all(transformed[:, 16:20] == 0)


def test_fit_empty_examples_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="empty",
    ):
        M4Normalizer.fit([])


def test_fit_invalid_sequence_shape_rejected() -> None:
    examples = [
        {
            "sequence": np.zeros(
                (2, M4_INPUT_FEATURE_COUNT - 1),
                dtype=np.float32,
            )
        }
    ]

    with pytest.raises(
        ValueError,
        match="shape",
    ):
        M4Normalizer.fit(examples)


def test_transform_invalid_sequence_shape_rejected(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    invalid = np.zeros(
        (2, M4_INPUT_FEATURE_COUNT - 1),
        dtype=np.float32,
    )

    with pytest.raises(
        ValueError,
        match="shape",
    ):
        normalizer.transform(invalid)


def test_transform_nonfinite_input_rejected(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    invalid = training_examples[0]["sequence"].copy()

    invalid[0, 0] = np.nan

    with pytest.raises(
        ValueError,
        match="non-finite",
    ):
        normalizer.transform(invalid)


def test_transform_does_not_mutate_input(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    original = training_examples[0]["sequence"]
    original_copy = original.copy()

    normalizer.transform(original)

    np.testing.assert_array_equal(
        original,
        original_copy,
    )


def test_serialization_contains_required_parameters(
    training_examples: list[dict],
) -> None:
    normalizer = M4Normalizer.fit(training_examples)

    data = normalizer.to_dict()

    assert "sensor_normalizer" in data
    assert "time_mean" in data
    assert "time_std" in data

    assert data["sensor_normalizer"]["sensor_names"] == list(SENSOR_NAMES)


def test_constant_intervals_have_safe_std() -> None:
    sequence = np.zeros(
        (2, M4_INPUT_FEATURE_COUNT),
        dtype=np.float32,
    )

    sequence[:, 7:14] = 1.0

    sequence[1, 14] = np.log1p(300.0)
    sequence[1, 15] = 1.0

    examples = [
        {
            "sequence": sequence.copy(),
        }
        for _ in range(3)
    ]

    normalizer = M4Normalizer.fit(examples)

    assert normalizer.time_std == 1.0


def test_no_known_intervals_uses_safe_defaults() -> None:
    sequence = np.zeros(
        (1, M4_INPUT_FEATURE_COUNT),
        dtype=np.float32,
    )

    sequence[:, 7:14] = 1.0

    normalizer = M4Normalizer.fit(
        [
            {
                "sequence": sequence,
            }
        ]
    )

    assert normalizer.time_mean == 0.0
    assert normalizer.time_std == 1.0


# ---------------------------------------------------------
# Additional safeguards: interval-known indicator validation
# ---------------------------------------------------------


def test_fit_rejects_invalid_interval_indicator(
    training_examples: list[dict],
) -> None:
    """Reject malformed interval indicators during fitting."""

    invalid = training_examples[0]["sequence"].copy()

    invalid[1, 15] = 0.5

    with pytest.raises(
        ValueError,
        match="Interval-known indicators",
    ):
        M4Normalizer.fit(
            [
                {
                    "sequence": invalid,
                }
            ]
        )


def test_transform_rejects_invalid_interval_indicator(
    training_examples: list[dict],
) -> None:
    """Reject malformed interval indicators during transformation."""

    normalizer = M4Normalizer.fit(training_examples)

    invalid = training_examples[0]["sequence"].copy()

    invalid[1, 15] = 0.5

    with pytest.raises(
        ValueError,
        match="Interval-known indicators",
    ):
        normalizer.transform(invalid)
