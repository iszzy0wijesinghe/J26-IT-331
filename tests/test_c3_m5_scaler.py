import numpy as np

from components.c3_forecasting.preprocessing.m5_scaler import (
    M5SensorScaler,
)


def make_features():

    features = np.zeros(
        (5, 21),
        dtype=np.float32,
    )

    for index in range(5):

        features[index, :7] = [
            40 + index,
            10 + index,
            1 + index,
            0.01 + index * 0.001,
            1000 + index * 10,
            28,
            70 + index,
        ]

        features[index, 7:14] = 1.0

        features[index, 14] = np.log1p(300)

        features[index, 15] = 1.0

        features[index, 17] = 1.0

    return features


def test_scaler_fit():

    scaler = M5SensorScaler()

    scaler.fit([make_features()])

    assert scaler.state is not None


def test_feature_normalization():

    features = make_features()

    scaler = M5SensorScaler().fit(
        [features]
    )

    normalized = scaler.transform_features(
        features
    )

    assert np.isfinite(normalized).all()


def test_mode_features_preserved():

    features = make_features()

    scaler = M5SensorScaler().fit(
        [features]
    )

    normalized = scaler.transform_features(
        features
    )

    np.testing.assert_array_equal(
        normalized[:, 16:],
        features[:, 16:],
    )


def test_time_features_preserved():

    features = make_features()

    scaler = M5SensorScaler().fit(
        [features]
    )

    normalized = scaler.transform_features(
        features
    )

    np.testing.assert_array_equal(
        normalized[:, 14:16],
        features[:, 14:16],
    )


def test_inverse_target_transform():

    features = make_features()

    scaler = M5SensorScaler().fit(
        [features]
    )

    targets = np.asarray(
        [
            [
                [50, 15, 2, 0.02, 1100, 28, 80],
                [55, 18, 3, 0.03, 1200, 27, 85],
                [60, 20, 4, 0.04, 1300, 26, 90],
            ]
        ],
        dtype=np.float32,
    )

    normalized = scaler.transform_targets(
        targets
    )

    restored = scaler.inverse_transform_targets(
        normalized
    )

    np.testing.assert_allclose(
        restored,
        targets,
        atol=1e-4,
    )


def test_scaler_serialization():

    features = make_features()

    scaler = M5SensorScaler().fit(
        [features]
    )

    data = scaler.to_dict()

    restored = M5SensorScaler.from_dict(
        data
    )

    np.testing.assert_allclose(
        scaler.state.sensor_mean,
        restored.state.sensor_mean,
    )


def test_missing_sensor_remains_zero():

    features = make_features()

    features[2, 0] = 0.0
    features[2, 7] = 0.0

    scaler = M5SensorScaler().fit(
        [features]
    )

    normalized = scaler.transform_features(
        features
    )

    assert normalized[2, 0] == 0.0