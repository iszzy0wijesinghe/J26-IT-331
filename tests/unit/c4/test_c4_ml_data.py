
from datetime import UTC, datetime, timedelta

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import LabelEncoder

from components.c4_trust import (
    C4TelemetryGate,
    C4TrustService,
    DeviceCredential,
)
from components.c4_trust import (
    quarantine as quarantine_module,
)
from components.c4_trust.data_split import ScenarioAwareSplitter, create_c4_splits
from components.c4_trust.features import FeatureExtractor
from components.c4_trust.models import (
    C4BehavioralModelRunner,
    ModelSchemaError,
    ModelType,
    TrainedModel,
)
from scripts.ablation_study_c4 import deterministic_only_assessment
from shared.contracts import C4TrustAssessment, TelemetryPacket
from shared.contracts.telemetry import SecurityMetadata, TransportMetadata
from shared.enums import C4RoutingOutcome, C4TrustLabel, SourceOrigin


class _FixedProbabilityModel:
    def __init__(self, probabilities):
        self.probabilities = probabilities

    def predict_proba(self, features):
        return np.asarray(self.probabilities)


def _raw_c4_frame() -> pd.DataFrame:
    row_count = 6
    return pd.DataFrame(
        {
            "tx_interval_s": [10.0, 20.0, 30.0, 10.0, 20.0, 30.0],
            "rx_delay_s": [0.1] * row_count,
            "freshness_status": ["fresh"] * row_count,
            "rssi_dbm": [-60.0, -61.0, -62.0, -63.0, -64.0, -65.0],
            "rssi_deviation_db": [1.0] * row_count,
            "snr_db": [20.0] * row_count,
            "retry_count": [0, 1, 2, 0, 1, 2],
            "packet_size_bytes": [100] * row_count,
            "counter_delta": [1] * row_count,
            "battery_pct": [90.0] * row_count,
            "battery_voltage_v": [3.2] * row_count,
            "current_ma": [10.0] * row_count,
            "reboot_count_24h": [0] * row_count,
            "sensor_fault_flag": [0] * row_count,
            "zone_registered": ["Z1"] * row_count,
            "zone_reported": ["Z1"] * row_count,
            "hub_registered": ["H1"] * row_count,
            "hub_id": ["H1"] * row_count,
            "device_id": [f"device-{index // 3}" for index in range(row_count)],
            "device_timestamp": pd.date_range(
                "2025-01-01",
                periods=row_count,
                freq="min",
            ),
            "scenario": [f"scenario-{index}" for index in range(row_count)],
            "trust_label": [
                "Trusted",
                "Trusted",
                "Trusted",
                "Untrusted",
                "Untrusted",
                "Untrusted",
            ],
            "split": ["train", "train", "val", "train", "test", "test"],
            "packet_id": [f"packet-{index}" for index in range(row_count)],
            "signature_valid": [1, 1, 1, 0, 0, 0],
            "is_malicious": [0, 0, 0, 1, 1, 1],
        }
    )


def _three_class_splits() -> dict[str, pd.DataFrame]:
    labels = ["Trusted", "Suspicious", "Untrusted"]
    return {
        split_name: pd.DataFrame(
            {
                "scenario": ["shared-scenario"] * len(labels),
                "device_id": [f"{split_name}-device"] * len(labels),
                "trust_label": labels,
            }
        )
        for split_name in ("train", "val", "test")
    }


def _historical_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "row_key": ["prior", "tie-a", "tie-b", "later"],
            "device_id": ["device-a"] * 4,
            "device_timestamp": pd.to_datetime(
                [
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T00:01:00Z",
                    "2025-01-01T00:01:00Z",
                    "2025-01-01T00:02:00Z",
                ],
                utc=True,
            ),
            "tx_interval_s": [10.0, 100.0, 1000.0, 20.0],
            "rssi_dbm": [-80.0, -20.0, -100.0, -60.0],
            "retry_count": [1, 3, 7, 2],
        }
    )


