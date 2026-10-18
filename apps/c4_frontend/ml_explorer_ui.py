from __future__ import annotations

import pandas as pd
import streamlit as st

from apps.c4_frontend.ml_explorer import (
    MODEL_CATALOG,
    WHAT_IF_FEATURES,
    C4ModelExplorer,
    available_catalog_entries,
    default_catalog_key,
)


def _heading(title: str, subtitle: str) -> None:
    st.markdown(f"### {title}")
    st.caption(subtitle)


@st.cache_resource(show_spinner=False)
def _load_explorer(model_key: str) -> C4ModelExplorer:
    return C4ModelExplorer.from_catalog(model_key)


@st.cache_data(show_spinner=False)
def _evaluate_holdout(model_key: str) -> dict:
    explorer = _load_explorer(model_key)
    evaluation = explorer.evaluate_holdout()
    return {
        "n_rows": evaluation["n_rows"],
        "accuracy": evaluation["accuracy"],
        "label_counts": evaluation["label_counts"],
        "confusion_matrix": evaluation["confusion_matrix"],
        "scored": evaluation["scored"],
        "features": evaluation["features"],
    }


def render_ml_model_explorer() -> None:
    _heading(
        "Machine Learning Model Explorer",
        "Inspect the C4 behavioral models, feature schema, holdout behaviour, "
        "and SHAP explanations used by the trust gate.",
    )

    available = available_catalog_entries()
    if not available:
        st.error(
            "No C4 model artifacts were found in experiments/c4/models. "
            "Train the baselines before using this page."
        )
        return

    catalog_keys = [entry.key for entry in available]
    default_key = default_catalog_key()
    default_index = (
        catalog_keys.index(default_key) if default_key in catalog_keys else 0
    )
    labels = {entry.key: entry.label for entry in MODEL_CATALOG}

    selected_key = st.selectbox(
        "Model artifact",
        catalog_keys,
        index=default_index,
        format_func=lambda key: labels.get(key, key),
    )

    try:
        explorer = _load_explorer(selected_key)
        profile = explorer.profile()
    except Exception as exc:
        st.error(f"{type(exc).__name__}: {exc}")
        return

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Model", str(profile["model_type"]).replace("_", " ").title())
    p2.metric("Features", profile["n_features"])
    p3.metric("Classes", ", ".join(profile["classes"]))
    p4.metric(
        "Runtime scorer",
        "YES" if profile["runtime_default"] else "NO",
    )

    if profile["notes"]:
        st.info(profile["notes"])

    if profile["runtime_default"]:
        st.caption(
            "This is the artifact loaded by the C4 dashboard backend. "
            "A high anomaly score can only quarantine packets that already "
            "passed mandatory cryptographic checks."
        )

    tabs = st.tabs(
        [
            "Profile & Schema",
            "Feature Importance",
            "Holdout Evaluation",
            "Sample Inspector",
            "What-If Scoring",
            "SHAP Plots",
        ]
    )

    with tabs[0]:
        _render_profile(explorer, profile)

    with tabs[1]:
        _render_importance(explorer)

    with tabs[2]:
        _render_holdout(selected_key)

    with tabs[3]:
        _render_inspector(selected_key, explorer)

    with tabs[4]:
        _render_what_if(selected_key, explorer)

    with tabs[5]:
        _render_shap(explorer)


def _render_profile(explorer: C4ModelExplorer, profile: dict) -> None:
    _heading(
        "Artifact profile",
        "Metadata stored with the serialized TrainedModel.",
    )

    metadata = profile["training_metadata"] or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Training samples", f"{metadata.get('n_train_samples', 'n/a')}")
    c2.metric("Estimators", f"{profile.get('n_estimators') or 'n/a'}")
    c3.metric("Random seed", f"{metadata.get('random_state', 'n/a')}")

    st.write("**Artifact path**")
    st.code(profile["artifact"], language="text")

    stored = profile["stored_metrics"]
    if stored:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Stored accuracy", f"{stored['accuracy']:.3f}")
        m2.metric("Macro precision", f"{stored['precision_macro']:.3f}")
        m3.metric("Macro recall", f"{stored['recall_macro']:.3f}")
        m4.metric("Macro F1", f"{stored['f1_macro']:.3f}")

    _heading(
        "Runtime feature schema",
        "Exact 18-feature order required by C4BehavioralModelRunner.",
    )
    st.dataframe(explorer.schema_table(), width="stretch", hide_index=True)


def _render_importance(explorer: C4ModelExplorer) -> None:
    table = explorer.importance_table()
    if table.empty:
        st.info("This estimator does not expose native feature importance.")
        return

    _heading(
        "Global feature importance",
        table["source"].iloc[0],
    )

    chart = table.set_index("feature")[["importance"]].sort_values(
        "importance",
        ascending=True,
    )
    st.bar_chart(chart)

    family = (
        table.groupby("family", as_index=False)["importance"]
        .sum()
        .sort_values("importance", ascending=False)
    )
    left, right = st.columns(2)
    with left:
        st.caption("Importance by behavioral family")
        st.bar_chart(family.set_index("family"))
    with right:
        st.dataframe(table, width="stretch", hide_index=True)


