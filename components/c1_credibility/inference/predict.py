"""C1 Credibility Inference Service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

MODEL_PATH = Path("models/c1/c1_xgboost_v1.json")
CLASSES = ["CLEAN", "ANOMALY", "VALID_EVENT"]

# These are NOT features (metadata, leakage, etc.)
DROP_COLS = [
    "record_id", "observation_id", "scenario_id", "zone_id", "device_id",
    "sensor_instance_id", "observed_at", "source_origin", "test_run_id",
    "dataset_version", "credibility_label", "label_source", "event_id",
    "calibration_version", "context_status", "ambiguous", "ambiguity_reason",
    "borderline_extreme", "train_eligible", "split", "split_temporal",
    "split_device", "mode", "rainfall_regime", "scenario_type",
    "value_present", "obs_gap_steps", "recent_read_failures",
]


class C1CredibilityService:
    """Service for C1 credibility predictions."""

    def __init__(self, model_path: Path = MODEL_PATH):
        """Load the trained XGBoost model."""
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        self.model = xgb.XGBClassifier()
        self.model.load_model(model_path)
        self.feature_names = self.model.get_booster().feature_names
        print(f"Loaded C1 model with {len(self.feature_names)} features")

    def predict(self, features: dict[str, float]) -> dict[str, Any]:
        """Predict credibility for a single observation.
        
        Args:
            features: dict of feature_name -> value
        
        Returns:
            dict with label, confidence, and probabilities
        """
        # Build DataFrame with only required features
        row = {name: features.get(name, 0.0) for name in self.feature_names}
        X = pd.DataFrame([row])
        
        # Predict
        proba = self.model.predict_proba(X)[0]
        pred_idx = int(np.argmax(proba))
        
        return {
            "credibility_label": CLASSES[pred_idx],
            "confidence": float(proba[pred_idx]),
            "class_probabilities": {
                CLASSES[i]: float(proba[i]) for i in range(len(CLASSES))
            },
        }

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Predict credibility for a batch of observations."""
        X = df[self.feature_names].copy()
        proba = self.model.predict_proba(X)
        pred_idx = np.argmax(proba, axis=1)
        
        result = df.copy()
        result["credibility_label"] = [CLASSES[i] for i in pred_idx]
        result["confidence"] = [float(proba[i, pred_idx[i]]) for i in range(len(pred_idx))]
        for i, cls in enumerate(CLASSES):
            result[f"proba_{cls}"] = proba[:, i]
        
        return result


def main():
    """Example usage."""
    service = C1CredibilityService()
    
    # Example observation (simulated)
    example_features = {
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
    
    result = service.predict(example_features)
    print("\n=== C1 Prediction ===")
    print(f"Label: {result['credibility_label']}")
    print(f"Confidence: {result['confidence']:.3f}")
    print(f"Probabilities: {result['class_probabilities']}")


if __name__ == "__main__":
    main()