def _runtime_packet() -> TelemetryPacket:
    now = datetime.now(UTC)
    return TelemetryPacket(
        schema_version="1.0",
        packet_id="packet-gate-test",
        device_id="device-gate-test",
        zone_id="zone-gate-test",
        boot_id="boot-gate-test",
        sequence_no=1,
        observed_at=now,
        received_at=now,
        source_origin=SourceOrigin.SIMULATED,
        security=SecurityMetadata(credential_id="cred-gate-test"),
        transport=TransportMetadata(gateway_id="hub-gate-test"),
    )


def test_training_features_exclude_labels_metadata_and_security_flags():
    source = _raw_c4_frame()
    original = source.copy(deep=True)

    features, labels = FeatureExtractor().extract_for_training(source)

    forbidden = {
        "trust_label",
        "scenario",
        "split",
        "packet_id",
        "signature_valid",
        "is_malicious",
        "counter_delta",
        "zone_match",
        "hub_match_flag",
        "mode_aware_interval_deviation",
        "expected_interval_s",
    }
    assert forbidden.isdisjoint(features.columns)
    assert set(features.columns).issubset(FeatureExtractor.TRAINING_FEATURE_FIELDS)
    assert list(features.columns) == list(FeatureExtractor.TRAINING_FEATURE_FIELDS)
    assert labels.equals(source["trust_label"])
    pd.testing.assert_frame_equal(source, original)


def test_preparation_output_keeps_timestamps_and_omits_stale_split(tmp_path):
    source_path = tmp_path / "raw_c4.csv"
    output_path = tmp_path / "behavioral_c4.csv"
    _raw_c4_frame().to_csv(source_path, index=False)

    FeatureExtractor().create_behavioral_dataset(
        str(source_path),
        str(output_path),
        add_historical=False,
    )

    prepared = pd.read_csv(output_path)
    assert "device_timestamp" in prepared.columns
    assert "split" not in prepared.columns
    assert prepared["device_id"].notna().all()


def test_historical_features_only_use_prior_packets():
    features, _ = FeatureExtractor().extract_for_training(_raw_c4_frame())

    assert features.loc[0, "rolling_interval_mean"] == 0
    assert features.loc[1, "rolling_interval_mean"] == 10
    assert features.loc[2, "rolling_interval_mean"] == 15
    assert features.loc[2, "rolling_interval_std"] == pytest.approx(7.0710678)
    assert features.loc[2, "rolling_rssi_mean"] == pytest.approx(-60.5)
    assert features.loc[2, "rolling_rssi_std"] == pytest.approx(0.7071068)
    assert features.loc[2, "rolling_retry_mean"] == pytest.approx(0.5)


def test_equal_timestamp_rows_do_not_influence_one_anothers_history():
    result = FeatureExtractor().add_historical_features(_historical_frame())
    tied_rows = result.set_index("row_key").loc[["tie-a", "tie-b"]]

    assert tied_rows["rolling_interval_mean"].tolist() == [10.0, 10.0]
    assert tied_rows["rolling_rssi_mean"].tolist() == [-80.0, -80.0]
    assert tied_rows["rolling_retry_mean"].tolist() == [1.0, 1.0]


def test_reordering_equal_timestamp_rows_does_not_change_history():
    source = _historical_frame()
    history_columns = [
        "rolling_interval_mean",
        "rolling_interval_std",
        "rolling_rssi_mean",
        "rolling_rssi_std",
        "rolling_retry_mean",
    ]

    original = FeatureExtractor().add_historical_features(source)
    reordered = FeatureExtractor().add_historical_features(
        source.iloc[[0, 2, 1, 3]]
    )

    original_history = original.set_index("row_key")[history_columns].sort_index()
    reordered_history = reordered.set_index("row_key")[history_columns].sort_index()
    pd.testing.assert_frame_equal(original_history, reordered_history)


