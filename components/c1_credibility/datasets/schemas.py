# schemas.py - enums, column specs, feature list, param record + manifest models
# lives in components/c1_credibility/datasets/
#
# feature columns are an allow-list built from the features yaml, so anything
# not on the list (device_id, scenario_id, observed_at ...) can never reach
# the model. validate.py still checks against forbidden_features on top of this

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any, Iterable, Literal, Mapping, Sequence

import pandas as pd
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

DATASET_SCHEMA_VERSION = "1"   # bump when CANONICAL_COLUMNS changes


class SchemaError(ValueError):
    pass


def _as_str(value: Any) -> str:
    # yaml gives 1, 1.0 or "1.1" for versions, manifest keeps text
    return str(value)


VersionStr = Annotated[str, BeforeValidator(_as_str)]


# ---- enums ----

class Label(str, Enum):
    CLEAN = "CLEAN"
    ANOMALY = "ANOMALY"
    VALID_EVENT = "VALID_EVENT"


class SourceType(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    PHYSICAL_DEMO = "PHYSICAL_DEMO"
    EXTERNAL = "EXTERNAL"


class ParamSource(str, Enum):
    NBRO = "NBRO"
    LITERATURE = "LITERATURE"
    EXTERNAL_RECORDS = "EXTERNAL_RECORDS"
    DEVICE_DATASHEET = "DEVICE_DATASHEET"
    DATA_DRIVEN = "DATA_DRIVEN"
    DESIGN_CHOICE = "DESIGN_CHOICE"
    PENDING_EVIDENCE = "PENDING_EVIDENCE"


class SplitName(str, Enum):
    TRAIN = "train"
    VAL = "val"      # same key as split.fractions.val in the labeling yaml
    TEST = "test"


# keys of labeling.scenario_to_label
class ScenarioType(str, Enum):
    CLEAN_BASELINE = "clean_baseline"
    FAULT_SPIKE = "fault_spike"
    FAULT_STUCK_AT = "fault_stuck_at"
    FAULT_DRIFT = "fault_drift"
    FAULT_BIAS = "fault_bias"
    FAULT_EXCESSIVE_NOISE = "fault_excessive_noise"
    FAULT_QUANTIZATION_ADC = "fault_quantization_adc"
    FAULT_OUT_OF_RANGE = "fault_out_of_range"
    FAULT_DROPOUT = "fault_dropout"
    COHERENT_ENVIRONMENTAL_EVENT = "coherent_environmental_event"

    @property
    def is_fault(self) -> bool:
        return self.value.startswith("fault_")


# keys of labeling.ambiguous.reasons
class AmbiguityReason(str, Enum):
    FAULT_BELOW_DETECTABILITY = "FAULT_BELOW_DETECTABILITY"
    ISOLATED_RESPONSE = "ISOLATED_RESPONSE"
    PARTIAL_NEIGHBOUR_RESPONSE = "PARTIAL_NEIGHBOUR_RESPONSE"
    OVERLAPPING_EVENTS = "OVERLAPPING_EVENTS"
    BORDERLINE_EXTREME = "BORDERLINE_EXTREME"


class ContextStatus(str, Enum):
    # names are my guess, rename to match labeling spec v1.1 if different
    # if more than one thing is missing the first match in this order wins
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    RAINFALL_UNAVAILABLE = "RAINFALL_UNAVAILABLE"
    NEIGHBOURS_UNAVAILABLE = "NEIGHBOURS_UNAVAILABLE"

    @property
    def is_insufficient(self) -> bool:
        return self is not ContextStatus.SUFFICIENT


class FeatureGroup(str, Enum):
    TARGET = "target"
    TEMPORAL = "temporal"
    RAINFALL = "rainfall"
    NEIGHBOUR = "neighbour"
    DEVICE_HEALTH = "device_health"


class RainRepresentation(str, Enum):
    CONTINUOUS = "continuous"
    CONTINUOUS_PLUS_REGIME = "continuous_plus_regime"


class ColumnGroup(str, Enum):
    IDENTIFIER = "identifier"
    TIME = "time"
    PROVENANCE = "provenance"
    FEATURE = "feature"
    LABEL = "label"
    SCENARIO_TRUTH = "scenario_truth"
    SPLIT = "split"
    AMBIGUITY = "ambiguity"
    EVALUATION = "evaluation"


# ---- canonical columns (doc 05 s47 + metadata columns from the configs) ----

@dataclass(frozen=True)
class ColumnSpec:
    name: str
    dtype: str
    group: ColumnGroup
    nullable: bool = False
    required: bool = True            # must exist in every dataset
    synthetic_only: bool = False     # only required when SYNTHETIC rows exist
    enum: type[Enum] | None = None


S, F, I, B, T = "string", "float64", "Int64", "boolean", "datetime64[ns, UTC]"
G = ColumnGroup


def _specs(*specs: ColumnSpec) -> dict[str, ColumnSpec]:
    out: dict[str, ColumnSpec] = {}
    for spec in specs:
        if spec.name in out:
            raise SchemaError(f"duplicate column spec: {spec.name}")
        out[spec.name] = spec
    return out


LABEL_COLUMN = "credibility_label"

CANONICAL_COLUMNS: dict[str, ColumnSpec] = _specs(
    # ids, metadata only
    ColumnSpec("record_id", S, G.IDENTIFIER),
    ColumnSpec("observation_id", S, G.IDENTIFIER),
    ColumnSpec("zone_id", S, G.IDENTIFIER),
    ColumnSpec("device_id", S, G.IDENTIFIER),
    ColumnSpec("sensor_instance_id", S, G.IDENTIFIER),
    ColumnSpec("sensor_type", S, G.IDENTIFIER),        # constant while only soil_moisture
    ColumnSpec("observed_at", T, G.TIME),              # split key, never a feature
    # provenance
    ColumnSpec("source_origin", S, G.PROVENANCE, enum=SourceType),
    ColumnSpec("dataset_version", S, G.PROVENANCE, required=False),
    ColumnSpec("test_run_id", S, G.PROVENANCE, nullable=True, required=False),
    ColumnSpec("calibration_version", S, G.PROVENANCE, nullable=True, required=False),
    ColumnSpec("label_source", S, G.PROVENANCE, synthetic_only=True),   # scenario_truth
    # target + step features
    ColumnSpec("target_value", F, G.FEATURE, nullable=True),
    ColumnSpec("previous_value", F, G.FEATURE, nullable=True),
    ColumnSpec("delta_from_previous", F, G.FEATURE, nullable=True),
    ColumnSpec("time_since_previous_s", F, G.FEATURE, nullable=True),
    # rolling, short window
    ColumnSpec("rolling_mean", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("rolling_std", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("rolling_min", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("rolling_max", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("short_term_slope", F, G.FEATURE, nullable=True, required=False),
    # rolling, long window (_long suffix)
    ColumnSpec("rolling_mean_long", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("rolling_std_long", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("rolling_min_long", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("rolling_max_long", F, G.FEATURE, nullable=True, required=False),
    # rainfall (extra rain_<n>m/h_sum columns can come from the features yaml)
    ColumnSpec("rain_15m_sum", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("rain_1h_sum", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("rain_6h_sum", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("rainfall_regime", S, G.FEATURE, nullable=True, required=False),
    # neighbours
    ColumnSpec("neighbour_count", I, G.FEATURE, nullable=True, required=False),
    ColumnSpec("neighbour_mean", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("neighbour_std", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("target_minus_neighbour_mean", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("neighbour_agreement_fraction", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("neighbour_age_s", F, G.FEATURE, nullable=True, required=False),
    # device health
    ColumnSpec("device_voltage", F, G.FEATURE, nullable=True, required=False),
    ColumnSpec("recent_read_failures", I, G.FEATURE, nullable=True, required=False),
    # label
    ColumnSpec(LABEL_COLUMN, S, G.LABEL, enum=Label),
    # generator side truth, metadata only
    ColumnSpec("scenario_id", S, G.SCENARIO_TRUTH, synthetic_only=True),
    ColumnSpec("scenario_type", S, G.SCENARIO_TRUTH, synthetic_only=True, enum=ScenarioType),
    ColumnSpec("fault_type", S, G.SCENARIO_TRUTH, nullable=True, required=False),
    ColumnSpec("fault_window", S, G.SCENARIO_TRUTH, nullable=True, required=False),
    ColumnSpec("fault_id", S, G.SCENARIO_TRUTH, nullable=True, required=False),
    ColumnSpec("event_id", S, G.SCENARIO_TRUTH, nullable=True, required=False),
    ColumnSpec("injected_fault_flag", B, G.SCENARIO_TRUTH, nullable=True, required=False),
    ColumnSpec("ground_truth_event_flag", B, G.SCENARIO_TRUTH, nullable=True, required=False),
    ColumnSpec("true_value", F, G.SCENARIO_TRUTH, nullable=True, required=False),
    # split
    ColumnSpec("split", S, G.SPLIT, enum=SplitName),
    ColumnSpec("split_temporal", S, G.SPLIT, nullable=True, required=False),
    ColumnSpec("split_device", S, G.SPLIT, nullable=True, required=False),
    # ambiguity / context
    ColumnSpec("ambiguous", B, G.AMBIGUITY),
    ColumnSpec("ambiguity_reason", S, G.AMBIGUITY, nullable=True, enum=AmbiguityReason),
    ColumnSpec("borderline_extreme", B, G.AMBIGUITY, required=False),
    ColumnSpec("train_eligible", B, G.AMBIGUITY),
    ColumnSpec("context_status", S, G.AMBIGUITY, enum=ContextStatus),
    # written by experiments, not the builder
    ColumnSpec("c1_prediction", S, G.EVALUATION, nullable=True, required=False, enum=Label),
)

# everything that is not a model input and not the label
METADATA_COLUMNS: tuple[str, ...] = tuple(
    n for n, s in CANONICAL_COLUMNS.items() if s.group not in (G.FEATURE, G.LABEL)
)

_RAIN_WINDOW_RE = re.compile(r"^rain_\d+[mh]_sum$")


def required_columns(source_types: Iterable[SourceType]) -> list[str]:
    has_synthetic = SourceType.SYNTHETIC in set(source_types)
    return [
        n for n, s in CANONICAL_COLUMNS.items()
        if (s.required and not s.synthetic_only) or (s.synthetic_only and has_synthetic)
    ]


def missing_columns(df: pd.DataFrame, source_types: Iterable[SourceType]) -> list[str]:
    return [c for c in required_columns(source_types) if c not in df.columns]


def unknown_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in CANONICAL_COLUMNS and not _RAIN_WINDOW_RE.match(c)]


def invalid_enum_values(df: pd.DataFrame) -> dict[str, list[str]]:
    bad_by_col: dict[str, list[str]] = {}
    for name, spec in CANONICAL_COLUMNS.items():
        if spec.enum is None or name not in df.columns:
            continue
        allowed = {m.value for m in spec.enum}
        bad = sorted({str(v) for v in df[name].dropna().unique()} - allowed)
        if bad:
            bad_by_col[name] = bad
    return bad_by_col


def dtype_problems(df: pd.DataFrame) -> dict[str, tuple[str, str]]:
    # TODO: string vs object and Int64 vs int64 need care, use pandas.api.types
    raise NotImplementedError


# ---- feature columns ----

# features yaml temporal_features.rolling_stats -> short window columns
_STAT_COLUMNS = {
    "mean": ("rolling_mean",),
    "std": ("rolling_std",),
    "slope": ("short_term_slope",),
    "range": ("rolling_min", "rolling_max"),
}
_LONG_WINDOW_STATS = ("mean", "std", "range")   # no slope for the long window

_TARGET_COLUMNS = ("target_value",)   # value-only baseline (s54) is just this
_STEP_COLUMNS = ("previous_value", "delta_from_previous", "time_since_previous_s")   # temporal group (s55)
_NEIGHBOUR_COLUMNS = (
    "neighbour_count", "neighbour_mean", "neighbour_std",
    "target_minus_neighbour_mean", "neighbour_agreement_fraction", "neighbour_age_s",
)
_HEALTH_COLUMNS = ("device_voltage", "recent_read_failures")


def get_feature_columns(
    features_cfg: Mapping[str, Any],
    *,
    groups: Iterable[FeatureGroup] | None = None,
    rain_representation: RainRepresentation = RainRepresentation.CONTINUOUS_PLUS_REGIME,
    forbidden: Sequence[str] = (),
) -> list[str]:
    """model input columns for one experiment, built from c1_features_v1.yaml.
    groups=None means all groups. pass labeling["forbidden_features"] as
    `forbidden` to make sure the list never overlaps it."""
    wanted = set(groups) if groups is not None else set(FeatureGroup)
    cols: list[str] = []

    if FeatureGroup.TARGET in wanted:
        cols += _TARGET_COLUMNS
    if FeatureGroup.TEMPORAL in wanted:
        cols += _temporal_columns(features_cfg.get("temporal_features", {}))
    if FeatureGroup.RAINFALL in wanted:
        cols += _rainfall_columns(features_cfg, rain_representation)
    if FeatureGroup.NEIGHBOUR in wanted and "neighbour_context" in features_cfg:
        cols += _NEIGHBOUR_COLUMNS
    if FeatureGroup.DEVICE_HEALTH in wanted:
        cols += _HEALTH_COLUMNS

    unknown = [c for c in cols if c not in CANONICAL_COLUMNS and not _RAIN_WINDOW_RE.match(c)]
    if unknown:
        raise SchemaError(f"feature columns not in the schema: {unknown}")
    clash = sorted(set(cols) & set(forbidden))
    if clash:
        raise SchemaError(f"feature list overlaps forbidden_features: {clash}")
    return cols


def _temporal_columns(temporal_cfg: Mapping[str, Any]) -> list[str]:
    stats = list(temporal_cfg.get("rolling_stats", []))
    bad = [s for s in stats if s not in _STAT_COLUMNS]
    if bad:
        raise SchemaError(f"unknown rolling_stats in features config: {bad}")
    cols = list(_STEP_COLUMNS) + [c for s in stats for c in _STAT_COLUMNS[s]]
    if "rolling_window_long_min" in temporal_cfg:
        cols += [f"{c}_long" for s in stats if s in _LONG_WINDOW_STATS for c in _STAT_COLUMNS[s]]
    return cols


def _rainfall_columns(features_cfg: Mapping[str, Any], rep: RainRepresentation) -> list[str]:
    # column names are the window keys, so a new window in the yaml shows up here too
    cols = [k for k in features_cfg.get("rainfall_windows", {}) if _RAIN_WINDOW_RE.match(k)]
    if not cols:
        raise SchemaError("no rain_<n>m/h_sum windows in the features config")
    regime_cfg = features_cfg.get("rainfall_regime", {})
    allowed = {RainRepresentation(r) for r in regime_cfg.get("representation_ablation", [])}
    if allowed and rep not in allowed:
        raise SchemaError(f"rain representation {rep.value!r} is not in representation_ablation")
    if rep is RainRepresentation.CONTINUOUS_PLUS_REGIME and regime_cfg.get("enabled", False):
        cols.append("rainfall_regime")
    return cols


def enum_drift_problems(labeling_cfg: Mapping[str, Any]) -> list[str]:
    """enums that copy yaml keys vs the yaml itself, empty list = no drift"""
    problems: list[str] = []
    pairs = (
        ("scenario_to_label", ScenarioType, labeling_cfg.get("scenario_to_label", {})),
        ("ambiguous.reasons", AmbiguityReason, labeling_cfg.get("ambiguous", {}).get("reasons", {})),
    )
    for name, enum_cls, cfg_keys in pairs:
        in_enum, in_yaml = {m.value for m in enum_cls}, set(cfg_keys)
        for v in sorted(in_yaml - in_enum):
            problems.append(f"{name}: '{v}' is in the yaml but not in {enum_cls.__name__}")
        for v in sorted(in_enum - in_yaml):
            problems.append(f"{name}: '{v}' is in {enum_cls.__name__} but not in the yaml")
    labels = {m.value for m in Label}
    for scenario, label in labeling_cfg.get("scenario_to_label", {}).items():
        if label not in labels:
            problems.append(f"scenario_to_label.{scenario}: '{label}' is not a Label")
    return problems


# ---- param record ----

class ParamRecord(BaseModel):
    """one {value, unit, source, justification ...} entry from the yaml.
    shape is strict, content is not: null value / PENDING_EVIDENCE still parse,
    validate.py reports those at freeze time"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: Any = None
    unit: str | None = None
    source: ParamSource
    justification: str | None = None
    reference: str | None = None      # needed for NBRO / LITERATURE / EXTERNAL_RECORDS
    method: str | None = None         # how a DATA_DRIVEN / EXTERNAL_RECORDS value was derived
    derived_from: str | None = None   # checked against forbidden_derivation_sources

    @property
    def is_null(self) -> bool:
        return self.value is None

    @property
    def is_pending(self) -> bool:
        return self.source is ParamSource.PENDING_EVIDENCE

    def needs_reference(self, reference_sources: Iterable[ParamSource | str]) -> bool:
        return self.source in {ParamSource(s) for s in reference_sources}

    def has_reference(self) -> bool:
        return bool(self.reference and self.reference.strip())


def parse_param_record(raw: Mapping[str, Any]) -> ParamRecord:
    return ParamRecord.model_validate(dict(raw))


# ---- manifest (doc 05 s48), every value must come from the real build ----

HoldoutKind = Literal["temporal", "device"]


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_code: str = Field(min_length=1)               # C1_CREDIBILITY
    version: VersionStr
    schema_version: VersionStr = DATASET_SCHEMA_VERSION
    source_types: list[SourceType] = Field(min_length=1)
    builder_version: str = Field(min_length=1)
    label_schema_version: VersionStr
    split_strategy: str = Field(min_length=1)             # scenario_grouped
    random_seed: int = Field(ge=0)                        # split seed
    generator_seed: int = Field(ge=0)                     # not the same as the split seed
    row_count: int = Field(ge=0)
    class_counts: dict[SplitName, dict[Label, int]]
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    labeling_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    features_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    holdout_skips: dict[HoldoutKind, str] = Field(default_factory=dict)   # kind -> why it was skipped

    @field_validator("source_types")
    @classmethod
    def _unique_sources(cls, v: list[SourceType]) -> list[SourceType]:
        if len(set(v)) != len(v):
            raise ValueError("source_types must not repeat")
        return v

    @field_validator("class_counts")
    @classmethod
    def _no_negative_counts(cls, v):
        for split, counts in v.items():
            if any(n < 0 for n in counts.values()):
                raise ValueError(f"negative class count in split '{split.value}'")
        return v

    @model_validator(mode="after")
    def _counts_match_row_count(self) -> "DatasetManifest":
        total = sum(n for counts in self.class_counts.values() for n in counts.values())
        if total != self.row_count:
            raise ValueError(f"class_counts add up to {total}, row_count is {self.row_count}")
        return self

    @model_validator(mode="after")
    def _skip_needs_reason(self) -> "DatasetManifest":
        blank = [k for k, why in self.holdout_skips.items() if not why.strip()]
        if blank:
            raise ValueError(f"holdout_skips needs a reason for: {blank}")
        return self

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, text: str) -> "DatasetManifest":
        return cls.model_validate_json(text)