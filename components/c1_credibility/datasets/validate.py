# validate.py - c1 config + dataset checks (GEONEX-5)
# lives in components/c1_credibility/datasets/
#
# loads c1_labeling_v1.yaml and c1_features_v1.yaml, runs the validation_rules
# from each, checks a built dataset, and writes the manifest only if there are
# no errors (that is the "freeze")
#
# exit codes: 0 ok, 1 validation errors, 2 setup / config problem
# most checks are still stubs (NotImplementedError), the report, the param
# walker and the cli flow work already

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import pandas as pd
import yaml

DEFAULT_LABELING_CONFIG = Path("configs/components/c1_labeling_v1.yaml")
DEFAULT_FEATURES_CONFIG = Path("configs/components/c1_features_v1.yaml")
DEFAULT_MANIFEST_DIR = Path("data/manifests")

# empty, tbd, todo, pending..., n/a all count as no justification
BLANK_JUSTIFICATION = re.compile(r"^\s*(|tbd|todo|pending.*|n/?a|\?+)\s*$", re.IGNORECASE)


class Stage(str, Enum):
    DATASET_FREEZE = "dataset_freeze"
    MODEL_FREEZE = "model_freeze"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


# stage is only written in yaml comments for now, so keep the mapping here
# (could be a `stage:` key per section later)
SECTION_STAGE = {"runtime": Stage.MODEL_FREEZE}


# ---- report ----

@dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str      # e.g. CFG_STATUS_PROVISIONAL
    where: str     # file / dotted path / column
    message: str


@dataclass
class ValidationReport:
    # checks only add findings, they never raise, so one run shows everything
    findings: list[Finding] = field(default_factory=list)

    def error(self, code: str, where: str, message: str) -> None:
        self.findings.append(Finding(Severity.ERROR, code, where, message))

    def warn(self, code: str, where: str, message: str) -> None:
        self.findings.append(Finding(Severity.WARNING, code, where, message))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "error_count": len(self.errors),
            "findings": [vars(f) | {"severity": f.severity.value} for f in self.findings],
        }

    def print_summary(self) -> None:
        # errors first, then warnings
        for f in sorted(self.findings, key=lambda f: f.severity is not Severity.ERROR):
            print(f"[{f.severity.value}] {f.code} @ {f.where}: {f.message}")
        print("OK" if self.ok else f"FAILED: {len(self.errors)} error(s)")


@dataclass(frozen=True)
class ConfigBundle:
    labeling: Mapping[str, Any]
    features: Mapping[str, Any]
    labeling_path: Path
    features_path: Path
    labeling_sha256: str     # both hashes go into the manifest
    features_sha256: str


# ---- loading helpers ----

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, Mapping):
        raise ValueError(f"{path} must have a mapping at the top level")
    return data


def load_configs(labeling_path: Path, features_path: Path) -> ConfigBundle:
    # TODO: load both, then check labeling.features_config_ref and
    # features.meta.labeling_config_ref point at the files we were given
    raise NotImplementedError