def test_historical_features_are_isolated_between_devices():
    source = pd.DataFrame(
        {
            "row_key": ["a0", "b0", "a1", "b1"],
            "device_id": ["device-a", "device-b", "device-a", "device-b"],
            "device_timestamp": pd.to_datetime(
                [
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T00:01:00Z",
                    "2025-01-01T00:01:00Z",
                ],
                utc=True,
            ),
            "tx_interval_s": [10.0, 1000.0, 20.0, 2000.0],
            "rssi_dbm": [-80.0, -40.0, -70.0, -30.0],
            "retry_count": [1, 9, 2, 8],
        }
    )

    result = FeatureExtractor().add_historical_features(source).set_index("row_key")

    assert result.loc["a1", "rolling_interval_mean"] == 10.0
    assert result.loc["b1", "rolling_interval_mean"] == 1000.0


def test_equal_timestamp_batch_uses_only_strictly_earlier_timestamps():
    result = (
        FeatureExtractor()
        .add_historical_features(_historical_frame())
        .set_index("row_key")
    )

    assert result.loc["tie-a", "rolling_interval_mean"] == 10.0
    assert result.loc["tie-b", "rolling_interval_mean"] == 10.0
    assert result.loc["later", "rolling_interval_mean"] == 280.0


def test_historical_features_reject_missing_timestamp_column():
    source = _historical_frame().drop(columns="device_timestamp")

    with pytest.raises(ValueError, match="device_timestamp is required"):
        FeatureExtractor().add_historical_features(source)


@pytest.mark.parametrize("bad_timestamp", [None, "not-a-timestamp"])
def test_historical_features_reject_missing_or_invalid_timestamp_values(
    bad_timestamp,
):
    source = _historical_frame()
    source["device_timestamp"] = source["device_timestamp"].astype(object)
    source.loc[0, "device_timestamp"] = bad_timestamp

    with pytest.raises(
        ValueError,
        match="device_timestamp contains missing or invalid",
    ):
        FeatureExtractor().add_historical_features(source)


def test_extract_for_training_does_not_skip_history_without_timestamps():
    source = _raw_c4_frame().drop(columns="device_timestamp")

    with pytest.raises(ValueError, match="device_timestamp is required"):
        FeatureExtractor().extract_for_training(source)


def test_extract_for_training_does_not_skip_history_without_device_id():
    source = _raw_c4_frame().drop(columns="device_id")

    with pytest.raises(ValueError, match="device_id is required"):
        FeatureExtractor().extract_for_training(source)


def test_model_inference_rejects_feature_order_or_schema_mismatch():
    feature_names = list(FeatureExtractor.TRAINING_FEATURE_FIELDS)
    model = TrainedModel(
        model=_FixedProbabilityModel([[0.1, 0.8, 0.1]]),
        scaler=None,
        label_encoder=LabelEncoder().fit(
            ["Trusted", "Suspicious", "Untrusted"]
        ),
        model_type=ModelType.RANDOM_FOREST,
        feature_names=feature_names,
    )
    bad_features = pd.DataFrame([[0.0]], columns=[feature_names[0]])

    with pytest.raises(ModelSchemaError, match="Feature schema mismatch"):
        model.behavioural_anomaly_score(bad_features)


def test_model_runner_scores_one_packet_with_compatible_schema():
    feature_names = list(FeatureExtractor.TRAINING_FEATURE_FIELDS)

    def builder(packet):
        return pd.DataFrame(
            [[0.0] * len(feature_names)],
            columns=feature_names,
        )

    model = TrainedModel(
        model=_FixedProbabilityModel([[0.1, 0.8, 0.1]]),
        scaler=None,
        label_encoder=LabelEncoder().fit(
            ["Trusted", "Suspicious", "Untrusted"]
        ),
        model_type=ModelType.RANDOM_FOREST,
        feature_names=feature_names,
    )
    runner = C4BehavioralModelRunner(model, builder)
    now = datetime.now(UTC)
    packet = TelemetryPacket(
        schema_version="1.0",
        packet_id="packet-model-test",
        device_id="device-model-test",
        zone_id="zone-model-test",
        observed_at=now,
        received_at=now,
        source_origin=SourceOrigin.SIMULATED,
    )

    score = runner(packet)

    assert score == pytest.approx(0.2)


