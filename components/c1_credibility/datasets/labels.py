# labels.py - scenario truth -> label, ambiguity flag, context status (GEONEX-5)
# lives in components/c1_credibility/datasets/
#
# labels come ONLY from the generator's scenario truth, never from feature
# thresholds. so this file must not import features / neighbours / rainfall
# code, only schemas + stdlib + pandas (there is a test for that, see notes)
#
# order (from labeling.precedence): context eligibility, fault truth, event
# truth, clean

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from schemas import (
    LABEL_COLUMN,
    AmbiguityReason,
    ContextStatus,
    Label,
    ScenarioType,
)

EXPECTED_PRECEDENCE = ["context_eligibility", "fault_truth", "event_truth", "clean"]
LABEL_SOURCE = "scenario_truth"

# if a row matches more than one ambiguity reason, the first one in this list wins
REASON_PRIORITY = [
    AmbiguityReason.OVERLAPPING_EVENTS,
    AmbiguityReason.FAULT_BELOW_DETECTABILITY,
    AmbiguityReason.ISOLATED_RESPONSE,
    AmbiguityReason.PARTIAL_NEIGHBOUR_RESPONSE,
    AmbiguityReason.BORDERLINE_EXTREME,
]

# fault family -> generator param that sets the weakest fault we count as detectable
# (fault_magnitude must be in that param's unit). stuck / quantization / out of range /
# dropout have no magnitude rule yet
DETECTABILITY_PARAM = {
    ScenarioType.FAULT_SPIKE: "spike_min_sigma",
    ScenarioType.FAULT_BIAS: "bias_min_sigma",
    ScenarioType.FAULT_DRIFT: "drift_floor_sigma",
    ScenarioType.FAULT_EXCESSIVE_NOISE: "noise_factor_min",
}

# columns the truth table needs. these live in the builder's truth table, NOT in
# the released dataset (if one is kept, add it to forbidden_features + schemas)
TRUTH_COLUMNS = [
    "scenario_id", "scenario_type", "fault_active", "fault_magnitude",
    "in_event_window", "event_id", "event_response_sigma",
    "event_neighbour_count", "responding_neighbours", "overlapping_events",
    "borderline_extreme", "history_obs", "rainfall_available", "neighbours_available",
]

OUTPUT_COLUMNS = [
    LABEL_COLUMN, "label_source", "context_status", "ambiguous",
    "ambiguity_reason", "borderline_extreme", "train_eligible",
]


class LabelingError(ValueError):
    pass


# ---- inputs / outputs ----

@dataclass(frozen=True)
class ScenarioTruth:
    # what the generator knows about one row
    scenario_id: str
    scenario_type: ScenarioType
    fault_active: bool = False            # fault is injected on THIS sensor at this row
    fault_magnitude: float | None = None  # in the unit of the family's detectability param
    in_event_window: bool = False
    event_id: str | None = None
    event_response_sigma: float | None = None   # how strongly this sensor responds in the event
    event_neighbour_count: int = 0
    responding_neighbours: int = 0
    overlapping_events: int = 0           # extra events active at the same row
    borderline_extreme: bool = False      # set by the generator, assumption: genuine extreme close to the anomaly range


@dataclass(frozen=True)
class ContextFacts:
    # only availability facts from the builder, not signal values
    history_obs: int
    rainfall_available: bool
    neighbours_available: bool


@dataclass(frozen=True)
class LabelResult:
    label: Label
    context_status: ContextStatus
    ambiguity_reason: AmbiguityReason | None
    borderline_extreme: bool
    train_eligible: bool

    @property
    def ambiguous(self) -> bool:
        return self.ambiguity_reason is not None


# ---- rules from the labeling yaml ----