def _render_holdout(model_key: str) -> None:
    try:
        evaluation = _evaluate_holdout(model_key)
    except Exception as exc:
        st.warning(f"Holdout evaluation is unavailable: {exc}")
        return

    _heading(
        "Holdout predictions",
        "Scored against the catalog holdout split using the selected artifact.",
    )

    k1, k2, k3 = st.columns(3)
    k1.metric("Holdout packets", f"{evaluation['n_rows']:,}")
    k2.metric("Accuracy", f"{evaluation['accuracy']:.3f}")
    k3.metric(
        "Classes present",
        len(evaluation["label_counts"]),
    )

    st.caption("Confusion matrix")
    st.dataframe(
        evaluation["confusion_matrix"],
        width="stretch",
    )

    counts = pd.Series(evaluation["label_counts"], name="Packets")
    st.bar_chart(counts.to_frame())


def _render_inspector(model_key: str, explorer: C4ModelExplorer) -> None:
    try:
        evaluation = _evaluate_holdout(model_key)
        sample = explorer.inspector_sample(evaluation)
    except Exception as exc:
        st.warning(f"Sample inspection is unavailable: {exc}")
        return

    _heading(
        "Holdout sample inspector",
        "Select a packet from a class-balanced sample of the holdout split.",
    )

    if sample.empty:
        st.info("No holdout rows are available.")
        return

    filters = st.multiselect(
        "True trust label",
        sorted(sample["trust_label"].dropna().unique().tolist())
        if "trust_label" in sample.columns
        else [],
        default=sorted(sample["trust_label"].dropna().unique().tolist())
        if "trust_label" in sample.columns
        else [],
    )
    visible = (
        sample[sample["trust_label"].isin(filters)]
        if filters
        else sample
    )
    if visible.empty:
        st.info("No samples match the selected labels.")
        return

    options = visible.index.tolist()
    selected = st.selectbox(
        "Packet",
        options,
        format_func=lambda index: _sample_label(visible.loc[index]),
    )
    row = visible.loc[selected]

    c1, c2, c3 = st.columns(3)
    c1.metric("True label", str(row.get("trust_label", "n/a")))
    c2.metric("Predicted", str(row.get("predicted_label", "n/a")))
    if "anomaly_score" in row:
        c3.metric("Anomaly score", f"{float(row['anomaly_score']):.4f}")
    else:
        c3.metric("Anomaly score", "Unavailable")

    probability_columns = [
        column for column in visible.columns if column.startswith("p_")
    ]
    if probability_columns:
        probabilities = pd.Series(
            {column[2:].title(): float(row[column]) for column in probability_columns},
            name="Probability",
        )
        st.bar_chart(probabilities.to_frame())

    feature_values = pd.DataFrame(
        {
            "feature": explorer.model.feature_names,
            "value": [
                float(row[name]) for name in explorer.model.feature_names
            ],
        }
    )
    st.dataframe(feature_values, width="stretch", hide_index=True)


def _sample_label(row: pd.Series) -> str:
    packet_id = row.get("packet_id", "row")
    actual = row.get("trust_label", "?")
    predicted = row.get("predicted_label", "?")
    return f"{packet_id} — true {actual} / pred {predicted}"


def _render_what_if(model_key: str, explorer: C4ModelExplorer) -> None:
    _heading(
        "What-if scoring",
        "Adjust key behavioral features on a holdout baseline row and rescore.",
    )

    if not explorer.profile()["supports_probabilities"]:
        st.info(
            "Isolation Forest is not used as a calibrated C4 anomaly scorer, "
            "so interactive probability scoring is disabled."
        )
        return

    try:
        evaluation = _evaluate_holdout(model_key)
        sample = explorer.inspector_sample(evaluation, max_rows=80)
    except Exception as exc:
        st.warning(f"What-if scoring needs a holdout split: {exc}")
        return

    if sample.empty:
        st.info("No baseline rows are available.")
        return

    trusted = (
        sample[sample["trust_label"] == "Trusted"]
        if "trust_label" in sample.columns
        else sample
    )
    baseline = trusted.iloc[0] if not trusted.empty else sample.iloc[0]
    edited = {
        name: float(baseline[name]) for name in explorer.model.feature_names
    }

    st.caption(
        f"Baseline packet: {baseline.get('packet_id', 'unknown')} "
        f"({baseline.get('trust_label', 'unlabelled')})"
    )

    columns = st.columns(2)
    for index, feature in enumerate(WHAT_IF_FEATURES):
        if feature not in edited:
            continue
        current = edited[feature]
        span = max(abs(current) * 0.75, 1.0)
        with columns[index % 2]:
            edited[feature] = st.slider(
                feature,
                min_value=float(current - span),
                max_value=float(current + span),
                value=float(current),
            )

    features = pd.DataFrame([edited], columns=explorer.model.feature_names)
    scored = explorer.score_features(features).iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted", str(scored["predicted_label"]))
    c2.metric("Anomaly score", f"{float(scored['anomaly_score']):.4f}")
    c3.metric("ML threshold 0.70", str(scored["ml_decision"]))

    st.warning(
        "This tool scores behavioral features only. It cannot override a failed "
        "mandatory security check in the live C4 gate."
    )


def _render_shap(explorer: C4ModelExplorer) -> None:
    _heading(
        "Offline SHAP explanations",
        "Plots generated by scripts/explain_c4_model.py. They are research "
        "artifacts, not live per-packet explanations.",
    )

    plots = explorer.shap_plots()
    if not plots:
        st.info(
            "No SHAP plots were found in experiments/c4/plots. "
            "Generate them with python scripts/explain_c4_model.py."
        )
        return

    for path, caption in plots:
        st.image(str(path), caption=caption, width="stretch")
