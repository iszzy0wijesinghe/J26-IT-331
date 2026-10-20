from __future__ import annotations

import json
import pandas as pd
import streamlit as st
from pathlib import Path

from apps.c4_frontend.c4_backend import C4DemoBackend
from shared.simulation.topology import get_all_demo_pipes


def heading(title: str, subtitle: str) -> None:
    st.markdown(f"### {title}")
    st.caption(subtitle)


def help_card(title: str, body: str) -> None:
    st.markdown(
        f'<div class="help-card"><h4>{title}</h4><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def provenance_banner() -> None:
    st.markdown(
        """
        <div class="provenance-banner">
            <h4>Data shown on this dashboard</h4>
            <p>
                Command Center, Telemetry Explorer and Threat Investigation
                metrics are counted from Streamlit session assessments created
                by the sidebar scenario buttons. They are not live ESP32
                packets and they are not PostgreSQL rows unless a separate
                ingestion script was run. Clear Session Results removes them.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_workspace() -> None:
    st.markdown(
        """
        <div class="empty-card">
            <h4>No session assessments yet</h4>
            <p>
                Use a sidebar scenario such as
                <strong>Run Valid Telemetry (HMAC)</strong>
                or <strong>Run Valid X.509 + ECDSA</strong>.
                Each click calls
                <code>C4DemoBackend.run_simulation()</code>,
                which generates synthetic packets and processes them through
                the real <code>C4TelemetryGate</code>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def unavailable(value) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, float) and pd.isna(value):
        return "Unavailable"
    text = str(value)
    if text in {"", "nan", "None"}:
        return "Unavailable"
    return text


def show_results(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.info("No results match the current filters.")
        return

    display_columns = [
        "scenario",
        "packet_id",
        "assessment_id",
        "device_id",
        "zone_id",
        "signature_algorithm",
        "trust_label",
        "routing_outcome",
        "behavioural_score",
        "mandatory_security_pass",
        "ml_ran",
        "eligible_for_c1",
        "quarantined",
        "storage",
    ]
    available = [column for column in display_columns if column in frame.columns]
    st.dataframe(frame[available], width="stretch", hide_index=True, height=340)


def security_audit_frame(packet: pd.Series) -> pd.DataFrame:
    reason_codes = packet.get("reason_codes", [])
    if not isinstance(reason_codes, list):
        reason_codes = []

    controls = [
        ("Zone validation", ("ZONE_",), ()),
        ("Hub validation", ("HUB_",), ()),
        ("Device identity", ("IDENTITY_", "DEVICE_"), ()),
        ("Certificate validation", ("CERTIFICATE_",), ()),
        ("Credential ID", ("CREDENTIAL_ID_",), ()),
        ("Credential verification", ("CREDENTIAL_",), ("CREDENTIAL_ID_",)),
        ("Packet integrity", ("INTEGRITY_",), ()),
        ("Device attestation", ("ATTESTATION_",), ()),
        ("Telemetry provenance", ("PROVENANCE_",), ()),
        ("Freshness validation", ("FRESHNESS_", "TIMESTAMP_"), ()),
        ("Replay protection", ("REPLAY_", "SEQUENCE_REPLAY_"), ()),
        ("Behavioral ML", ("BEHAVIOURAL_",), ()),
    ]
    failure_terms = (
        "INVALID", "FAILED", "FAIL", "DETECTED", "REJECTED", "MISSING",
        "UNKNOWN", "EXPIRED", "REVOKED", "SUSPENDED", "STALE", "UNTRUSTED",
        "MISMATCH", "MALFORMED", "SELF_SIGNED", "NOT_YET_VALID", "ANOMALY",
        "NOT_ACTIVE",
    )
    rows = []
    for control, prefixes, exclusions in controls:
        evidence = [
            code for code in reason_codes
            if isinstance(code, str)
            and code.startswith(prefixes)
            and not code.startswith(exclusions)
        ]
        failures = [
            code for code in evidence
            if any(term in code for term in failure_terms)
        ]
        if failures:
            status, detail = "FAIL", ", ".join(failures)
        elif evidence:
            status, detail = "PASS", ", ".join(evidence)
        else:
            status, detail = "NOT REPORTED", "No explicit reason code available"
        rows.append(
            {"Security control": control, "Result": status, "Evidence": detail}
        )
    return pd.DataFrame(rows)


def show_packet_detail(packet: pd.Series) -> None:
    heading(
        "Packet lifecycle",
        "Fields below come from the simulated TelemetryPacket and C4TrustAssessment.",
    )

    origin, storage, identity = st.columns(3)
    origin.metric("Data origin", unavailable(packet.get("data_origin")))
    storage.metric("Stored in", unavailable(packet.get("storage")))
    identity.metric("Assessment ID", unavailable(packet.get("assessment_id")))

    if packet.get("origin_explanation"):
        st.info(packet["origin_explanation"])
    if packet.get("storage_explanation"):
        st.warning(packet["storage_explanation"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trust label", unavailable(packet.get("trust_label")))
    c2.metric("Routing", unavailable(packet.get("routing_outcome")))
    c3.metric(
        "Mandatory security",
        "PASS" if bool(packet.get("mandatory_security_pass")) else "FAIL",
    )
    score = pd.to_numeric(packet.get("behavioural_score"), errors="coerce")
    c4.metric(
        "Behavioral score",
        f"{score:.4f}" if pd.notna(score) else "Unavailable / not scored",
    )

    st.write("**Identity and timing**")
    st.write(
        {
            "packet_id": unavailable(packet.get("packet_id")),
            "device_id": unavailable(packet.get("device_id")),
            "zone_id": unavailable(packet.get("zone_id")),
            "hub_id": unavailable(packet.get("hub_id")),
            "sequence_no": unavailable(packet.get("sequence_no")),
            "observed_at": unavailable(packet.get("observed_at")),
            "received_at": unavailable(packet.get("received_at")),
            "source_origin": unavailable(packet.get("source_origin")),
            "authentication": unavailable(packet.get("signature_algorithm")),
            "credential_id": unavailable(packet.get("credential_id")),
            "certificate_present": unavailable(packet.get("certificate_present")),
        }
    )

    st.write("**Communication and health fields present on this packet**")
    st.write(
        {
            "rssi_dbm": unavailable(packet.get("rssi_dbm")),
            "snr_db": unavailable(packet.get("snr_db")),
            "retry_count": unavailable(packet.get("retry_count")),
            "tx_interval_s": unavailable(packet.get("tx_interval_s")),
            "freshness_status": unavailable(packet.get("freshness_status")),
            "battery_pct": unavailable(packet.get("battery_pct")),
            "battery_voltage": unavailable(packet.get("battery_voltage")),
            "sensor_fault_flag": unavailable(packet.get("sensor_fault_flag")),
        }
    )

    measurements = packet.get("measurements", [])
    if isinstance(measurements, list) and measurements:
        st.write("**Sensor measurements**")
        st.dataframe(pd.DataFrame(measurements), width="stretch", hide_index=True)
    else:
        st.caption("No measurement list is attached to this session row.")

    st.write("**Reason codes**")
    reasons = packet.get("reason_codes", [])
    if isinstance(reasons, list) and reasons:
        for reason in reasons:
            st.code(reason, language="text")
    else:
        st.caption("No reason codes recorded.")

    st.subheader("Security audit")
    st.dataframe(security_audit_frame(packet), width="stretch", hide_index=True)
    st.caption(
        "NOT REPORTED means this session row has no matching reason code. "
        "It does not mean the control passed."
    )

    q1, q2, q3 = st.columns(3)
    q1.metric("Eligible for C1", "YES" if bool(packet.get("eligible_for_c1")) else "NO")
    q2.metric("Quarantined", "YES" if bool(packet.get("quarantined")) else "NO")
    q3.metric("Quarantine ID", unavailable(packet.get("quarantine_id")))
    q4, q5 = st.columns(2)
    q4.metric("ML ran", "YES" if bool(packet.get("ml_ran")) else "NO")
    q5.metric(
        "Saved to PostgreSQL",
        "YES" if bool(packet.get("persisted_to_database")) else "NO",
    )


def render_how_c4_works() -> None:
    heading(
        "How C4 works",
        "Verified from the current repository. This page describes code that exists today.",
    )
    help_card(
        "Purpose of C4",
        "C4 is the trust gate for GeoNex telemetry. It decides whether a packet "
        "is authentic enough to enter C1. Cryptographic and identity checks are "
        "mandatory. Behavioral ML can only influence packets that already passed "
        "those checks.",
    )

    st.markdown(
        """
**Verified runtime path used by this dashboard**

`Sidebar button → C4DemoBackend.run_simulation() → generate_scheduled_demo_telemetry()
→ C4TrustService.sign_packet() or sign_packet_ecdsa() → C4TelemetryGate.process()
→ C4TrustService.assess() → optional C4BehavioralModelRunner → QuarantineManager
→ Streamlit session_state.c4_results`

**Not used by this dashboard**

- Physical ESP32 or LoRa packets
- Direct reads from `experiments/c4/data/*.csv`
- Direct writes to PostgreSQL `telemetry_packets`

The CSV files and saved models are used for offline training and the ML Model Explorer.
PostgreSQL is used by `scripts/load_demo_simulation.py`, a separate ingestion path.
        """
    )

    st.subheader("HMAC versus ECDSA")
    left, right = st.columns(2)
    with left:
        st.markdown(
            """
**HMAC-SHA256**
- Shared secret known to sender and verifier
- `C4TrustService.sign_packet()`
- Fast symmetric integrity check
- Dashboard demo secrets stay in memory and are never shown
            """
        )
    with right:
        st.markdown(
            """
**ECDSA-SHA256 (P-256)**
- Device private key signs; C4 verifies with the public key
- `C4TrustService.sign_packet_ecdsa()`
- Usually paired with an X.509 device certificate
- Private keys are generated in memory for the demo only
            """
        )

    st.subheader("Glossary")
    st.dataframe(
        pd.DataFrame(
            [
                (
                    "TelemetryPacket",
                    "Normalized packet contract in shared/contracts/telemetry.py",
                ),
                (
                    "Mandatory security",
                    "Identity, zone/hub, cert, signature, freshness, replay, "
                    "attestation, provenance",
                ),
                (
                    "Behavioral score",
                    "Anomaly score 1 - P(Trusted) from the Random Forest",
                ),
                (
                    "TRUSTED / ACCEPT",
                    "Mandatory checks passed and score below 0.70; eligible for C1",
                ),
                (
                    "UNTRUSTED / REJECT",
                    "A mandatory check failed; ML cannot override this",
                ),
                (
                    "SUSPICIOUS / QUARANTINE",
                    "Mandatory checks passed but ML score >= 0.70",
                ),
                (
                    "UNKNOWN / SECURITY_REVIEW",
                    "Evidence missing or ML score unavailable",
                ),
                (
                    "Session result",
                    "A row in Streamlit memory; lost on refresh or Clear Session",
                ),
                (
                    "Quarantine JSON",
                    "Evidence file; dashboard uses a temp folder deleted after each run",
                ),
            ],
            columns=["Term", "Meaning in this repository"],
        ),
        width="stretch",
        hide_index=True,
    )


def render_command_center(frame: pd.DataFrame) -> None:
    heading(
        "Command Center",
        "Session-only security operations summary. "
        "Every number is counted from assessments in this browser session.",
    )
    provenance_banner()
    if frame.empty:
        empty_workspace()
        return

    processed = len(frame)
    trusted = int((frame["trust_label"] == "TRUSTED").sum())
    untrusted = int((frame["trust_label"] == "UNTRUSTED").sum())
    suspicious = int((frame["trust_label"] == "SUSPICIOUS").sum())
    unknown = int((frame["trust_label"] == "UNKNOWN").sum())
    quarantined = int(frame["quarantined"].sum()) if "quarantined" in frame else 0
    accepted = int((frame["routing_outcome"] == "ACCEPT").sum())
    auth_fail = int((~frame["mandatory_security_pass"].astype(bool)).sum())
    ml_ran = int(frame["ml_ran"].sum()) if "ml_ran" in frame else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Packets assessed", f"{processed:,}", help="session_state.c4_results length")
    k2.metric("Trusted", f"{trusted:,}", help="trust_label == TRUSTED")
    k3.metric("Accepted for C1", f"{accepted:,}", help="routing_outcome == ACCEPT")
    k4.metric("Authentication failures", f"{auth_fail:,}", help="mandatory_security_pass is false")

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Untrusted / rejected", f"{untrusted:,}")
    k6.metric("Suspicious", f"{suspicious:,}")
    k7.metric("Unknown / review", f"{unknown:,}")
    k8.metric("Quarantined", f"{quarantined:,}")

    st.caption(f"Behavioral model produced a score for {ml_ran} of {processed} session packets.")

    left, right = st.columns(2)
    with left:
        heading("Trust distribution", "Labels returned by C4TrustService.assess().")
        distribution = (
            frame["trust_label"].value_counts()
            .reindex(["TRUSTED", "UNTRUSTED", "SUSPICIOUS", "UNKNOWN"], fill_value=0)
            .rename_axis("Trust label").to_frame("Packets")
        )
        st.bar_chart(distribution)
    with right:
        heading("Routing outcomes", "Decisions from C4TelemetryGate.")
        st.bar_chart(
            frame["routing_outcome"].value_counts().rename_axis("Routing").to_frame("Packets")
        )

    heading("Recent session activity", "Last 30 behavioral scores. Missing scores appear as gaps.")
    activity = frame.tail(30).reset_index(drop=True)
    activity.index = activity.index + 1
    st.line_chart(activity[["behavioural_score"]].set_axis(activity.index, axis="index"))
    show_results(frame.tail(10).iloc[::-1])


def render_telemetry_explorer(frame: pd.DataFrame) -> None:
    heading(
        "Telemetry Explorer",
        "Inspect one simulated packet, including fields that actually exist on the session row.",
    )
    help_card(
        "What happens when I click a scenario button?",
        "C4DemoBackend creates synthetic packets, signs them, and calls "
        "C4TelemetryGate.process(). The assessment is appended to session memory. "
        "It is not loaded from the C4 CSV dataset and not written to PostgreSQL.",
    )
    if frame.empty:
        empty_workspace()
        return

    f1, f2, f3 = st.columns(3)
    with f1:
        devices = sorted(frame["device_id"].dropna().unique().tolist())
        selected_devices = st.multiselect("Device", devices, default=devices)
    with f2:
        labels = sorted(frame["trust_label"].dropna().unique().tolist())
        selected_trust = st.multiselect("Trust label", labels, default=labels)
    with f3:
        scenarios = sorted(frame["scenario"].dropna().unique().tolist())
        selected_scenarios = st.multiselect("Scenario", scenarios, default=scenarios)

    filtered = frame[
        frame["device_id"].isin(selected_devices)
        & frame["trust_label"].isin(selected_trust)
        & frame["scenario"].isin(selected_scenarios)
    ].copy()
    st.caption(f"{len(filtered)} packet assessment(s) match the filters.")
    show_results(filtered)
    if filtered.empty:
        return

    selected_index = st.selectbox(
        "Investigate a packet",
        filtered.index.tolist(),
        format_func=lambda index: (
            f"{filtered.loc[index, 'packet_id']} — "
            f"{filtered.loc[index, 'trust_label']} / "
            f"{filtered.loc[index, 'routing_outcome']}"
        ),
    )
    show_packet_detail(filtered.loc[selected_index])


def render_threat_investigation(frame: pd.DataFrame) -> None:
    heading(
        "Threat Investigation",
        "Rejected, suspicious, unknown or quarantined session assessments.",
    )
    if frame.empty:
        empty_workspace()
        return

    incidents = frame[
        (frame["trust_label"] != "TRUSTED")
        | frame["quarantined"].astype(bool)
        | (~frame["mandatory_security_pass"].astype(bool))
    ].copy()

    a1, a2, a3 = st.columns(3)
    a1.metric("Flagged assessments", len(incidents))
    a2.metric(
        "Integrity failures",
        int(incidents["reason_codes"].apply(
            lambda reasons: any(code == "INTEGRITY_INVALID" for code in reasons)
        ).sum()) if not incidents.empty else 0,
    )
    a3.metric(
        "Replay detections",
        int(incidents["reason_codes"].apply(
            lambda reasons: any("REPLAY" in code for code in reasons)
        ).sum()) if not incidents.empty else 0,
    )

    if incidents.empty:
        st.success("No flagged assessments in this session.")
        return

    show_results(incidents.iloc[::-1])
    reason_counts: dict[str, int] = {}
    for reasons in incidents["reason_codes"]:
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    reason_frame = pd.DataFrame(
        sorted(reason_counts.items(), key=lambda item: item[1], reverse=True),
        columns=["Reason code", "Occurrences"],
    ).set_index("Reason code")
    heading("Incident reason frequency", "Counted from flagged session rows only.")
    st.bar_chart(reason_frame.head(12))

    selected_index = st.selectbox(
        "Select packet",
        incidents.index.tolist(),
        format_func=lambda index: (
            f"{incidents.loc[index, 'packet_id']} — "
            f"{incidents.loc[index, 'scenario']} — "
            f"{incidents.loc[index, 'routing_outcome']}"
        ),
    )
    show_packet_detail(incidents.loc[selected_index])
    st.warning(
        "This view reports simulation outcomes. It does not release quarantine records."
    )


def render_authentication(frame: pd.DataFrame) -> None:
    heading(
        "Authentication and Device Trust",
        "Mandatory cryptographic checks. Behavioral ML cannot override a failure here.",
    )
    help_card(
        "Which checks are mandatory?",
        "Device identity and ACTIVE lifecycle, zone and hub match, credential ID, "
        "HMAC or ECDSA integrity, freshness, replay, attestation and provenance. "
        "X.509 validation runs when a certificate is present or required.",
    )

    st.dataframe(
        pd.DataFrame(
            [
                (
                    "HMAC-SHA256",
                    "Symmetric shared secret",
                    "C4TrustService.sign_packet / _verify_signature",
                    "Mandatory if credential algorithm is HMAC",
                ),
                (
                    "ECDSA-SHA256 P-256",
                    "Asymmetric public-key signature",
                    "sign_packet_ecdsa / _verify_signature",
                    "Mandatory if credential algorithm is ECDSA",
                ),
                (
                    "X.509 certificate",
                    "Identity binding and CA trust",
                    "X509CertificateValidator.validate",
                    "When certificate_pem is present",
                ),
                (
                    "Freshness",
                    "Packet age versus max_age_seconds=30",
                    "C4TrustService.assess",
                    "Mandatory",
                ),
                (
                    "Replay",
                    "Duplicate packet_id or non-increasing sequence",
                    "C4TrustService.assess",
                    "Mandatory",
                ),
            ],
            columns=["Control", "Simple meaning", "Code location", "When it applies"],
        ),
        width="stretch",
        hide_index=True,
    )

    if frame.empty:
        empty_workspace()
        return

    if "signature_algorithm" in frame:
        hmac_rows = frame[frame["signature_algorithm"] == "hmac-sha256"]
        ecdsa_rows = frame[frame["signature_algorithm"] == "ecdsa-sha256"]
    else:
        hmac_rows = frame.head(0)
        ecdsa_rows = frame.head(0)
    c1, c2, c3 = st.columns(3)
    c1.metric("HMAC assessments", len(hmac_rows))
    c2.metric("ECDSA assessments", len(ecdsa_rows))
    c3.metric(
        "Integrity invalid",
        int(frame["reason_codes"].apply(
            lambda reasons: any(code == "INTEGRITY_INVALID" for code in reasons)
        ).sum()),
    )
    show_results(frame)


def render_registry_and_policy() -> None:
    heading(
        "Device Registry and Policy",
        "In-memory demonstration registry created by C4DemoBackend. Secrets are not displayed.",
    )
    help_card(
        "Lifecycle states",
        "PROVISIONED: registered but not yet allowed to send. ACTIVE: authorized. "
        "SUSPENDED: temporarily blocked. REVOKED: permanently untrusted. "
        "RETIRED: decommissioned. Dashboard devices are registered then activated.",
    )

    backend = None
    try:
        backend = C4DemoBackend()
        devices = pd.DataFrame(backend.list_safe_devices())
    except Exception as exc:
        st.error(f"{type(exc).__name__}: {exc}")
        devices = pd.DataFrame()
    finally:
        if backend is not None:
            backend.close()

    if devices.empty:
        st.info("The demonstration registry could not be listed.")
    else:
        st.dataframe(devices, width="stretch", hide_index=True)
        st.caption(
            "secret_material_present is a boolean only. "
            "HMAC secrets and private keys are never shown."
        )

    heading(
        "Demonstration topology",
        "From shared/simulation/topology.py. These are simulated pipes, "
        "not physical sensors.",
    )
    topology = pd.DataFrame(
        [
            {
                "device_id": pipe.device_id,
                "zone_id": pipe.zone_id,
                "role": pipe.role.value,
            }
            for pipe in get_all_demo_pipes()
        ]
    )
    st.dataframe(topology, width="stretch", hide_index=True)

    heading("Security policy C4_POLICY_1.1", "Configured mechanisms in the current C4TrustService.")
    st.dataframe(
        pd.DataFrame(
            [
                ("Device identity and lifecycle", "DeviceRegistry.is_active"),
                ("Zone and hub binding", "Compare packet.zone_id and transport.gateway_id"),
                ("X.509 validation", "X509CertificateValidator"),
                ("Packet integrity", "HMAC-SHA256 or ECDSA-SHA256"),
                ("Freshness", "max_age_seconds = 30"),
                ("Replay protection", "packet_id and sequence cache"),
                ("Attestation / provenance", "Demo evidence verifiers in C4DemoBackend"),
                ("Behavioral assessment", "Random Forest anomaly score, threshold 0.70"),
                ("Routing", "C4TelemetryGate"),
            ],
            columns=["Control", "Configured mechanism"],
        ),
        width="stretch",
        hide_index=True,
    )


def render_quarantine_viewer() -> None:
    """Render the quarantine file viewer section."""
    quarantine_dir = Path(__file__).resolve().parents[3] / "quarantine" / "c4"

    if not quarantine_dir.exists():
        st.warning(f"Quarantine directory not found: {quarantine_dir}")
        return

    quarantine_files = list(quarantine_dir.glob("*.json"))

    if not quarantine_files:
        st.info("No quarantine files found in quarantine/c4/")
        return

    st.caption(f"Found {len(quarantine_files)} quarantine file(s)")

    # Load all quarantine records
    records = []
    for file_path in sorted(quarantine_files):
        try:
            with file_path.open(encoding="utf-8") as f:
                record = json.load(f)
                records.append(record)
        except Exception as e:
            st.error(f"Error reading {file_path.name}: {e}")

    if not records:
        st.error("Could not load any quarantine records")
        return

    # Create summary dataframe
    summary_data = []
    for record in records:
        summary_data.append({
            "quarantine_id": record.get("quarantine_id"),
            "packet_id": record.get("packet_id"),
            "device_id": record.get("device_id"),
            "trust_label": record.get("trust_label"),
            "routing_outcome": record.get("routing_outcome"),
            "quarantine_reason": record.get("quarantine_reason"),
            "released": "Yes" if record.get("released") else "No",
            "quarantined_at": record.get("quarantined_at"),
        })

    summary_df = pd.DataFrame(summary_data)

    # Show summary table
    st.subheader("Quarantine Summary")
    st.dataframe(
        summary_df,
        width="stretch",
        hide_index=True,
        height=300,
    )

    # Detailed view
    st.subheader("Quarantine Record Details")
    selected_id = st.selectbox(
        "Select quarantine record to view details",
        summary_df["quarantine_id"].tolist(),
        format_func=lambda qid: f"{qid} - {summary_df[summary_df['quarantine_id'] == qid]['packet_id'].iloc[0]}",
    )

    selected_record = next((r for r in records if r.get("quarantine_id") == selected_id), None)

    if selected_record:
        col1, col2, col3 = st.columns(3)
        col1.metric("Quarantine ID", selected_record.get("quarantine_id"))
        col2.metric("Packet ID", selected_record.get("packet_id"))
        col3.metric("Device ID", selected_record.get("device_id"))

        col4, col5, col6 = st.columns(3)
        col4.metric("Trust Label", selected_record.get("trust_label"))
        col5.metric("Routing Outcome", selected_record.get("routing_outcome"))
        col6.metric("Released", "Yes" if selected_record.get("released") else "No")

        st.write("**Reason Codes**")
        reason_codes = selected_record.get("reason_codes", [])
        if reason_codes:
            for code in reason_codes:
                st.code(code, language="text")
        else:
            st.caption("No reason codes")

        st.write("**Quarantine Reason**")
        st.code(selected_record.get("quarantine_reason"), language="text")

        st.write("**Packet Data**")
        packet_data = selected_record.get("packet_data", {})
        if packet_data:
            st.json(packet_data)
        else:
            st.caption("No packet data")

        if selected_record.get("released"):
            st.write("**Release Information**")
            st.write({
                "released_at": selected_record.get("released_at"),
                "release_reason": selected_record.get("release_reason"),
                "reviewed_by": selected_record.get("reviewed_by"),
            })

        st.write("**Assessment**")
        assessment = selected_record.get("assessment")
        if assessment:
            st.json(assessment)
        else:
            st.caption("No assessment data")

        # Statistics
        st.divider()
        st.subheader("Quarantine Statistics")

        total = len(records)
        released_count = sum(1 for r in records if r.get("released"))
        unreleased_count = total - released_count

        stat1, stat2, stat3 = st.columns(3)
        stat1.metric("Total Records", total)
        stat2.metric("Released", released_count)
        stat3.metric("Unreleased", unreleased_count)

        # Reason distribution
        reason_counts = {}
        for record in records:
            reason = record.get("quarantine_reason", "UNKNOWN")
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        if reason_counts:
            st.write("**Quarantine Reason Distribution**")
            reason_df = pd.DataFrame(
                [{"Reason": k, "Count": v} for k, v in reason_counts.items()]
            )
            st.bar_chart(reason_df.set_index("Reason"))


def render_storage_and_diagnostics() -> None:
    heading(
        "Data Storage and System Diagnostics",
        "Where each data category lives in this repository. Passwords and secrets are not shown.",
    )
    diagnostics = C4DemoBackend.system_diagnostics()
    database = diagnostics["database"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Runtime model file", "FOUND" if diagnostics["model_available"] else "MISSING")
    m2.metric("PostgreSQL", "REACHABLE" if database.get("reachable") else "NOT REACHABLE")
    m3.metric(
        "telemetry_packets rows",
        unavailable(database.get("telemetry_packets")),
    )

    st.write("**Model artifact**")
    st.code(diagnostics["model_path"], language="text")
    st.write("**Configured database**")
    st.write(
        {
            "host": database.get("host"),
            "port": database.get("port"),
            "name": database.get("name"),
            "user": database.get("user"),
            "reachable": database.get("reachable"),
        }
    )
    if database.get("error"):
        st.warning(database["error"])

    st.subheader("Storage inventory")
    st.dataframe(
        pd.DataFrame(
            [
                (
                    "Dashboard assessments",
                    "st.session_state.c4_results",
                    "Scenario buttons",
                    "This UI",
                    "No",
                ),
                (
                    "Dashboard quarantine files",
                    "TemporaryDirectory inside C4DemoBackend",
                    "C4TelemetryGate.process()",
                    "Deleted by backend.close()",
                    "No",
                ),
                (
                    "Default C4 quarantine JSON",
                    "quarantine/c4/",
                    "QuarantineManager when no temp dir is supplied",
                    "JSON files",
                    "Yes, on disk",
                ),
                (
                    "Offline C4 dataset",
                    "experiments/c4/data/*.csv",
                    "Preparation and split scripts",
                    "pandas / ML Explorer",
                    "Yes",
                ),
                (
                    "Saved models",
                    "experiments/c4/models/*.joblib",
                    "Training scripts",
                    "TrainedModel.load",
                    "Yes",
                ),
                (
                    "Demo registry",
                    "In-memory DeviceRegistry",
                    "C4DemoBackend.__init__",
                    "list_safe_devices()",
                    "No",
                ),
                (
                    "PostgreSQL telemetry",
                    "geonex.telemetry_packets / sensor_observations",
                    "apps/ingestion/persistence.py via load_demo_simulation.py",
                    "SQLAlchemy",
                    "Yes, if the database is running",
                ),
            ],
            columns=[
                "Item",
                "Exact source or path",
                "How data gets there",
                "How it is read",
                "Survives restart?",
            ],
        ),
        width="stretch",
        hide_index=True,
    )
    st.info(
        "A packet count in PostgreSQL does not mean this dashboard is displaying those rows. "
        "The Command Center only counts session assessments."
    )

    st.divider()
    st.subheader("Quarantine File Viewer")
    help_card(
        "Quarantine records",
        "These are JSON files stored in quarantine/c4/ that contain detailed information "
        "about quarantined telemetry packets, including trust labels, reason codes, and packet data."
    )
    render_quarantine_viewer()


def render_model_policy() -> None:
    heading(
        "Model & Security Policy",
        "Compact reference for the runtime demonstration. "
        "Use ML Model Explorer for artifact inspection.",
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Runtime model", "Random Forest")
    m2.metric("Expected features", "18")
    m3.metric("Security policy", "C4_POLICY_1.1")
    st.info(
        "Behavioral inference cannot override a failed mandatory security check. "
        "This dashboard uses simulation evidence verifiers; it is not a production TPM deployment."
    )