@dataclass(frozen=True)
class LabelingRules:
    scenario_to_label: Mapping[ScenarioType, Label]
    reason_policy: Mapping[AmbiguityReason, str]       # "exclude" | "keep"
    event_response_epsilon_sigma: float
    neighbour_agreement_fraction_min: float
    min_history_obs: int
    detectability_min: Mapping[ScenarioType, float]

    @classmethod
    def from_config(cls, labeling_cfg: Mapping[str, Any]) -> "LabelingRules":
        # fails loudly when a needed value is still null, so labels can't be
        # built from a half filled config
        if labeling_cfg.get("labeling", {}).get("label_source") != LABEL_SOURCE:
            raise LabelingError(f"labeling.label_source must be {LABEL_SOURCE}")
        if list(labeling_cfg.get("labeling", {}).get("precedence", [])) != EXPECTED_PRECEDENCE:
            raise LabelingError(f"labeling.precedence must be {EXPECTED_PRECEDENCE}")
        if labeling_cfg.get("insufficient_context", {}).get("policy") != "exclude_from_training":
            raise LabelingError("insufficient_context.policy must be exclude_from_training")

        s2l = {ScenarioType(k): Label(v) for k, v in labeling_cfg["labeling"]["scenario_to_label"].items()}
        missing = set(ScenarioType) - set(s2l)
        if missing:
            raise LabelingError(f"scenario_to_label has no entry for: {sorted(m.value for m in missing)}")

        policy = {AmbiguityReason(k): v for k, v in labeling_cfg["ambiguous"]["reasons"].items()}
        bad = {k.value: v for k, v in policy.items() if v not in ("exclude", "keep")}
        if bad:
            raise LabelingError(f"ambiguous.reasons must be exclude or keep, got {bad}")
        if set(policy) != set(AmbiguityReason):
            raise LabelingError("ambiguous.reasons does not match AmbiguityReason")

        gen = "generator.anomaly_injection."
        return cls(
            scenario_to_label=s2l,
            reason_policy=policy,
            event_response_epsilon_sigma=float(_param(labeling_cfg, "generator.valid_event_scenario.event_response_epsilon_sigma")),
            neighbour_agreement_fraction_min=float(_param(labeling_cfg, "generator.valid_event_scenario.neighbour_agreement_fraction_min")),
            min_history_obs=int(_param(labeling_cfg, "insufficient_context.min_history_obs")),
            detectability_min={t: float(_param(labeling_cfg, gen + name)) for t, name in DETECTABILITY_PARAM.items()},
        )


def _param(cfg: Mapping[str, Any], dotted: str) -> Any:
    node: Any = cfg
    for key in dotted.split("."):
        if not isinstance(node, Mapping) or key not in node:
            raise LabelingError(f"{dotted} is missing in the labeling config")
        node = node[key]
    value = node.get("value") if isinstance(node, Mapping) and "value" in node else node
    if value is None:
        raise LabelingError(f"{dotted} is still null, fill it before building labels")
    return value


# ---- steps ----

def assign_context_status(facts: ContextFacts, rules: LabelingRules) -> ContextStatus:
    # first match wins: history, then rainfall, then neighbours
    if facts.history_obs < rules.min_history_obs:
        return ContextStatus.INSUFFICIENT_HISTORY
    if not facts.rainfall_available:
        return ContextStatus.RAINFALL_UNAVAILABLE
    if not facts.neighbours_available:
        return ContextStatus.NEIGHBOURS_UNAVAILABLE
    return ContextStatus.SUFFICIENT


def _responds(truth: ScenarioTruth, rules: LabelingRules) -> bool:
    # weak responses stay CLEAN
    return (
        truth.in_event_window
        and truth.event_response_sigma is not None
        and truth.event_response_sigma >= rules.event_response_epsilon_sigma
    )


def assign_label(truth: ScenarioTruth, rules: LabelingRules) -> Label:
    mapped = rules.scenario_to_label[truth.scenario_type]

    # fault truth first: the faulty sensor is ANOMALY even inside an event,
    # its neighbours are separate rows and keep VALID_EVENT
    if truth.fault_active:
        if mapped is not Label.ANOMALY:
            raise LabelingError(f"{truth.scenario_id}: fault_active but {truth.scenario_type.value} maps to {mapped.value}")
        return Label.ANOMALY

    # event truth
    if _responds(truth, rules):
        if mapped is not Label.VALID_EVENT:
            raise LabelingError(f"{truth.scenario_id}: responding in an event but {truth.scenario_type.value} maps to {mapped.value}")
        return Label.VALID_EVENT

    return Label.CLEAN


