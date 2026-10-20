"""Test the C1 inference service."""

import pytest
import pandas as pd
from pathlib import Path
from components.c1_credibility.inference.predict import C1CredibilityService


@pytest.fixture
def service():
    """Load the C1 inference service."""
    return C1CredibilityService()


def test_service_loads_model(service):
    """Test that the model loads successfully."""
    assert service is not None
    assert len(service.feature_names) == 18


def test_predict_returns_valid_label(service):
    """Test that predict returns a valid credibility label."""
    features = {
        "dt_s": 300.0,
        "value": 45.5,
        "delta_prev_pct_per_min": 0.1,
        "baseline_mean": 45.0,
        "baseline_std": 0.5,
        "value_minus_baseline": 0.5,
        "stuck_run_len": 1,
        "rain_15m_mm": 0.0,
        "rain_1h_mm": 0.0,
        "rain_3h_mm": 0.0,
        "steps_since_rain": 50,
        "n_neighbours_fresh": 3,
        "neighbour_consensus_change": 0.1,
        "target_minus_consensus": 0.0,
        "neighbour_change_spread": 0.05,
        "neighbour_rise_agree_frac": 0.0,
        "device_voltage": 3.85,
        "history_obs": 12,
    }
    
    result = service.predict(features)
    
    assert "credibility_label" in result
    assert result["credibility_label"] in ["CLEAN", "ANOMALY", "VALID_EVENT"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["class_probabilities"]) == 3


def test_predict_clean_observation(service):
    """Test that a normal observation is classified as CLEAN."""
    features = {
        "dt_s": 300.0,
        "value": 45.5,
        "delta_prev_pct_per_min": 0.1,
        "baseline_mean": 45.0,
        "baseline_std": 0.5,
        "value_minus_baseline": 0.5,
        "stuck_run_len": 1,
        "rain_15m_mm": 0.0,
        "rain_1h_mm": 0.0,
        "rain_3h_mm": 0.0,
        "steps_since_rain": 50,
        "n_neighbours_fresh": 3,
        "neighbour_consensus_change": 0.1,
        "target_minus_consensus": 0.0,
        "neighbour_change_spread": 0.05,
        "neighbour_rise_agree_frac": 0.0,
        "device_voltage": 3.85,
        "history_obs": 12,
    }
    
    result = service.predict(features)
    assert result["credibility_label"] == "CLEAN"


def test_predict_anomaly_observation(service):
    """Test that an extreme observation is classified as ANOMALY."""
    features = {
        "dt_s": 300.0,
        "value": 105.0,  # Extreme value
        "delta_prev_pct_per_min": 0.1,
        "baseline_mean": 45.0,
        "baseline_std": 0.5,
        "value_minus_baseline": 60.0,  # Way above baseline
        "stuck_run_len": 1,
        "rain_15m_mm": 0.0,
        "rain_1h_mm": 0.0,
        "rain_3h_mm": 0.0,
        "steps_since_rain": 50,
        "n_neighbours_fresh": 3,
        "neighbour_consensus_change": 0.1,
        "target_minus_consensus": 60.0,  # Way above neighbours
        "neighbour_change_spread": 0.05,
        "neighbour_rise_agree_frac": 0.0,
        "device_voltage": 3.85,
        "history_obs": 12,
    }
    
    result = service.predict(features)
    assert result["credibility_label"] == "ANOMALY"


def test_predict_batch(service):
    """Test batch prediction."""
    df = pd.DataFrame([
        {
            "dt_s": 300.0, "value": 45.5, "delta_prev_pct_per_min": 0.1,
            "baseline_mean": 45.0, "baseline_std": 0.5, "value_minus_baseline": 0.5,
            "stuck_run_len": 1, "rain_15m_mm": 0.0, "rain_1h_mm": 0.0, "rain_3h_mm": 0.0,
            "steps_since_rain": 50, "n_neighbours_fresh": 3, "neighbour_consensus_change": 0.1,
            "target_minus_consensus": 0.0, "neighbour_change_spread": 0.05,
            "neighbour_rise_agree_frac": 0.0, "device_voltage": 3.85, "history_obs": 12,
        },
        {
            "dt_s": 300.0, "value": 105.0, "delta_prev_pct_per_min": 0.1,
            "baseline_mean": 45.0, "baseline_std": 0.5, "value_minus_baseline": 60.0,
            "stuck_run_len": 1, "rain_15m_mm": 0.0, "rain_1h_mm": 0.0, "rain_3h_mm": 0.0,
            "steps_since_rain": 50, "n_neighbours_fresh": 3, "neighbour_consensus_change": 0.1,
            "target_minus_consensus": 60.0, "neighbour_change_spread": 0.05,
            "neighbour_rise_agree_frac": 0.0, "device_voltage": 3.85, "history_obs": 12,
        },
    ])
    
    result = service.predict_batch(df)
    
    assert len(result) == 2
    assert "credibility_label" in result.columns
    assert "confidence" in result.columns
    assert "proba_CLEAN" in result.columns
    assert "proba_ANOMALY" in result.columns
    assert "proba_VALID_EVENT" in result.columns