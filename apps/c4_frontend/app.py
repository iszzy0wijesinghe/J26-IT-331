
import pandas as pd
import streamlit as st

from apps.c4_frontend.c4_backend import C4DemoBackend

st.set_page_config(
    page_title="GeoNex | C4 Security Operations",
    page_icon="C4",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --navy: #14283F;
        --navy-light: #203B56;
        --teal: #0D9488;
        --canvas: #F3F6FA;
        --surface: #FFFFFF;
        --text: #24364B;
        --muted: #64748B;
        --border: #DCE5EF;
    }

    .stApp {
        background: var(--canvas);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(243, 246, 250, 0.96);
    }

    [data-testid="stSidebar"] {
        background: var(--navy);
        border-right: 1px solid var(--navy-light);
    }

    [data-testid="stSidebar"] * {
        color: #E7EEF7;
    }

    [data-testid="stSidebar"] hr {
        border-color: #38516B;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #C4D2E1;
    }

    [data-testid="stSidebar"] button {
        background: #203B56;
        border: 1px solid #42617D;
        color: #FFFFFF;
    }

    [data-testid="stSidebar"] button:hover {
        background: #0D9488;
        border-color: #5EEAD4;
        color: #FFFFFF;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2.5rem;
        max-width: 1600px;
    }

    h1, h2, h3, h4 {
        color: #14283F !important;
        letter-spacing: -0.3px;
    }

    p, li, label {
        color: var(--text);
    }

    [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 13px;
        padding: 19px 20px;
        box-shadow: 0 3px 12px rgba(20, 40, 63, 0.045);
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: var(--navy) !important;
        font-weight: 750;
    }

    .hero {
        background: linear-gradient(
            115deg,
            #14283F 0%,
            #203B56 68%,
            #0F766E 100%
        );
        border: 1px solid #31516D;
        border-radius: 16px;
        padding: 28px 30px;
        margin-bottom: 25px;
        box-shadow: 0 8px 24px rgba(20, 40, 63, 0.12);
    }

    .hero-label {
        color: #99F6E4;
        font-size: 12px;
        font-weight: 750;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .hero-title {
        color: #FFFFFF;
        font-size: 31px;
        font-weight: 800;
        margin: 8px 0;
    }

    .hero-subtitle {
        color: #D5E6F2;
        font-size: 14px;
        line-height: 1.7;
    }

    div.stButton > button {
        background: #FFFFFF;
        color: var(--navy);
        border: 1px solid #C9D7E5;
        border-radius: 9px;
        min-height: 43px;
        font-weight: 650;
        transition: all 0.15s ease;
    }

    div.stButton > button:hover {
        background: #E6FFFB;
        border-color: var(--teal);
        color: #115E59;
    }

    [data-testid="stDataFrame"] {
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 11px;
        overflow: hidden;
    }

    [data-testid="stPlotlyChart"],
    [data-testid="stVegaLiteChart"],
    [data-testid="stArrowVegaLiteChart"] {
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 10px;
    }

    [data-testid="stAlert"] {
        border-radius: 10px;
    }

    input, textarea {
        background: #FFFFFF !important;
        color: var(--text) !important;
    }

    [data-baseweb="select"] > div {
        background: #FFFFFF;
        border-color: #C9D7E5;
    }

    hr {
        border-color: var(--border);
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "c4_results" not in st.session_state:
    st.session_state.c4_results = []

if "c4_run_count" not in st.session_state:
    st.session_state.c4_run_count = 0


def run_scenario(scenario: str) -> None:
    backend = None

    try:
        with st.spinner(f"Executing {scenario} scenario..."):
            backend = C4DemoBackend()
            results = backend.run_simulation(scenario)

        run_number = st.session_state.c4_run_count + 1

        for result in results:
            result["scenario"] = scenario
            result["run_number"] = run_number

        st.session_state.c4_run_count = run_number
        st.session_state.c4_results.extend(results)
        st.session_state.c4_notice = (
            f"{len(results)} assessment result(s) recorded "
            f"for {scenario}."
        )
        st.session_state.pop("c4_error", None)

    except Exception as exc:
        st.session_state.c4_error = (
            f"{type(exc).__name__}: {exc}"
        )

    finally:
        if backend is not None:
            backend.close()


def results_frame(results: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(results)

    if frame.empty:
        return frame

    frame["behavioural_score"] = pd.to_numeric(
        frame["behavioural_score"],
        errors="coerce",
    )

    frame["reason_codes"] = frame["reason_codes"].apply(
        lambda value: value if isinstance(value, list) else []
    )

    frame["reason_codes_text"] = frame["reason_codes"].apply(
        lambda items: ", ".join(items)
    )

    return frame


def show_results(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.info("No results match the current filters.")
        return

    display_columns = [
        "scenario",
        "packet_id",
        "device_id",
        "trust_label",
        "routing_outcome",
        "behavioural_score",
        "mandatory_security_pass",
        "eligible_for_c1",
        "quarantined",
    ]

    available = [
        column for column in display_columns
        if column in frame.columns
    ]

    st.dataframe(
        frame[available],
        width="stretch",
        hide_index=True,
        height=350,
    )


def section_heading(title: str, subtitle: str) -> None:
    st.markdown(f"### {title}")
    st.caption(subtitle)


def security_audit_frame(packet: pd.Series) -> pd.DataFrame:
    reason_codes = packet.get("reason_codes", [])

    if not isinstance(reason_codes, list):
        reason_codes = []

    controls = [
        (
            "Zone validation",
            ("ZONE_",),
            (),
        ),
        (
            "Hub validation",
            ("HUB_",),
            (),
        ),
        (
            "Device identity",
            ("IDENTITY_",),
            (),
        ),
        (
            "Credential ID",
            ("CREDENTIAL_ID_",),
            (),
        ),
        (
            "Credential verification",
            ("CREDENTIAL_",),
            ("CREDENTIAL_ID_",),
        ),
        (
            "Packet integrity",
            ("INTEGRITY_",),
            (),
        ),
        (
            "Device attestation",
            ("ATTESTATION_",),
            (),
        ),
        (
            "Telemetry provenance",
            ("PROVENANCE_",),
            (),
        ),
        (
            "Freshness validation",
            ("FRESHNESS_",),
            (),
        ),
        (
            "Replay protection",
            ("REPLAY_", "SEQUENCE_REPLAY_"),
            (),
        ),
    ]

    failure_terms = (
        "INVALID",
        "FAILED",
        "FAIL",
        "DETECTED",
        "REJECTED",
        "MISSING",
        "UNKNOWN",
        "EXPIRED",
        "REVOKED",
        "SUSPENDED",
        "STALE",
    )

    rows = []

    for control, prefixes, exclusions in controls:
        evidence = [
            code
            for code in reason_codes
            if isinstance(code, str)
            and code.startswith(prefixes)
            and not code.startswith(exclusions)
        ]

        failures = [
            code
            for code in evidence
            if any(term in code for term in failure_terms)
        ]

        if failures:
            status = "FAIL"
            detail = ", ".join(failures)
        elif evidence:
            status = "PASS"
            detail = ", ".join(evidence)
        else:
            status = "NOT REPORTED"
            detail = "No explicit reason code available"

        rows.append(
            {
                "Security control": control,
                "Result": status,
                "Evidence": detail,
            }
        )

    return pd.DataFrame(rows)


def show_security_audit(packet: pd.Series) -> None:
    st.subheader("Security Audit")

    identity, decision, model = st.columns(3)

    identity.metric(
        "Mandatory Security",
        (
            "PASS"
            if bool(packet["mandatory_security_pass"])
            else "FAIL"
        ),
    )

    decision.metric(
        "Routing Outcome",
        str(packet["routing_outcome"]),
    )

    score = pd.to_numeric(
        packet["behavioural_score"],
        errors="coerce",
    )

    model.metric(
        "Behavioural Score",
        f"{score:.4f}" if pd.notna(score) else "Unavailable",
    )

    st.dataframe(
        security_audit_frame(packet),
        width="stretch",
        hide_index=True,
    )

    eligibility, quarantine = st.columns(2)

    eligibility.metric(
        "Eligible for C1",
        "YES" if bool(packet["eligible_for_c1"]) else "NO",
    )

    quarantine.metric(
        "Quarantined",
        "YES" if bool(packet["quarantined"]) else "NO",
    )

    st.caption(
        "Audit statuses are derived from recorded C4 reason codes. "
        "NOT REPORTED means explicit evidence was not found. "
        "It does not mean that the control passed."
    )


st.sidebar.markdown("## GEONEX")
st.sidebar.caption("C4 SECURITY OPERATIONS")
st.sidebar.divider()

page = st.sidebar.radio(
    "WORKSPACE",
    [
        "Command Center",
        "Telemetry Explorer",
        "Threat Investigation",
        "Model & Policy",
    ],
)

st.sidebar.divider()
st.sidebar.markdown("**SIMULATION CONTROLS**")

if st.sidebar.button(
    "Run Valid Telemetry",
    width="stretch",
):
    run_scenario("valid")
    st.rerun()

if st.sidebar.button(
    "Test Packet Tampering",
    width="stretch",
):
    run_scenario("tampered")
    st.rerun()

if st.sidebar.button(
    "Test Replay Attack",
    width="stretch",
):
    run_scenario("replay")
    st.rerun()

if st.sidebar.button(
    "Clear Session Results",
    width="stretch",
):
    st.session_state.c4_results = []
    st.session_state.c4_run_count = 0
    st.session_state.pop("c4_notice", None)
    st.session_state.pop("c4_error", None)
    st.rerun()

st.sidebar.divider()
st.sidebar.caption("IT4010 | GeoNex Research Project")
st.sidebar.warning(
    "Simulation environment. Test credentials and test evidence "
    "verifiers are not production authentication."
)

if st.session_state.get("c4_notice"):
    st.success(st.session_state.pop("c4_notice"))

if st.session_state.get("c4_error"):
    st.error(st.session_state.pop("c4_error"))

frame = results_frame(st.session_state.c4_results)

st.markdown(
    """
    <div class="hero">
        <div class="hero-label">GeoNex / Component C4</div>
        <div class="hero-title">Security Operations Center</div>
        <div class="hero-subtitle">
            Telemetry trust • Integrity verification • Behavioral analysis
            • Secure routing
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


if page == "Command Center":
    section_heading(
        "Security Overview",
        "A summary of assessments recorded in the current dashboard session.",
    )

    processed = len(frame)

    trusted = (
        int((frame["trust_label"] == "TRUSTED").sum())
        if processed else 0
    )
    untrusted = (
        int((frame["trust_label"] == "UNTRUSTED").sum())
        if processed else 0
    )
    unknown = (
        int((frame["trust_label"] == "UNKNOWN").sum())
        if processed else 0
    )
    suspicious = (
        int((frame["trust_label"] == "SUSPICIOUS").sum())
        if processed else 0
    )
    quarantined = (
        int(frame["quarantined"].sum())
        if processed else 0
    )
    accepted = (
        int((frame["routing_outcome"] == "ACCEPT").sum())
        if processed else 0
    )

    k1, k2, k3 = st.columns(3)
    k1.metric("Packets Assessed", f"{processed:,}")
    k2.metric("Trusted", f"{trusted:,}")
    k3.metric("Accepted for C1", f"{accepted:,}")

    k4, k5, k6 = st.columns(3)
    k4.metric("Untrusted", f"{untrusted:,}")
    k5.metric("Suspicious / Unknown", f"{suspicious + unknown:,}")
    k6.metric("Quarantined", f"{quarantined:,}")

    st.divider()

    left, right = st.columns(2)

    with left:
        section_heading(
            "Trust Distribution",
            "Assessment labels returned by C4.",
        )

        if processed:
            distribution = (
                frame["trust_label"]
                .value_counts()
                .reindex(
                    ["TRUSTED", "UNTRUSTED", "SUSPICIOUS", "UNKNOWN"],
                    fill_value=0,
                )
                .rename_axis("Trust label")
                .to_frame("Packets")
            )
            st.bar_chart(distribution)
        else:
            st.info("Run a scenario to populate trust distribution.")

    with right:
        section_heading(
            "Routing Outcomes",
            "Decisions from the C4 gate.",
        )

        if processed:
            routing = (
                frame["routing_outcome"]
                .value_counts()
                .rename_axis("Routing outcome")
                .to_frame("Packets")
            )
            st.bar_chart(routing)
        else:
            st.info(
                "Routing analytics will appear after the first simulation."
            )

    st.divider()

    section_heading(
        "Assessment Activity",
        "Recent results recorded in this session.",
    )

    if processed:
        activity = frame.tail(30).reset_index(drop=True)
        activity.index = activity.index + 1

        st.line_chart(
            activity[["behavioural_score"]].set_axis(
                activity.index,
                axis="index",
            )
        )

        show_results(frame.tail(10).iloc[::-1])
    else:
        st.info("No assessments yet. Run a simulation from the sidebar.")


elif page == "Telemetry Explorer":
    section_heading(
        "Telemetry Explorer",
        "Filter assessment records and inspect individual telemetry packets.",
    )

    if frame.empty:
        st.info("Run a simulation to create records for exploration.")
    else:
        f1, f2, f3 = st.columns(3)

        with f1:
            device_options = sorted(
                frame["device_id"].dropna().unique().tolist()
            )
            selected_devices = st.multiselect(
                "Device",
                device_options,
                default=device_options,
            )

        with f2:
            trust_options = sorted(
                frame["trust_label"].dropna().unique().tolist()
            )
            selected_trust = st.multiselect(
                "Trust label",
                trust_options,
                default=trust_options,
            )

        with f3:
            scenario_options = sorted(
                frame["scenario"].dropna().unique().tolist()
            )
            selected_scenarios = st.multiselect(
                "Scenario",
                scenario_options,
                default=scenario_options,
            )

        filtered = frame[
            frame["device_id"].isin(selected_devices)
            & frame["trust_label"].isin(selected_trust)
            & frame["scenario"].isin(selected_scenarios)
        ].copy()

        st.caption(
            f"{len(filtered)} packet assessment(s) match your filters."
        )

        show_results(filtered)

        if not filtered.empty:
            packet_options = filtered.index.tolist()

            selected_index = st.selectbox(
                "Investigate a packet",
                packet_options,
                format_func=lambda index: (
                    f"{filtered.loc[index, 'packet_id']} — "
                    f"{filtered.loc[index, 'trust_label']} / "
                    f"{filtered.loc[index, 'routing_outcome']}"
                ),
            )

            packet = filtered.loc[selected_index]

            st.subheader("Packet Details")

            d1, d2, d3 = st.columns(3)

            d1.metric("Trust Label", packet["trust_label"])
            d2.metric("Routing", packet["routing_outcome"])

            score = packet["behavioural_score"]

            d3.metric(
                "Behavioural Score",
                f"{score:.4f}" if pd.notna(score) else "Unavailable",
            )

            st.write("**Packet ID:**", packet["packet_id"])
            st.write("**Device ID:**", packet["device_id"])

            st.write("**Security reason codes**")

            for reason in packet["reason_codes"]:
                st.code(reason, language="text")

            show_security_audit(packet)


elif page == "Threat Investigation":
    section_heading(
        "Threat Investigation",
        "Review suspicious routing decisions, failed checks, and quarantined packets.",
    )

    if frame.empty:
        st.info("No assessment records are available yet.")
    else:
        incidents = frame[
            (frame["trust_label"] != "TRUSTED")
            | frame["quarantined"].astype(bool)
            | (~frame["mandatory_security_pass"].astype(bool))
        ].copy()

        a1, a2, a3 = st.columns(3)

        a1.metric("Flagged Assessments", len(incidents))

        a2.metric(
            "Integrity Failures",
            int(
                incidents["reason_codes"].apply(
                    lambda reasons: any(
                        code == "INTEGRITY_INVALID"
                        for code in reasons
                    )
                ).sum()
            ),
        )

        a3.metric(
            "Replay Detections",
            int(
                incidents["reason_codes"].apply(
                    lambda reasons: any(
                        "REPLAY" in code
                        for code in reasons
                    )
                ).sum()
            ),
        )

        if incidents.empty:
            st.success(
                "No security incidents are present in this session."
            )
        else:
            show_results(incidents.iloc[::-1])

            st.subheader("Incident Reason Frequency")

            reason_counts: dict[str, int] = {}

            for reasons in incidents["reason_codes"]:
                for reason in reasons:
                    reason_counts[reason] = (
                        reason_counts.get(reason, 0) + 1
                    )

            reason_frame = pd.DataFrame(
                sorted(
                    reason_counts.items(),
                    key=lambda item: item[1],
                    reverse=True,
                ),
                columns=["Reason code", "Occurrences"],
            ).set_index("Reason code")

            st.bar_chart(reason_frame.head(12))

            st.subheader("Investigation Details")

            incident_indices = incidents.index.tolist()

            selected_index = st.selectbox(
                "Select packet",
                incident_indices,
                format_func=lambda index: (
                    f"{incidents.loc[index, 'packet_id']} — "
                    f"{incidents.loc[index, 'scenario']} — "
                    f"{incidents.loc[index, 'routing_outcome']}"
                ),
            )

            incident = incidents.loc[selected_index]

            st.write("**Device:**", incident["device_id"])
            st.write("**Scenario:**", incident["scenario"])
            st.write("**Trust:**", incident["trust_label"])
            st.write("**Routing:**", incident["routing_outcome"])

            st.write("**Reason codes:**")

            for reason in incident["reason_codes"]:
                st.code(reason, language="text")

            show_security_audit(incident)

            st.warning(
                "This view reports simulation assessment outcomes. "
                "It does not provide authorized quarantine release controls."
            )


elif page == "Model & Policy":
    section_heading(
        "Model & Security Policy",
        "Technical information about the configured C4 demonstration.",
    )

    m1, m2, m3 = st.columns(3)

    m1.metric("Model", "Random Forest")
    m2.metric("Expected Features", "18")
    m3.metric("Security Policy", "C4_POLICY_1.1")

    st.subheader("Behavioural model")

    st.write(
        "The dashboard backend loads the corrected Random Forest model "
        "and extracts runtime features through RuntimeFeatureAdapter."
    )

    st.subheader("Mandatory security controls")

    controls = pd.DataFrame(
        [
            ("Device identity and lifecycle", "Gate check"),
            ("Packet integrity", "Signature verification"),
            ("Freshness", "Timestamp validation"),
            ("Attestation", "Demo evidence verifier"),
            ("Provenance", "Demo evidence verifier"),
            ("Replay protection", "Packet and sequence checks"),
            ("Behavioural assessment", "Random Forest inference"),
            ("Routing", "C4 trust gate"),
        ],
        columns=["Control", "Configured mechanism"],
    )

    st.dataframe(
        controls,
        width="stretch",
        hide_index=True,
    )

    st.info(
        "Behavioural inference cannot override a failed mandatory security "
        "check. This dashboard uses simulation evidence verifiers; it is "
        "not a production device-attestation deployment."
    )


st.divider()

st.caption(
    "GeoNex C4 | Research simulation dashboard | "
    "Session results are in memory and are not persistent audit storage."
)