def test_model_runner_load_rejects_incompatible_artifact_schema(tmp_path):
    feature_names = list(FeatureExtractor.TRAINING_FEATURE_FIELDS)
    model = TrainedModel(
        model=_FixedProbabilityModel([[0.1, 0.8, 0.1]]),
        scaler=None,
        label_encoder=LabelEncoder().fit(
            ["Trusted", "Suspicious", "Untrusted"]
        ),
        model_type=ModelType.RANDOM_FOREST,
        feature_names=feature_names[:-1],
    )
    artifact_path = tmp_path / "incompatible.joblib"
    joblib.dump(model, artifact_path)

    def feature_builder(packet):
        return pd.DataFrame(
            [[0.0] * len(feature_names)],
            columns=feature_names,
        )

    with pytest.raises(ModelSchemaError, match="feature schema"):
        C4BehavioralModelRunner.load(
            artifact_path,
            expected_feature_names=feature_names,
            feature_builder=feature_builder,
        )


def test_model_runner_load_failure_is_explicit(tmp_path):
    def feature_builder(packet):
        return pd.DataFrame()

    with pytest.raises(FileNotFoundError):
        C4BehavioralModelRunner.load(
            tmp_path / "missing.joblib",
            expected_feature_names=FeatureExtractor.TRAINING_FEATURE_FIELDS,
            feature_builder=feature_builder,
        )


def test_isolation_forest_is_not_used_as_calibrated_trust_score():
    model = TrainedModel(
        model=_FixedProbabilityModel([[0.1, 0.8, 0.1]]),
        scaler=None,
        label_encoder=LabelEncoder().fit(
            ["Trusted", "Suspicious", "Untrusted"]
        ),
        model_type=ModelType.ISOLATION_FOREST,
        feature_names=list(FeatureExtractor.TRAINING_FEATURE_FIELDS),
    )

    def builder(packet):
        return pd.DataFrame()

    with pytest.raises(ModelSchemaError, match="Isolation Forest"):
        C4BehavioralModelRunner(model, builder)


def test_saving_model_does_not_overwrite_existing_artifact(tmp_path):
    path = tmp_path / "existing.joblib"
    existing_contents = b"existing model artifact"
    path.write_bytes(existing_contents)
    model = TrainedModel(
        model=_FixedProbabilityModel([[0.1, 0.8, 0.1]]),
        scaler=None,
        label_encoder=LabelEncoder().fit(
            ["Trusted", "Suspicious", "Untrusted"]
        ),
        model_type=ModelType.RANDOM_FOREST,
        feature_names=list(FeatureExtractor.TRAINING_FEATURE_FIELDS),
    )

    with pytest.raises(FileExistsError):
        model.save(path)

    assert path.read_bytes() == existing_contents


def test_scenario_split_keeps_groups_disjoint_and_covers_all_rows():
    source = _raw_c4_frame()
    original = source.copy(deep=True)
    splitter = ScenarioAwareSplitter(random_seed=7)

    splits = splitter.split_by_scenario(source)
    splitter.validate_splits(splits)

    assert sum(len(frame) for frame in splits.values()) == len(source)
    assert all(not frame.empty for frame in splits.values())
    pd.testing.assert_frame_equal(source, original)


def test_scenario_split_rejects_too_few_independent_groups():
    source = _raw_c4_frame()
    source["scenario"] = "one-scenario"

    with pytest.raises(ValueError, match="At least three independent groups"):
        ScenarioAwareSplitter().split_by_scenario(source)


def test_persisted_row_splits_with_scenario_overlap_are_rejected():
    source = _raw_c4_frame()
    splits = {
        "train": source.iloc[:2],
        "val": source.iloc[1:4],
        "test": source.iloc[4:],
    }

    with pytest.raises(ValueError, match="Scenario leakage"):
        ScenarioAwareSplitter.validate_splits(splits)


