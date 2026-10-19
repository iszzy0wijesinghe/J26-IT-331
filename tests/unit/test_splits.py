import copy
import sys
from pathlib import Path

import pandas as pd
import pytest

DATASETS_DIR = Path(__file__).resolve().parents[2] / "components" / "c1_credibility" / "datasets"
sys.path.insert(0, str(DATASETS_DIR))

import schemas  # noqa: E402
import splits  # noqa: E402

TYPES = ["clean_baseline", "fault_spike", "coherent_environmental_event"]
LABELS = {"clean_baseline": "CLEAN", "fault_spike": "ANOMALY", "coherent_environmental_event": "VALID_EVENT"}

CFG = {
    "split": {
        "strategy": "scenario_grouped",
        "group_by": "scenario_id",
        "random_seed": 42,
        "stratify_by": "scenario_type",
        "fractions": {
            "train": {"value": 0.70}, "val": {"value": 0.15}, "test": {"value": 0.15},
        },
        "temporal_holdout": {"enabled": False},
        "device_holdout": {"enabled": False},
    }
}


def make_df(n_scen=60, n_devices=4):
    rows = []
    base = pd.Timestamp("2026-01-01", tz="UTC")
    for i in range(n_scen):
        stype = TYPES[i % 3]
        if stype == "coherent_environmental_event":
            devs = [i % n_devices, (i + 1) % n_devices]      # events span two devices
        else:
            devs = [i % n_devices]
        for k in range(6):
            rows.append({
                "scenario_id": f"S{i:03d}", "scenario_type": stype, "credibility_label": LABELS[stype],
                "device_id": f"d{devs[k % len(devs)]}", "observed_at": base + pd.Timedelta(hours=2 * i, minutes=10 * k),
                "train_eligible": True,
            })
    return pd.DataFrame(rows)


def cfg_with(**flags):
    cfg = copy.deepcopy(CFG)
    cfg["split"]["device_holdout"]["enabled"] = flags.get("device", False)
    cfg["split"]["temporal_holdout"]["enabled"] = flags.get("temporal", False)
    return cfg


def test_scenario_never_split():
    for flags in ({}, {"device": True}, {"temporal": True}, {"device": True, "temporal": True}):
        out, _ = splits.assign_splits(make_df(), cfg_with(**flags))
        assert (out.groupby("scenario_id")["split"].nunique() == 1).all()


def test_fractions_close_to_config_without_holdouts():
    out, skips = splits.assign_splits(make_df(), cfg_with())
    per = out.drop_duplicates("scenario_id")["split"].value_counts()
    assert abs(per["train"] - 42) <= 2 and abs(per["val"] - 9) <= 2 and abs(per["test"] - 9) <= 2
    assert skips == {}


def test_every_row_gets_a_valid_split():
    out, _ = splits.assign_splits(make_df(), cfg_with(device=True, temporal=True))
    assert set(out["split"].unique()) <= {"train", "val", "test"}
    assert out["split"].notna().all()


def test_device_holdout_all_rows_in_test():
    out, skips = splits.assign_splits(make_df(), cfg_with(device=True))
    dev = out.attrs["split_info"]["held_out_device"]
    assert dev is not None and "device" not in skips
    assert (out.loc[out["device_id"] == dev, "split"] == "test").all()
    assert (out.loc[out["split_device"] == "test", "device_id"] == dev).all()


def test_temporal_holdout_has_no_future_in_train():
    out, skips = splits.assign_splits(make_df(), cfg_with(temporal=True))
    assert "temporal" not in skips
    cutoff = pd.Timestamp(out.attrs["split_info"]["temporal_cutoff"])
    train_val = out[out["split"].isin(["train", "val"])]
    assert train_val["observed_at"].max() < cutoff
    assert (out.loc[out["split_temporal"] == "test", "split"] == "test").all()


def test_same_seed_same_result_other_seed_differs():
    a, _ = splits.assign_splits(make_df(), cfg_with())
    b, _ = splits.assign_splits(make_df(), cfg_with())
    pd.testing.assert_series_equal(a["split"], b["split"])
    other = copy.deepcopy(CFG); other["split"]["random_seed"] = 7
    c, _ = splits.assign_splits(make_df(), other)
    assert not a["split"].equals(c["split"])


def test_input_not_modified():
    df = make_df(); before = df.copy()
    splits.assign_splits(df, cfg_with(device=True, temporal=True))
    pd.testing.assert_frame_equal(df, before)


def test_device_holdout_skipped_with_too_few_devices():
    out, skips = splits.assign_splits(make_df(n_devices=2), cfg_with(device=True))
    assert "at least" in skips["device"] and out.attrs["split_info"]["held_out_device"] is None


def test_device_holdout_skipped_when_no_device_has_two_classes():
    df = make_df(n_devices=3)
    df["device_id"] = df["scenario_type"].map({"clean_baseline": "a", "fault_spike": "b", "coherent_environmental_event": "c"})
    _, skips = splits.assign_splits(df, cfg_with(device=True))
    assert skips["device"] == "no device has more than one class"


def test_temporal_holdout_skipped_when_later_period_misses_a_class():
    df = make_df()
    late = df["observed_at"] > df["observed_at"].quantile(0.7)
    df.loc[late & (df["credibility_label"] == "VALID_EVENT"), ["credibility_label", "scenario_type"]] = ["CLEAN", "clean_baseline"]
    _, skips = splits.assign_splits(df, cfg_with(temporal=True))
    assert "VALID_EVENT" in skips["temporal"]


def test_temporal_holdout_skipped_without_timestamps():
    df = make_df(); df["observed_at"] = pd.NaT
    _, skips = splits.assign_splits(df, cfg_with(temporal=True))
    assert "observed_at" in skips["temporal"]


def test_class_gap_is_reported_not_raised():
    df = make_df(n_scen=6)             # too small, some split will miss a class
    out, skips = splits.assign_splits(df, cfg_with())
    assert any(k.startswith("classes:") for k in skips)


def test_ineligible_rows_do_not_count_for_class_coverage():
    df = make_df()
    df.loc[df["credibility_label"] == "ANOMALY", "train_eligible"] = False
    _, skips = splits.assign_splits(df, cfg_with())
    assert all("ANOMALY" in skips[f"classes:{s}"] for s in ("train", "val", "test"))


def test_bad_config_raises():
    bad = copy.deepcopy(CFG); bad["split"]["fractions"]["test"] = {"value": 0.5}
    with pytest.raises(splits.SplitError):
        splits.assign_splits(make_df(), bad)
    bad2 = copy.deepcopy(CFG); bad2["split"]["strategy"] = "random"
    with pytest.raises(splits.SplitError):
        splits.assign_splits(make_df(), bad2)
    with pytest.raises(splits.SplitError):
        splits.assign_splits(make_df().drop(columns=["scenario_id"]), CFG)


def test_manifest_helpers():
    out, skips = splits.assign_splits(make_df(n_devices=2), cfg_with(device=True))
    counts = splits.class_counts(out)
    h = "a" * 64
    m = schemas.DatasetManifest(
        dataset_code="C1_CREDIBILITY", version=1, source_types=["SYNTHETIC"], builder_version="0.1",
        label_schema_version="1.1", split_strategy="scenario_grouped", random_seed=42, generator_seed=7,
        row_count=len(out), class_counts=counts, file_sha256=h, labeling_config_sha256=h, features_config_sha256=h,
        holdout_skips=splits.manifest_holdout_skips(skips),
    )
    assert "device" in m.holdout_skips