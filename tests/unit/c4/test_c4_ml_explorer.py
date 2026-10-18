from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from apps.c4_frontend.ml_explorer import (
    C4ModelExplorer,
    available_catalog_entries,
    default_catalog_key,
    feature_importance_table,
    features_from_split,
)
from components.c4_trust.models import ModelSchemaError, ModelType, TrainedModel
from components.c4_trust.runtime_features import C4_MODEL_FEATURE_SCHEMA


def _tiny_trained_model() -> TrainedModel:
    feature_names = list(C4_MODEL_FEATURE_SCHEMA)
    rng = np.random.default_rng(7)
    x_train = pd.DataFrame(
        rng.normal(size=(60, len(feature_names))),
        columns=feature_names,
    )
    labels = np.array(["Trusted"] * 20 + ["Suspicious"] * 20 + ["Untrusted"] * 20)
    encoder = LabelEncoder()
    encoded = encoder.fit_transform(labels)
    forest = RandomForestClassifier(n_estimators=8, random_state=7)
    forest.fit(x_train, encoded)
    return TrainedModel(
        model=forest,
        scaler=None,
        label_encoder=encoder,
        model_type=ModelType.RANDOM_FOREST,
        feature_names=feature_names,
        training_metadata={"n_train_samples": 60, "random_state": 7},
    )


def _holdout_frame(path: Path) -> Path:
    feature_names = list(C4_MODEL_FEATURE_SCHEMA)
    rows = []
    for index, label in enumerate(["Trusted", "Suspicious", "Untrusted"] * 4):
        row = {name: float(index + offset) for offset, name in enumerate(feature_names)}
        row.update(
            {
                "packet_id": f"P{index:03d}",
                "device_id": f"D{index}",
                "scenario": "unit-test",
                "trust_label": label,
            }
        )
        rows.append(row)
    frame = pd.DataFrame(rows)
    output = path / "holdout.csv"
    frame.to_csv(output, index=False)
    return output


def test_features_from_split_requires_complete_schema():
    frame = pd.DataFrame({"tx_interval_s": [1.0], "trust_label": ["Trusted"]})

    with pytest.raises(ModelSchemaError, match="missing required model features"):
        features_from_split(frame, list(C4_MODEL_FEATURE_SCHEMA))


def test_explorer_scores_holdout_and_reports_importance(tmp_path):
    model = _tiny_trained_model()
    artifact = tmp_path / "tiny.joblib"
    model.save(artifact)
    holdout = _holdout_frame(tmp_path)

    explorer = C4ModelExplorer.from_artifact(
        artifact,
        holdout_path=holdout,
        plots_dir=tmp_path,
    )

    profile = explorer.profile()
    assert profile["n_features"] == 18
    assert set(profile["classes"]) == {"Trusted", "Suspicious", "Untrusted"}
    assert explorer.schema_table().shape[0] == 18

    importance = feature_importance_table(explorer.model)
    assert not importance.empty
    assert pytest.approx(importance["importance"].sum(), rel=1e-6) == 1.0

    evaluation = explorer.evaluate_holdout()
    assert evaluation["n_rows"] == 12
    assert "predicted_label" in evaluation["scored"].columns
    assert "anomaly_score" in evaluation["scored"].columns

    sample = explorer.inspector_sample(evaluation, max_rows=6)
    assert len(sample) <= 6
    assert "predicted_label" in sample.columns

    scored = explorer.score_features(evaluation["features"].head(1))
    assert 0.0 <= float(scored.loc[scored.index[0], "anomaly_score"]) <= 1.0


def test_catalog_default_is_corrected_runtime_model():
    assert default_catalog_key() == "random_forest_corrected"

    models_dir = Path("experiments/c4/models")
    if not (models_dir / "random_forest_corrected.joblib").exists():
        pytest.skip("C4 model artifacts are not present")

    available = available_catalog_entries(models_dir)
    keys = {entry.key for entry in available}
    assert "random_forest_corrected" in keys

    explorer = C4ModelExplorer.from_catalog("random_forest_corrected")
    assert explorer.profile()["runtime_default"] is True
    assert explorer.model.feature_names == list(C4_MODEL_FEATURE_SCHEMA)