def iter_param_records(node: Any, path: str = "") -> Iterator[tuple[str, Mapping[str, Any]]]:
    """yields (dotted path, record) for every mapping that has both `value` and `source`"""
    if isinstance(node, Mapping):
        if "value" in node and "source" in node:
            yield path, node
            return
        for key, child in node.items():
            yield from iter_param_records(child, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for i, child in enumerate(node):
            yield from iter_param_records(child, f"{path}[{i}]")


def stage_of(path: str) -> Stage:
    return SECTION_STAGE.get(path.split(".", 1)[0], Stage.DATASET_FREEZE)


def is_blank_justification(text: Any) -> bool:
    return not isinstance(text, str) or bool(BLANK_JUSTIFICATION.match(text))


# ---- config checks (each yaml is checked against its own validation_rules) ----

def check_status(cfg: Mapping[str, Any], name: str, report: ValidationReport) -> None:
    # meta.status == PROVISIONAL is an error
    raise NotImplementedError


def check_param_records(cfg: Mapping[str, Any], name: str, stage: Stage, report: ValidationReport) -> None:
    # walk iter_param_records for sections in this stage and flag:
    #   value null, source PENDING_EVIDENCE, blank/TBD justification,
    #   missing reference when source is in the rule's reference list
    # rule switches come from cfg["validation_rules"]
    raise NotImplementedError


def check_regime_rules(features: Mapping[str, Any], report: ValidationReport) -> None:
    # features yaml only:
    #   bound sources in allowed_sources, none derived from forbidden_derivation_sources
    #   EXTERNAL_RECORDS bounds have `method`, external_record block is filled
    #   LIGHT < MODERATE < HEAVY < EXTREME and 15m < 1h < 6h windows
    #   tuned_on_test_split flags are false
    raise NotImplementedError


def check_generator_independent_of_regimes(
    labeling: Mapping[str, Any], features: Mapping[str, Any], report: ValidationReport
) -> None:
    # no generator param may reference or copy a regime bound, otherwise the
    # regime feature just gives the generator rule back to the model
    raise NotImplementedError


def check_runtime_block(features: Mapping[str, Any], report: ValidationReport) -> None:
    # model_freeze only: model_path, model_version, confidence_threshold filled,
    # threshold not tuned on the test split
    raise NotImplementedError


# ---- dataset checks ----

def check_required_columns(df: pd.DataFrame, report: ValidationReport) -> None:
    # TODO: schemas.missing_columns / unknown_columns / invalid_enum_values
    raise NotImplementedError


def check_forbidden_features(
    feature_columns: Sequence[str], forbidden: Sequence[str], report: ValidationReport
) -> None:
    # compare against the FEATURE columns, not every column. device_id,
    # scenario_id, observed_at, split ... are fine as metadata, they just must
    # never be model inputs
    raise NotImplementedError


def check_device_id_leakage(
    df: pd.DataFrame,
    feature_columns: Sequence[str],
    report: ValidationReport,
    *,
    baseline_margin: float | None,
) -> None:
    # 1. device_id is not a feature
    # 2. every class shows up on more than one device
    # 3. device_id-only baseline must not beat the majority baseline by more than
    #    baseline_margin (comes from the labeling yaml, no number in code)
    raise NotImplementedError


def check_label_matches_scenario_truth(df: pd.DataFrame, labeling: Mapping[str, Any], report: ValidationReport) -> None:
    # label == scenario_to_label[scenario_type] for every row
    # also run schemas.enum_drift_problems(labeling) here
    raise NotImplementedError


def check_ambiguity_policy(df: pd.DataFrame, labeling: Mapping[str, Any], report: ValidationReport) -> None:
    # reasons are all listed in ambiguous.reasons, `exclude` reasons have
    # train_eligible False, `keep` reasons stay eligible
    raise NotImplementedError


def check_split_integrity(df: pd.DataFrame, labeling: Mapping[str, Any], report: ValidationReport) -> None:
    # no scenario_id in more than one split, fractions roughly match the config
    # (per scenario group), holdout conditions met or skip reason recorded,
    # a device is fully in train or fully in holdout
    raise NotImplementedError


def check_classes_per_split(df: pd.DataFrame, labeling: Mapping[str, Any], report: ValidationReport) -> None:
    # all three classes in train, val, test and the temporal holdout
    raise NotImplementedError


def check_source_separation(
    df: pd.DataFrame, labeling: Mapping[str, Any], manifest_flags: Mapping[str, Any], report: ValidationReport
) -> None:
    # SYNTHETIC / PHYSICAL_DEMO / EXTERNAL not mixed unless the manifest flags it,
    # and source types in the data match labeling.meta.source_types
    raise NotImplementedError


def check_as_of_context(df: pd.DataFrame, report: ValidationReport) -> None:
    # context features only use data at or before the row's observed_at
    # (needs the max source timestamp per row from the builder)
    raise NotImplementedError


def check_fit_on_train_only(build_info: Mapping[str, Any], report: ValidationReport) -> None:
    # scalers / imputers / encoders in build_info were fitted on train rows only
    raise NotImplementedError


# ---- manifest ----

def build_manifest(
    df: pd.DataFrame,
    bundle: ConfigBundle,
    *,
    dataset_path: Path,
    dataset_code: str,
    dataset_version: str,
    builder_version: str,
    split_skips: Mapping[str, str],
) -> dict[str, Any]:
    # TODO: everything from the real build, use schemas.DatasetManifest
    # (source_types from the data, class_counts per split, file + config sha256,
    # both seeds, holdout skips)
    raise NotImplementedError


def write_manifest(manifest: Mapping[str, Any], out_dir: Path, report: ValidationReport) -> Path:
    # <out_dir>/<dataset_code>_<version>.json
    if not report.ok:
        raise RuntimeError("not writing a manifest while the report has errors")
    raise NotImplementedError


# ---- flow ----

def run_config_checks(bundle: ConfigBundle, stage: Stage, report: ValidationReport) -> None:
    for name, cfg in (("labeling", bundle.labeling), ("features", bundle.features)):
        check_status(cfg, name, report)
        check_param_records(cfg, name, stage, report)
    check_regime_rules(bundle.features, report)
    check_generator_independent_of_regimes(bundle.labeling, bundle.features, report)
    if stage is Stage.MODEL_FREEZE:
        check_runtime_block(bundle.features, report)


def run_dataset_checks(
    df: pd.DataFrame,
    bundle: ConfigBundle,
    feature_columns: Sequence[str],
    build_info: Mapping[str, Any],
    report: ValidationReport,
) -> None:
    labeling = bundle.labeling
    check_required_columns(df, report)
    check_forbidden_features(feature_columns, labeling["forbidden_features"], report)
    check_device_id_leakage(df, feature_columns, report, baseline_margin=None)   # TODO: read margin from the yaml
    check_label_matches_scenario_truth(df, labeling, report)
    check_ambiguity_policy(df, labeling, report)
    check_split_integrity(df, labeling, report)
    check_classes_per_split(df, labeling, report)
    check_source_separation(df, labeling, build_info.get("manifest_flags", {}), report)
    check_as_of_context(df, report)
    check_fit_on_train_only(build_info, report)


def run_validation(
    bundle: ConfigBundle,
    stage: Stage,
    *,
    df: pd.DataFrame | None = None,
    feature_columns: Sequence[str] = (),
    build_info: Mapping[str, Any] | None = None,
) -> ValidationReport:
    report = ValidationReport()
    run_config_checks(bundle, stage, report)
    if df is not None:   # dataset checks only when a dataset is given
        run_dataset_checks(df, bundle, feature_columns, build_info or {}, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="c1 config + dataset validation")
    p.add_argument("--labeling", type=Path, default=DEFAULT_LABELING_CONFIG)
    p.add_argument("--features", type=Path, default=DEFAULT_FEATURES_CONFIG)
    p.add_argument("--dataset", type=Path, help="built dataset, leave out for config-only checks")
    p.add_argument("--build-info", type=Path, help="json from the dataset builder")
    p.add_argument("--stage", type=Stage, choices=list(Stage), default=Stage.DATASET_FREEZE)
    p.add_argument("--freeze", action="store_true", help="write the manifest if everything passes")
    p.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    p.add_argument("--json-report", type=Path)
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        bundle = load_configs(args.labeling, args.features)
        df = None                            # TODO: read args.dataset
        build_info: Mapping[str, Any] = {}   # TODO: json.load args.build_info
        feature_columns: Sequence[str] = ()  # TODO: schemas.get_feature_columns(bundle.features, forbidden=bundle.labeling["forbidden_features"])
    except (OSError, ValueError, NotImplementedError) as exc:
        print(f"setup problem: {exc}", file=sys.stderr)
        return 2

    report = run_validation(bundle, args.stage, df=df, feature_columns=feature_columns, build_info=build_info)
    report.print_summary()
    if args.json_report:
        args.json_report.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    if args.freeze and report.ok and df is not None:
        pass   # TODO: build_manifest(...) then write_manifest(...)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())