def test_scenario_validation_remains_the_default():
    splits = _three_class_splits()
    for split_name, split_df in splits.items():
        split_df["scenario"] = split_name

    ScenarioAwareSplitter.validate_splits(splits)


def test_device_validation_allows_scenario_overlap():
    splits = _three_class_splits()

    ScenarioAwareSplitter.validate_splits(splits, device_id_col="device_id")


def test_device_validation_rejects_device_leakage():
    splits = _three_class_splits()
    splits["val"]["device_id"] = "train-device"

    with pytest.raises(ValueError, match="Device leakage"):
        ScenarioAwareSplitter.validate_splits(splits, device_id_col="device_id")


def test_device_validation_rejects_missing_inferred_label():
    splits = _three_class_splits()
    splits["val"] = splits["val"].iloc[:2]

    with pytest.raises(ValueError, match="missing expected trust_label classes"):
        ScenarioAwareSplitter.validate_splits(splits, device_id_col="device_id")


def test_device_validation_rejects_missing_explicit_label():
    splits = _three_class_splits()
    for split_df in splits.values():
        split_df.loc[
            split_df["trust_label"] == "Suspicious",
            "trust_label",
        ] = "Trusted"

    with pytest.raises(ValueError, match="missing expected trust_label classes"):
        ScenarioAwareSplitter.validate_splits(
            splits,
            device_id_col="device_id",
            expected_labels={"Trusted", "Suspicious", "Untrusted"},
        )


def test_device_validation_rejects_partial_label_columns():
    splits = _three_class_splits()
    splits["val"] = splits["val"].drop(columns="trust_label")

    with pytest.raises(ValueError, match="must be present in all splits or none"):
        ScenarioAwareSplitter.validate_splits(splits, device_id_col="device_id")


def test_device_validation_skips_label_checks_when_labels_are_absent():
    splits = _three_class_splits()
    splits = {
        name: frame.drop(columns="trust_label")
        for name, frame in splits.items()
    }

    ScenarioAwareSplitter.validate_splits(splits, device_id_col="device_id")


def test_split_generation_uses_device_holdout_and_updates_split_metadata(
    tmp_path,
):
    labels = ["Trusted", "Suspicious", "Untrusted"]
    rows = [
        {
            "device_id": f"device-{device_index}",
            "scenario": f"scenario-{packet_index % 2}",
            "trust_label": labels[device_index % len(labels)],
            "split": "legacy-row-split",
        }
        for device_index in range(9)
        for packet_index in range(2)
    ]
    input_path = tmp_path / "behavioral.csv"
    output_dir = tmp_path / "splits"
    pd.DataFrame(rows).to_csv(input_path, index=False)

    create_c4_splits(str(input_path), str(output_dir))

    splits = {
        name: pd.read_csv(output_dir / f"C4_{name}.csv")
        for name in ("train", "val", "test")
    }
    ScenarioAwareSplitter.validate_splits(splits, device_id_col="device_id")
    for split_name, split_df in splits.items():
        assert set(split_df["split"]) == {split_name}
        assert set(split_df["trust_label"]) == set(labels)


def test_scenario_and_device_split_keeps_both_groups_disjoint_without_mutation():
    source = pd.DataFrame(
        {
            "scenario": ["A", "A", "B", "B", "C", "C"],
            "device_id": ["A1", "A2", "B1", "B2", "C1", "C2"],
        }
    )
    original = source.copy(deep=True)

    splits = ScenarioAwareSplitter(
        random_seed=3
    ).split_by_scenario_and_device(source)

    for first, second in (
        ("train", "val"),
        ("train", "test"),
        ("val", "test"),
    ):
        assert set(splits[first]["scenario"]).isdisjoint(
            splits[second]["scenario"]
        )
        assert set(splits[first]["device_id"]).isdisjoint(
            splits[second]["device_id"]
        )
    pd.testing.assert_frame_equal(source, original)


