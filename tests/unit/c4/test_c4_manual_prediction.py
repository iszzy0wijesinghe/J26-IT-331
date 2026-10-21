"""Tests for C4 manual prediction API endpoint.

These tests verify that the manual prediction endpoint:
- Uses the actual model output without demo overrides
- Calculates anomaly score correctly as 1 - P(Trusted)
- Applies the 0.70 threshold consistently
- Allows experimental inputs without strict domain validation
- Rejects only crash-preventing invalid inputs (non-finite, negative counts)
- Supplies all 18 features correctly
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from apps.api.c4_model_explorer_api import app, ManualPredictionRequest


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def normal_request():
    """Create a normal manual prediction request."""
    return ManualPredictionRequest(
        tx_interval_s=300.0,
        rssi_dbm=-75.0,
        snr_db=10.0,
        retry_count=0,
        battery_pct=85.0,
        battery_voltage_v=3.7,
        current_ma=15.0,
        reboot_count_24h=0,
        sensor_fault_flag=False,
        freshness_status="fresh",
    )


def test_manual_prediction_uses_actual_model(client, normal_request):
    """Test that manual prediction uses the actual model output without demo override."""
    response = client.post("/api/c4/predict-manual", json=normal_request.model_dump())

    # Check that the endpoint responds
    assert response.status_code in [200, 503]  # 503 if model not found

    if response.status_code == 200:
        data = response.json()
        # Verify demo_override is False
        assert data["debug_info"]["demo_override"] is False

        # Verify predicted_label matches raw_prediction (no override)
        assert data["predicted_label"] == data["raw_prediction"]

        # Verify anomaly score is present
        assert "anomaly_score" in data["debug_info"]
        assert isinstance(data["debug_info"]["anomaly_score"], (int, float))


def test_manual_prediction_flags_unrealistic_rssi(client):
    """Test that implausible RSSI values are flagged as experimental but still run."""
    experimental_request = ManualPredictionRequest(
        tx_interval_s=300.0,
        rssi_dbm=58.0,  # Positive RSSI is unusual for LoRa
        snr_db=10.0,
        retry_count=0,
        battery_pct=85.0,
        battery_voltage_v=3.7,
        current_ma=15.0,
        reboot_count_24h=0,
        sensor_fault_flag=False,
        freshness_status="fresh",
    )

    response = client.post("/api/c4/predict-manual", json=experimental_request.model_dump())

    assert response.status_code == 200
    data = response.json()
    # Should NOT be INVALID_INPUT - should run with experimental flag
    assert data["predicted_label"] != "INVALID_INPUT"
    assert data["predicted_label"] in ["Trusted", "Untrusted", "Suspicious"]
    # Should be flagged as experimental
    assert data["debug_info"].get("is_experimental") is True


def test_manual_prediction_flags_zero_tx_interval(client):
    """Test that TX Interval = 0 is flagged as experimental but still runs."""
    experimental_request = ManualPredictionRequest(
        tx_interval_s=0.0,  # Unrealistic but allowed for exploration
        rssi_dbm=-75.0,
        snr_db=10.0,
        retry_count=0,
        battery_pct=85.0,
        battery_voltage_v=3.7,
        current_ma=15.0,
        reboot_count_24h=0,
        sensor_fault_flag=False,
        freshness_status="fresh",
    )

    response = client.post("/api/c4/predict-manual", json=experimental_request.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["predicted_label"] != "INVALID_INPUT"
    assert data["debug_info"].get("is_experimental") is True


def test_manual_prediction_flags_zero_battery_voltage(client):
    """Test that Battery Voltage = 0 is flagged as experimental but still runs."""
    experimental_request = ManualPredictionRequest(
        tx_interval_s=300.0,
        rssi_dbm=-75.0,
        snr_db=10.0,
        retry_count=0,
        battery_pct=85.0,
        battery_voltage_v=0.0,  # Unrealistic but allowed for exploration
        current_ma=15.0,
        reboot_count_24h=0,
        sensor_fault_flag=False,
        freshness_status="fresh",
    )

    response = client.post("/api/c4/predict-manual", json=experimental_request.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["predicted_label"] != "INVALID_INPUT"
    assert data["debug_info"].get("is_experimental") is True


def test_manual_prediction_rejects_negative_retry_count(client):
    """Test that negative retry count is rejected (basic sanity check)."""
    invalid_request = ManualPredictionRequest(
        tx_interval_s=300.0,
        rssi_dbm=-75.0,
        snr_db=10.0,
        retry_count=-1,  # Negative should be rejected
        battery_pct=85.0,
        battery_voltage_v=3.7,
        current_ma=15.0,
        reboot_count_24h=0,
        sensor_fault_flag=False,
        freshness_status="fresh",
    )

    response = client.post("/api/c4/predict-manual", json=invalid_request.model_dump())

    assert response.status_code == 400  # Bad Request


def test_manual_prediction_accepts_normal_rssi(client):
    """Test that normal RSSI values (-60 to -80 dBm) are accepted."""
    normal_rssi_values = [-60.0, -70.0, -75.0, -80.0]

    for rssi in normal_rssi_values:
        request = ManualPredictionRequest(
            tx_interval_s=300.0,
            rssi_dbm=rssi,
            snr_db=10.0,
            retry_count=0,
            battery_pct=85.0,
            battery_voltage_v=3.7,
            current_ma=15.0,
            reboot_count_24h=0,
            sensor_fault_flag=False,
            freshness_status="fresh",
        )

        response = client.post("/api/c4/predict-manual", json=request.model_dump())

        # Should not return INVALID_INPUT for normal RSSI
        if response.status_code == 200:
            data = response.json()
            assert data["predicted_label"] != "INVALID_INPUT", \
                f"RSSI {rssi} should be accepted but got INVALID_INPUT"
            assert data["predicted_label"] in ["Trusted", "Untrusted", "Suspicious"]


def test_manual_prediction_accepts_realistic_inputs(client):
    """Test that realistic device inputs are accepted."""
    request = ManualPredictionRequest(
        tx_interval_s=300.0,
        rssi_dbm=-75.0,
        snr_db=10.0,
        retry_count=0,
        battery_pct=85.0,
        battery_voltage_v=3.7,
        current_ma=15.0,
        reboot_count_24h=0,
        sensor_fault_flag=False,
        freshness_status="fresh",
    )

    response = client.post("/api/c4/predict-manual", json=request.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["predicted_label"] != "INVALID_INPUT"
    assert data["predicted_label"] in ["Trusted", "Untrusted", "Suspicious"]


def test_manual_prediction_supplies_all_18_features(client, normal_request):
    """Test that all 18 model features are supplied correctly."""
    response = client.post("/api/c4/predict-manual", json=normal_request.model_dump())

    if response.status_code == 200:
        data = response.json()
        features = data.get("features", {})

        # Verify all 18 features are present
        expected_features = [
            "tx_interval_s",
            "rx_delay_s",
            "freshness_status_encoded",
            "rssi_dbm",
            "rssi_deviation_db",
            "snr_db",
            "retry_count",
            "packet_size_bytes",
            "battery_pct",
            "battery_voltage_v",
            "current_ma",
            "reboot_count_24h",
            "sensor_fault_flag",
            "rolling_interval_mean",
            "rolling_interval_std",
            "rolling_rssi_mean",
            "rolling_rssi_std",
            "rolling_retry_mean",
        ]

        for feature in expected_features:
            assert feature in features, f"Missing feature: {feature}"

        # Verify feature types are numeric
        for feature, value in features.items():
            if feature != "freshness_status_encoded":
                assert isinstance(value, (int, float)), f"Feature {feature} is not numeric: {type(value)}"


def test_manual_prediction_anomaly_score_calculation(client, normal_request):
    """Test that anomaly score equals 1 - P(Trusted)."""
    response = client.post("/api/c4/predict-manual", json=normal_request.model_dump())

    if response.status_code == 200:
        data = response.json()
        debug_info = data.get("debug_info", {})

        # Get anomaly score and p_trusted
        anomaly_score = debug_info.get("anomaly_score")
        p_trusted = debug_info.get("p_trusted")

        if anomaly_score != "N/A" and p_trusted != "N/A":
            # Verify anomaly_score = 1 - p_trusted
            calculated_anomaly = 1.0 - p_trusted
            assert abs(anomaly_score - calculated_anomaly) < 0.001, \
                f"Anomaly score {anomaly_score} != 1 - P(Trusted) {calculated_anomaly}"


def test_manual_prediction_threshold_consistency(client, normal_request):
    """Test that the 0.70 threshold is applied consistently for ml_decision."""
    response = client.post("/api/c4/predict-manual", json=normal_request.model_dump())

    if response.status_code == 200:
        data = response.json()
        debug_info = data.get("debug_info", {})

        anomaly_score = debug_info.get("anomaly_score")
        ml_decision = debug_info.get("ml_decision")

        if anomaly_score != "N/A" and ml_decision != "N/A":
            # Verify threshold logic
            if anomaly_score >= 0.70:
                assert ml_decision == "SUSPICIOUS", \
                    f"Anomaly score {anomaly_score} >= 0.70 but ml_decision is {ml_decision}"
            else:
                assert ml_decision == "BEHAVIOURAL_NORMAL", \
                    f"Anomaly score {anomaly_score} < 0.70 but ml_decision is {ml_decision}"


def test_manual_prediction_freshness_encoding(client):
    """Test that freshness status is encoded correctly."""
    freshness_cases = [
        ("fresh", 0),
        ("delayed", 1),
        ("stale", 2),
    ]

    for status, expected_encoded in freshness_cases:
        request = ManualPredictionRequest(
            tx_interval_s=300.0,
            rssi_dbm=-75.0,
            snr_db=10.0,
            retry_count=0,
            battery_pct=85.0,
            battery_voltage_v=3.7,
            current_ma=15.0,
            reboot_count_24h=0,
            sensor_fault_flag=False,
            freshness_status=status,
        )

        response = client.post("/api/c4/predict-manual", json=request.model_dump())

        if response.status_code == 200:
            data = response.json()
            features = data.get("features", {})
            encoded = features.get("freshness_status_encoded")

            if encoded is not None:
                assert encoded == expected_encoded, \
                    f"Freshness '{status}' encoded as {encoded}, expected {expected_encoded}"


def test_manual_prediction_sensor_fault_encoding(client):
    """Test that sensor fault flag is encoded correctly (0 or 1)."""
    for flag in [False, True]:
        request = ManualPredictionRequest(
            tx_interval_s=300.0,
            rssi_dbm=-75.0,
            snr_db=10.0,
            retry_count=0,
            battery_pct=85.0,
            battery_voltage_v=3.7,
            current_ma=15.0,
            reboot_count_24h=0,
            sensor_fault_flag=flag,
            freshness_status="fresh",
        )

        response = client.post("/api/c4/predict-manual", json=request.model_dump())

        if response.status_code == 200:
            data = response.json()
            features = data.get("features", {})
            encoded = features.get("sensor_fault_flag")

            if encoded is not None:
                expected = 1 if flag else 0
                assert encoded == expected, \
                    f"Sensor fault {flag} encoded as {encoded}, expected {expected}"


@pytest.mark.parametrize("unhealthy", [False, True])
def test_manual_prediction_matches_artifact_and_health(client, normal_request, unhealthy):
    from apps.c4_frontend.ml_explorer import C4ModelExplorer
    from components.c4_trust.runtime_features import C4_MODEL_FEATURE_SCHEMA

    payload = normal_request.model_dump()
    if unhealthy:
        payload.update(tx_interval_s=0, battery_pct=0, battery_voltage_v=0,
                       sensor_fault_flag=True, freshness_status="stale")
    response = client.post("/api/c4/predict-manual", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    features = data["features"]
    assert list(features) == list(C4_MODEL_FEATURE_SCHEMA)
    expected = [payload["tx_interval_s"], 5, 2 if unhealthy else 0, -75, 0,
                10, 0, 256, payload["battery_pct"], payload["battery_voltage_v"],
                15, 0, int(unhealthy), 0, 0, 0, 0, 0]
    assert list(features.values()) == expected
    model = C4ModelExplorer.from_catalog("random_forest_corrected").model
    frame = pd.DataFrame([features], columns=C4_MODEL_FEATURE_SCHEMA)
    values = model.scaler.transform(frame) if model.scaler is not None else frame.values
    estimator = model.model
    classes = model.label_encoder.inverse_transform(estimator.classes_)
    probabilities = estimator.predict_proba(values)[0]
    label = model.label_encoder.inverse_transform(estimator.predict(values))[0]
    trusted_column = list(classes).index("Trusted")
    assert data["predicted_label"] == label == data["raw_prediction"]
    assert data["behavioural_score"] == 1.0 - probabilities[trusted_column]
    for column, name in enumerate(classes):
        assert data["scored_results"][f"p_{name.lower()}"] == probabilities[column]
    assert data["scored_results"]["predicted_label"] == label
    assert data["debug_info"]["anomaly_score"] == data["behavioural_score"]
    assert data["message"] == f"ML model prediction: {label} (anomaly score: {data['behavioural_score']:.4f})"
    assert len(data["input_health_warnings"]) == (5 if unhealthy else 0)
    assert len(data["feature_assumptions"]) == 4


def test_explorer_uses_one_probability_request(monkeypatch):
    from apps.c4_frontend.ml_explorer import C4ModelExplorer
    from components.c4_trust.runtime_features import C4_MODEL_FEATURE_SCHEMA

    explorer = C4ModelExplorer.from_catalog("random_forest_corrected")
    calls = []
    original = explorer.model.predict_proba
    def probability_spy(frame):
        calls.append(frame.copy())
        return original(frame)
    monkeypatch.setattr(explorer.model, "predict_proba", probability_spy)
    frame = pd.DataFrame([[0.] * 18], columns=C4_MODEL_FEATURE_SCHEMA, index=[17])
    scored = explorer.score_features(frame)
    assert len(calls) == 1
    pd.testing.assert_frame_equal(calls[0], frame)
    assert scored.index.tolist() == [17]
    assert scored.loc[17, "anomaly_score"] == 1 - scored.loc[17, "p_trusted"]
