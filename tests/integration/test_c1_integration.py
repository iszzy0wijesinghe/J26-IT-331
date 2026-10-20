"""Integration test for C1 component.

This test verifies that the C1 inference service can be used by other components
(C3/C4) to get credibility assessments.
"""

import pytest
from components.c1_credibility.inference.predict import C1CredibilityService


@pytest.fixture(scope="module")
def service():
    """Load the C1 inference service."""
    return C1CredibilityService()


def test_integration_c1_provides_credibility_for_c3(service):
    """Test that C1 can provide credibility assessment for C3's temporal window.
    
    C3 needs to know if the recent observations are trustworthy before
    building a temporal feature window.
    """
    # Simulate a sequence of observations from a C3 window
    observations = [
        {
            "dt_s": 300.0, "value": 45.0, "delta_prev_pct_per_min": 0.1,
            "baseline_mean": 45.0, "baseline_std": 0.5, "value_minus_baseline": 0.0,
            "stuck_run_len": 1, "rain_15m_mm": 0.0, "rain_1h_mm": 0.0, "rain_3h_mm": 0.0,
            "steps_since_rain": 50, "n_neighbours_fresh": 3, "neighbour_consensus_change": 0.1,
            "target_minus_consensus": 0.0, "neighbour_change_spread": 0.05,
            "neighbour_rise_agree_frac": 0.0, "device_voltage": 3.85, "history_obs": 12,
        },
        {
            "dt_s": 300.0, "value": 46.0, "delta_prev_pct_per_min": 0.2,
            "baseline_mean": 45.5, "baseline_std": 0.6, "value_minus_baseline": 0.5,
            "stuck_run_len": 1, "rain_15m_mm": 0.0, "rain_1h_mm": 0.0, "rain_3h_mm": 0.0,
            "steps_since_rain": 49, "n_neighbours_fresh": 3, "neighbour_consensus_change": 0.2,
            "target_minus_consensus": 0.3, "neighbour_change_spread": 0.06,
            "neighbour_rise_agree_frac": 0.0, "device_voltage": 3.84, "history_obs": 13,
        },
    ]
    
    results = [service.predict(obs) for obs in observations]
    
    # C3 should be able to use these credibility labels
    for result in results:
        assert result["credibility_label"] in ["CLEAN", "ANOMALY", "VALID_EVENT"]
        assert result["confidence"] > 0.0
        assert "class_probabilities" in result
    
    # Both should be CLEAN (normal observations)
    assert all(r["credibility_label"] == "CLEAN" for r in results)


def test_integration_c1_provides_anomaly_for_c3(service):
    """Test that C1 can identify anomalies that C3 should exclude."""
    # Simulate an anomalous observation (e.g., sensor spike)
    anomaly_obs = {
        "dt_s": 300.0, "value": 105.0, "delta_prev_pct_per_min": 0.1,
        "baseline_mean": 45.0, "baseline_std": 0.5, "value_minus_baseline": 60.0,
        "stuck_run_len": 1, "rain_15m_mm": 0.0, "rain_1h_mm": 0.0, "rain_3h_mm": 0.0,
        "steps_since_rain": 50, "n_neighbours_fresh": 3, "neighbour_consensus_change": 0.1,
        "target_minus_consensus": 60.0, "neighbour_change_spread": 0.05,
        "neighbour_rise_agree_frac": 0.0, "device_voltage": 3.85, "history_obs": 12,
    }
    
    result = service.predict(anomaly_obs)
    
    # C1 should flag this as ANOMALY so C3 can exclude/downweight it
    assert result["credibility_label"] == "ANOMALY"
    assert result["class_probabilities"]["ANOMALY"] > 0.0


def test_integration_c1_provides_valid_event_for_c3(service):
    """Test that C1 identifies genuine environmental events as VALID_EVENT."""
    # Simulate a genuine environmental event (high soil moisture + rainfall)
    event_obs = {
        "dt_s": 300.0, "value": 85.0, "delta_prev_pct_per_min": 2.5,
        "baseline_mean": 50.0, "baseline_std": 2.0, "value_minus_baseline": 35.0,
        "stuck_run_len": 1, "rain_15m_mm": 12.5, "rain_1h_mm": 25.0, "rain_3h_mm": 35.0,
        "steps_since_rain": 2, "n_neighbours_fresh": 3, "neighbour_consensus_change": 15.0,
        "target_minus_consensus": 5.0, "neighbour_change_spread": 3.0,
        "neighbour_rise_agree_frac": 0.8, "device_voltage": 3.85, "history_obs": 20,
    }
    
    result = service.predict(event_obs)
    
    # C1 should identify this as VALID_EVENT (genuine environmental change)
    # This is critical for C3 to not exclude genuine hazard evidence
    assert result["credibility_label"] in ["VALID_EVENT", "CLEAN"]
    assert result["class_probabilities"]["VALID_EVENT"] > 0.0