def test_deterministic_ablation_uses_gate_fields_not_the_target_label():
    from scripts.ablation_study_c4 import DETERMINISTIC_SECURITY_FIELDS

    source = pd.DataFrame(
        {
            **{field: [1, 1] for field in DETERMINISTIC_SECURITY_FIELDS},
            "signature_valid": [1, 0],
            "trust_label": ["Untrusted", "Trusted"],
        }
    )

    result = deterministic_only_assessment(source)

    assert result["predictions"] == ["Trusted", "Untrusted"]


def test_default_quarantine_records_are_saved_under_project_c4_folder(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        quarantine_module,
        "__file__",
        str(tmp_path / "components" / "c4_trust" / "quarantine.py"),
    )
    manager = quarantine_module.QuarantineManager()

    record = manager.quarantine(
        packet_id="packet-1",
        device_id="device-1",
        trust_label=C4TrustLabel.SUSPICIOUS,
        routing_outcome=C4RoutingOutcome.QUARANTINE,
        reason_codes=["BEHAVIOURAL_ANOMALY"],
        quarantine_reason=quarantine_module.QuarantineReason.BEHAVIOURAL_ANOMALY,
    )

    expected_path = (
        tmp_path / "quarantine" / "c4" / f"{record.quarantine_id}.json"
    )
    assert expected_path.is_file()


def test_quarantine_assessment_serializes_and_reloads(tmp_path):
    now = datetime.now(UTC)
    manager = quarantine_module.QuarantineManager(tmp_path)
    assessment = C4TrustAssessment(
        schema_version="1.0",
        assessment_id="C4A_QUARANTINE_001",
        packet_id="packet-persisted",
        device_id="device-persisted",
        trust_label=C4TrustLabel.SUSPICIOUS,
        trust_score=0.4,
        mandatory_security_pass=True,
        reason_codes=["BEHAVIOURAL_ANOMALY"],
        routing_outcome=C4RoutingOutcome.QUARANTINE,
        generated_at=now,
    )
    record = manager.quarantine(
        packet_id=assessment.packet_id,
        device_id=assessment.device_id,
        trust_label=assessment.trust_label,
        routing_outcome=C4RoutingOutcome.QUARANTINE,
        reason_codes=assessment.reason_codes,
        quarantine_reason=quarantine_module.QuarantineReason.BEHAVIOURAL_ANOMALY,
        packet_data={"received_at": now},
        assessment=assessment,
    )

    reloaded = quarantine_module.QuarantineManager(tmp_path)
    loaded_record = reloaded.get(record.quarantine_id)

    assert loaded_record is not None
    assert loaded_record.assessment == assessment
    assert pd.Timestamp(loaded_record.packet_data["received_at"]) == pd.Timestamp(
        now
    )
    assert reloaded.load_errors == {}


def test_corrupt_quarantine_file_is_reported_and_preserved(tmp_path):
    corrupt_path = tmp_path / "Q_corrupt.json"
    corrupt_contents = "{not-json"
    corrupt_path.write_text(corrupt_contents, encoding="utf-8")

    manager = quarantine_module.QuarantineManager(tmp_path)

    assert manager.count() == 0
    assert manager.load_errors == {corrupt_path.name: "JSONDecodeError"}
    assert corrupt_path.read_text(encoding="utf-8") == corrupt_contents