def assign_ambiguity(truth: ScenarioTruth, label: Label, rules: LabelingRules) -> AmbiguityReason | None:
    hits: set[AmbiguityReason] = set()

    if truth.overlapping_events > 0:
        hits.add(AmbiguityReason.OVERLAPPING_EVENTS)

    if label is Label.ANOMALY:
        floor = rules.detectability_min.get(truth.scenario_type)
        if floor is not None and truth.fault_magnitude is not None and truth.fault_magnitude < floor:
            hits.add(AmbiguityReason.FAULT_BELOW_DETECTABILITY)

    if label is Label.VALID_EVENT and truth.event_neighbour_count > 0:
        if truth.responding_neighbours == 0:
            hits.add(AmbiguityReason.ISOLATED_RESPONSE)
        elif truth.responding_neighbours / truth.event_neighbour_count < rules.neighbour_agreement_fraction_min:
            hits.add(AmbiguityReason.PARTIAL_NEIGHBOUR_RESPONSE)

    if truth.borderline_extreme:
        hits.add(AmbiguityReason.BORDERLINE_EXTREME)

    return next((r for r in REASON_PRIORITY if r in hits), None)


def label_row(truth: ScenarioTruth, facts: ContextFacts, rules: LabelingRules) -> LabelResult:
    status = assign_context_status(facts, rules)   # step 1, context eligibility
    label = assign_label(truth, rules)             # steps 2-4, fault / event / clean
    reason = assign_ambiguity(truth, label, rules)

    excluded_by_reason = reason is not None and rules.reason_policy[reason] == "exclude"
    return LabelResult(
        label=label,
        context_status=status,
        ambiguity_reason=reason,
        borderline_extreme=truth.borderline_extreme,
        # label stays on insufficient-context rows (truth exists), they just are not trained on
        train_eligible=not status.is_insufficient and not excluded_by_reason,
    )


# ---- dataframe wrapper ----

def _row_to_inputs(row: Any) -> tuple[ScenarioTruth, ContextFacts]:
    truth = ScenarioTruth(
        scenario_id=str(row.scenario_id),
        scenario_type=ScenarioType(row.scenario_type),
        fault_active=bool(row.fault_active),
        fault_magnitude=None if pd.isna(row.fault_magnitude) else float(row.fault_magnitude),
        in_event_window=bool(row.in_event_window),
        event_id=None if pd.isna(row.event_id) else str(row.event_id),
        event_response_sigma=None if pd.isna(row.event_response_sigma) else float(row.event_response_sigma),
        event_neighbour_count=int(row.event_neighbour_count),
        responding_neighbours=int(row.responding_neighbours),
        overlapping_events=int(row.overlapping_events),
        borderline_extreme=bool(row.borderline_extreme),
    )
    facts = ContextFacts(int(row.history_obs), bool(row.rainfall_available), bool(row.neighbours_available))
    return truth, facts


def label_dataframe(truth_df: pd.DataFrame, rules: LabelingRules) -> pd.DataFrame:
    """takes the builder's truth table (TRUTH_COLUMNS), returns the label columns
    with the same index. row loop for now, vectorize if it gets slow"""
    missing = [c for c in TRUTH_COLUMNS if c not in truth_df.columns]
    if missing:
        raise LabelingError(f"truth table is missing columns: {missing}")

    out = []
    for row in truth_df.itertuples(index=False):
        truth, facts = _row_to_inputs(row)
        res = label_row(truth, facts, rules)
        out.append({
            LABEL_COLUMN: res.label.value,
            "label_source": LABEL_SOURCE,
            "context_status": res.context_status.value,
            "ambiguous": res.ambiguous,
            "ambiguity_reason": res.ambiguity_reason.value if res.ambiguity_reason else None,
            "borderline_extreme": res.borderline_extreme,
            "train_eligible": res.train_eligible,
        })
    result = pd.DataFrame(out, index=truth_df.index, columns=OUTPUT_COLUMNS)
    return result.astype({
        LABEL_COLUMN: "string", "label_source": "string", "context_status": "string",
        "ambiguous": "boolean", "ambiguity_reason": "string",
        "borderline_extreme": "boolean", "train_eligible": "boolean",
    })


def expected_labels(truth_df: pd.DataFrame, rules: LabelingRules) -> pd.Series:
    # validate.py compares the dataset's label column against this
    return label_dataframe(truth_df, rules)[LABEL_COLUMN]