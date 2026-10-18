import pandas as pd
import streamlit as st

from apps.c4_frontend.c4_backend import C4DemoBackend
from apps.c4_frontend.ml_explorer_ui import render_ml_model_explorer
from apps.c4_frontend.styles import APP_CSS
from apps.c4_frontend.views import (
    render_authentication,
    render_command_center,
    render_how_c4_works,
    render_model_policy,
    render_registry_and_policy,
    render_storage_and_diagnostics,
    render_telemetry_explorer,
    render_threat_investigation,
)

st.set_page_config(
    page_title="GeoNex | C4 Security Operations",
    page_icon="C4",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(APP_CSS, unsafe_allow_html=True)

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
            result["scenario_key"] = scenario
            result["run_number"] = run_number

        st.session_state.c4_run_count = run_number
        st.session_state.c4_results.extend(results)
        st.session_state.c4_notice = (
            f"{len(results)} assessment result(s) recorded for {scenario}."
        )
        st.session_state.pop("c4_error", None)

    except Exception as exc:
        st.session_state.c4_error = f"{type(exc).__name__}: {exc}"

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


PAGES = [
    "How C4 Works",
    "Command Center",
    "Telemetry Explorer",
    "Threat Investigation",
    "Authentication & Device Trust",
    "ML Model Explorer",
    "Device Registry & Policy",
    "Data Storage & Diagnostics",
    "Model & Policy",
]

st.sidebar.markdown("## GEONEX")
st.sidebar.caption("C4 TRUSTED TELEMETRY")
st.sidebar.divider()

page = st.sidebar.radio("WORKSPACE", PAGES)

st.sidebar.divider()
st.sidebar.markdown("**HMAC SCENARIOS**")
st.sidebar.caption("Synthetic packets signed with a demo HMAC secret.")

if st.sidebar.button("Run Valid Telemetry (HMAC)", width="stretch"):
    run_scenario("valid_hmac")
    st.rerun()

if st.sidebar.button("Test Tampered (HMAC)", width="stretch"):
    run_scenario("tampered_hmac")
    st.rerun()

if st.sidebar.button("Test Replay Attack (HMAC)", width="stretch"):
    run_scenario("replay_hmac")
    st.rerun()

st.sidebar.markdown("**X.509 & ECDSA SCENARIOS**")
st.sidebar.caption("Synthetic packets signed with an in-memory P-256 key.")

if st.sidebar.button("Run Valid X.509 + ECDSA", width="stretch"):
    run_scenario("valid_ecdsa")
    st.rerun()

if st.sidebar.button("Test Tampered (ECDSA)", width="stretch"):
    run_scenario("tampered_ecdsa")
    st.rerun()

if st.sidebar.button("Test Expired Certificate", width="stretch"):
    run_scenario("expired_x509")
    st.rerun()

if st.sidebar.button("Test Untrusted CA", width="stretch"):
    run_scenario("untrusted_ca_x509")
    st.rerun()

if st.sidebar.button("Test Identity Mismatch Cert", width="stretch"):
    run_scenario("mismatched_identity_x509")
    st.rerun()

if st.sidebar.button("Test Revoked Certificate", width="stretch"):
    run_scenario("revoked_x509")
    st.rerun()

if st.sidebar.button("Test Alg Fallback Rejection", width="stretch"):
    run_scenario("fallback_rejection")
    st.rerun()

st.sidebar.divider()

if st.sidebar.button("Clear Session Results", width="stretch"):
    st.session_state.c4_results = []
    st.session_state.c4_run_count = 0
    st.session_state.pop("c4_notice", None)
    st.session_state.pop("c4_error", None)
    st.rerun()

st.sidebar.divider()
st.sidebar.caption("IT4010 | GeoNex Research Project")
st.sidebar.warning(
    "Simulation environment. Test credentials are not production authentication. "
    "Session results are in memory only."
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
        <div class="hero-title">Trusted Telemetry Operations</div>
        <div class="hero-subtitle">
            Research demonstration of device authentication, X.509 and
            ECDSA/HMAC integrity, freshness and replay protection, and
            behavioral ML. Dashboard packets are synthetic. They are not
            live landslide-sensor telemetry.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if page == "How C4 Works":
    render_how_c4_works()
elif page == "Command Center":
    render_command_center(frame)
elif page == "Telemetry Explorer":
    render_telemetry_explorer(frame)
elif page == "Threat Investigation":
    render_threat_investigation(frame)
elif page == "Authentication & Device Trust":
    render_authentication(frame)
elif page == "ML Model Explorer":
    render_ml_model_explorer()
elif page == "Device Registry & Policy":
    render_registry_and_policy()
elif page == "Data Storage & Diagnostics":
    render_storage_and_diagnostics()
elif page == "Model & Policy":
    render_model_policy()

st.divider()
st.caption(
    "GeoNex C4 research simulation dashboard | "
    "Session results are in memory and are not persistent audit storage."
)