def test_untrusted_quarantine_requires_fresh_trusted_revalidation(tmp_path):
    manager = quarantine_module.QuarantineManager(
        tmp_path,
        release_authorizer=lambda reviewer_id: reviewer_id == "security-operator",
    )
    original_assessment = C4TrustAssessment(
        schema_version="1.0",
        assessment_id="C4A_ORIGINAL_001",
        packet_id="packet-review",
        device_id="device-review",
        trust_label=C4TrustLabel.UNTRUSTED,
        trust_score=0.0,
        mandatory_security_pass=False,
        reason_codes=["INTEGRITY_INVALID"],
        routing_outcome=C4RoutingOutcome.REJECT,
        generated_at=datetime.now(UTC),
    )
    record = manager.quarantine(
        packet_id=original_assessment.packet_id,
        device_id=original_assessment.device_id,
        trust_label=original_assessment.trust_label,
        routing_outcome=C4RoutingOutcome.REJECT,
        reason_codes=original_assessment.reason_codes,
        quarantine_reason=quarantine_module.QuarantineReason.SECURITY_FAILURE,
        assessment=original_assessment,
    )

    with pytest.raises(ValueError, match="fresh TRUSTED assessment"):
        manager.release(
            record.quarantine_id,
            "Manual review only",
            reviewer_id="security-operator",
        )

    revalidation = C4TrustAssessment(
        schema_version="1.0",
        assessment_id="C4A_REVALIDATED_001",
        packet_id=record.packet_id,
        device_id=record.device_id,
        trust_label=C4TrustLabel.TRUSTED,
        trust_score=1.0,
        mandatory_security_pass=True,
        reason_codes=["REVALIDATED"],
        routing_outcome=C4RoutingOutcome.ACCEPT,
        generated_at=record.quarantined_at + timedelta(seconds=1),
    )
    released = manager.release(
        record.quarantine_id,
        "Fresh security verification passed",
        review_assessment=revalidation,
        reviewer_id="security-operator",
    )

    assert released.trust_label is C4TrustLabel.TRUSTED
    assert released.assessment == original_assessment
    assert released.review_assessment == revalidation
    assert released.reviewed_by == "security-operator"


def test_quarantine_release_is_denied_without_authorizer(tmp_path):
    manager = quarantine_module.QuarantineManager(tmp_path)
    record = manager.quarantine(
        packet_id="packet-denied-release",
        device_id="device-denied-release",
        trust_label=C4TrustLabel.SUSPICIOUS,
        routing_outcome=C4RoutingOutcome.QUARANTINE,
        reason_codes=["BEHAVIOURAL_ANOMALY"],
        quarantine_reason=quarantine_module.QuarantineReason.BEHAVIOURAL_ANOMALY,
    )

    with pytest.raises(ValueError, match="authorized reviewer"):
        manager.release(record.quarantine_id, "No authorization configured")


def test_c4_gate_exposes_only_trusted_packet_to_c1(tmp_path):
    packet = _runtime_packet()
    credential = DeviceCredential("cred-gate-test", b"gate-secret")
    service = C4TrustService(
        {packet.device_id: credential},
        attestation_verifier=lambda incoming, device: True,
        provenance_verifier=lambda incoming, device: True,
        behavioural_scorer=lambda incoming: 0.1,
    )
    signature = service.sign_packet(packet, credential.secret)
    gate = C4TelemetryGate(
        service,
        quarantine_module.QuarantineManager(tmp_path),
    )

    result = gate.process(packet, signature)

    assert result.eligible_for_c1
    assert result.eligible_packet is packet
    assert result.quarantine_record is None
    assert result.assessment.trust_label is C4TrustLabel.TRUSTED


def test_c4_gate_sends_unknown_and_untrusted_packets_to_quarantine(tmp_path):
    packet = _runtime_packet()
    credential = DeviceCredential("cred-gate-test", b"gate-secret")
    service = C4TrustService(
        {packet.device_id: credential},
        allow_deterministic_only=True,
    )
    quarantine = quarantine_module.QuarantineManager(tmp_path)
    gate = C4TelemetryGate(service, quarantine)

    unknown_result = gate.process(
        packet,
        service.sign_packet(packet, credential.secret),
    )
    untrusted_result = gate.process(packet, "invalid-signature")

    assert unknown_result.assessment.trust_label is C4TrustLabel.UNKNOWN
    assert (
        unknown_result.assessment.routing_outcome
        is C4RoutingOutcome.SECURITY_REVIEW
    )
    assert unknown_result.eligible_packet is None
    assert unknown_result.quarantine_record is not None
    assert untrusted_result.assessment.trust_label is C4TrustLabel.UNTRUSTED
    assert untrusted_result.assessment.routing_outcome is C4RoutingOutcome.REJECT
    assert untrusted_result.eligible_packet is None
    assert quarantine.count() == 2