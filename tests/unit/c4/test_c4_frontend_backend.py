from apps.c4_frontend.c4_backend import C4DemoBackend


def test_valid_hmac_result_is_simulated_and_not_database_backed():
    backend = C4DemoBackend()
    try:
        rows = backend.run_simulation("valid_hmac")
    finally:
        backend.close()

    assert rows
    row = rows[0]
    assert row["data_origin"] == "FRONTEND_SIMULATION"
    assert row["source_origin"] == "SIMULATED"
    assert row["persisted_to_database"] is False
    assert row["storage"] == "streamlit_session_state"
    assert "secret" not in row
    assert "certificate_pem" not in row
    assert isinstance(row["measurements"], list)
    assert row["packet_id"]
    assert row["assessment_id"].startswith("C4A_")


def test_safe_device_list_omits_secret_material():
    backend = C4DemoBackend()
    try:
        devices = backend.list_safe_devices()
    finally:
        backend.close()

    assert devices
    first = devices[0]
    assert "secret" not in first
    assert "certificate_pem" not in first
    assert "public_key_pem" not in first
    assert first["secret_material_present"] is True
    assert first["lifecycle_state"] == "ACTIVE"


def test_tampered_hmac_fails_mandatory_security():
    backend = C4DemoBackend()
    try:
        rows = backend.run_simulation("tampered_hmac")
    finally:
        backend.close()

    row = rows[0]
    assert row["mandatory_security_pass"] is False
    assert row["trust_label"] == "UNTRUSTED"
    assert row["eligible_for_c1"] is False
    assert "INTEGRITY_INVALID" in row["reason_codes"]


def test_valid_ecdsa_is_trusted_and_accepted():
    backend = C4DemoBackend()
    try:
        rows = backend.run_simulation("valid_ecdsa")
    finally:
        backend.close()

    assert len(rows) == 1
    row = rows[0]
    assert row["trust_label"] == "TRUSTED"
    assert row["routing_outcome"] == "ACCEPT"
    assert row["mandatory_security_pass"] is True
    assert row["eligible_for_c1"] is True
    assert "CERTIFICATE_VALID" in row["reason_codes"]
    assert "INTEGRITY_VALID" in row["reason_codes"]
    assert "CERTIFICATE_NOT_YET_VALID" not in row["reason_codes"]


def test_expired_x509_still_fails_for_expiry_not_clock_skew():
    backend = C4DemoBackend()
    try:
        rows = backend.run_simulation("expired_x509")
    finally:
        backend.close()

    row = rows[0]
    assert row["trust_label"] == "UNTRUSTED"
    assert "CERTIFICATE_EXPIRED" in row["reason_codes"]
    assert "CERTIFICATE_NOT_YET_VALID" not in row["reason_codes"]
