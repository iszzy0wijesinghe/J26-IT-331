# C4 Security Validation and Cryptographic Verification Guide

## 1. Purpose of Component 4 (C4)

Component 4 (C4) — **Trusted Telemetry Provenance and Device Attestation** — is the foundational security boundary in the GeoNex Smart Landslide Early-Warning System architecture. Its responsibility is to ensure that incoming IoT telemetry originates from authorized, active sensor devices, has not been tampered with in transit, is not replayed or delayed beyond allowable timing bounds, complies with approved firmware and configuration states, and exhibits normal operational behavior.

C4 acts as a strict admission gate ahead of downstream processing:
- Telemetry that passes all mandatory security checks and shows normal behavior is labeled **TRUSTED** and routed to **ACCEPT** (forwarded to C1 Geological Analysis).
- Telemetry showing behavioral anomalies while passing deterministic checks is labeled **SUSPICIOUS** and routed to **QUARANTINE**.
- Telemetry with missing or unverifiable security evidence is labeled **UNKNOWN** and routed to **SECURITY_REVIEW** for forensic audit.
- Telemetry that fails any mandatory cryptographic, identity, lifecycle, freshness, replay, or approval check is labeled **UNTRUSTED** and routed to **REJECT** (and quarantined for security audit).

```
                      [ Raw Telemetry Packet ]
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │  Mandatory Deterministic Gate (C4)   │
               │  - Device Identity & Lifecycle       │
               │  - Signature Verification (HMAC/ECC) │
               │  - Timestamp Freshness & Replay      │
               │  - Gateway & Zone Binding            │
               │  - Firmware & Config Hash Approval   │
               └──────────────────┬───────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
             FAIL │                               │ PASS
                  ▼                               ▼
       [ UNTRUSTED / REJECT ]         ┌─────────────────────────┐
       [ UNKNOWN / SEC_REVIEW ]       │ Behavioral ML Inference │
       (Cannot be overridden by ML)   └───────────┬─────────────┘
                                                  │
                                      ┌───────────┴───────────┐
                                      │ Anomalous             │ Normal
                                      ▼                       ▼
                           [ SUSPICIOUS / QUARANTINE ]  [ TRUSTED / ACCEPT ]
```

---

## 2. Signature Algorithms: HMAC-SHA256 vs. ECDSA-SHA256

GeoNex supports two cryptographic signing algorithms to balance compute/bandwidth constraints on field sensors with asymmetric non-repudiation:

| Attribute | HMAC-SHA256 (`hmac-sha256`) | ECDSA-SHA256 (`ecdsa-sha256`) |
| :--- | :--- | :--- |
| **Cryptography Type** | Symmetric Message Authentication Code | Asymmetric Public-Key Digital Signature |
| **Curve / Standard** | RFC 2104 / SHA-256 | NIST P-256 (`SECP256R1`) / ANSI X9.62 / RFC 5480 |
| **Key Architecture** | Shared secret between device and ingestion service | Private key on device; public key in registry |
| **Key Exposure Impact** | Compromise of server secret enables signature forgery | Server stores only public keys; private keys remain isolated on devices |
| **Non-Repudiation** | No (both parties hold symmetric secret) | Yes (only device holding private key can generate valid signature) |
| **Signature Size** | 32 bytes (64 hex characters) | 64–72 bytes ASN.1 DER (variable hex characters) |
| **Primary Target** | Low-power microcontroller nodes with constrained cycles | High-priority primary sensor nodes or secure hardware elements |

### Algorithm Isolation and No Silent Fallback
The `DeviceCredential` model defines `signature_algorithm: str = "hmac-sha256"`. When configured for `ecdsa-sha256`, the trust service executes exclusively asymmetric ECDSA verification using `cryptography.hazmat.primitives.asymmetric.ec`. Under no circumstances does an ECDSA credential fall back to HMAC-SHA256, even if a shared secret is present or the public key is missing.

---

## 3. How Public-Key Verification Works

ECDSA-SHA256 verification in `C4TrustService` operates deterministically as follows:

1. **Canonical Serialization**:
   The telemetry packet is serialized to canonical JSON bytes using `C4TrustService._canonical_packet(packet)`. Keys are sorted (`sort_keys=True`) with compact separators (`separators=(',', ':')`) and UTF-8 encoding.
2. **Public Key Retrieval and Validation**:
   The registered `credential.public_key_pem` is decoded. The public key is loaded via `serialization.load_pem_public_key()`. The implementation verifies that the loaded object is an instance of `ec.EllipticCurvePublicKey`. If the PEM is invalid, malformed, or of an unsupported algorithm (e.g., RSA), verification fails closed as unverifiable.
3. **Signature Decoding**:
   The incoming signature string is converted from hexadecimal representation into ASN.1 DER-encoded bytes via `bytes.fromhex(signature)`. If the string is malformed hex, it is caught safely and treated as invalid.
4. **Cryptographic Verification**:
   The public key verifies the signature over the canonical packet bytes:
   $$\text{Verify}_{PK}(\text{Canonical}(P), \text{Sig}_{\text{DER}})$$
   If valid, `INTEGRITY_VALID` is recorded. If an `InvalidSignature` exception is raised, verification returns `False` and `INTEGRITY_INVALID` is recorded.

---

## 4. Handling Invalid vs. Unverifiable Evidence

A strict architectural distinction is maintained between **cryptographically invalid telemetry** and **missing/unverifiable credentials**:

| Condition | Failure Type | Trust Label | Routing Outcome | Reason Code |
| :--- | :--- | :--- | :--- | :--- |
| Telemetry payload altered after signing | Cryptographic Mismatch | `UNTRUSTED` | `REJECT` | `INTEGRITY_INVALID` |
| Signature generated with wrong key | Cryptographic Mismatch | `UNTRUSTED` | `REJECT` | `INTEGRITY_INVALID` |
| Malformed signature data (non-hex, bad DER) | Cryptographic Mismatch | `UNTRUSTED` | `REJECT` | `INTEGRITY_INVALID` |
| Device unregistered | Identity Failure | `UNTRUSTED` | `REJECT` | `DEVICE_UNKNOWN` |
| Device suspended, revoked, or retired | Lifecycle Inactive | `UNTRUSTED` | `REJECT` | `DEVICE_NOT_ACTIVE` |
| Credential expired | Credential Validity | `UNTRUSTED` | `REJECT` | `CREDENTIAL_EXPIRED` |
| Credential `issued_at` in the future | Credential Validity | `UNTRUSTED` | `REJECT` | `CREDENTIAL_NOT_YET_VALID` |
| Packet observed_at > now + 5s | Freshness Invalidation | `UNTRUSTED` | `REJECT` | `TIMESTAMP_IN_FUTURE` |
| Packet observed_at < now - 30s | Freshness Invalidation | `UNTRUSTED` | `REJECT` | `FRESHNESS_EXPIRED` |
| Duplicate `(device_id, packet_id)` seen | Replay Detection | `UNTRUSTED` | `REJECT` | `REPLAY_DETECTED` |
| Sequence number $\le$ last recorded | Sequence Enforcement | `UNTRUSTED` | `REJECT` | `SEQUENCE_REPLAY_DETECTED` |
| Firmware hash $\ne$ registered approval | Approval Failure | `UNTRUSTED` | `REJECT` | `FIRMWARE_UNAPPROVED` |
| Config hash $\ne$ registered approval | Approval Failure | `UNTRUSTED` | `REJECT` | `CONFIG_MISMATCH` |
| Gateway/Hub ID $\ne$ registered hub | Topology Mismatch | `UNTRUSTED` | `REJECT` | `HUB_MISMATCH` |
| Zone ID $\ne$ registered zone | Topology Mismatch | `UNTRUSTED` | `REJECT` | `ZONE_MISMATCH` |
| Signature string omitted (`None` or `""`) | Missing Evidence | `UNKNOWN` | `SECURITY_REVIEW` | `SIGNATURE_MISSING` |
| Credential not configured on registered device | Missing Evidence | `UNKNOWN` | `SECURITY_REVIEW` | `CREDENTIAL_NOT_CONFIGURED` |
| Public key PEM missing or malformed | Unverifiable Key | `UNKNOWN` | `SECURITY_REVIEW` | `SIGNATURE_UNVERIFIABLE` |
| Unknown signature algorithm configured | Unverifiable Algo | `UNKNOWN` | `SECURITY_REVIEW` | `SIGNATURE_UNVERIFIABLE` |
| Missing sequence or boot ID when required | Missing Evidence | `UNKNOWN` | `SECURITY_REVIEW` | `SEQUENCE_EVIDENCE_MISSING` |
| Missing gateway ID in transport | Missing Evidence | `UNKNOWN` | `SECURITY_REVIEW` | `HUB_ID_MISSING` |
| Naive / unparseable credential dates | Unverifiable Evidence | `UNKNOWN` | `SECURITY_REVIEW` | `CREDENTIAL_ISSUED_AT_INVALID` |

Neither `UNTRUSTED` nor `UNKNOWN` packets can ever be routed to `ACCEPT`.

---

## 5. Device Lifecycle Enforcement

The `DeviceRegistry` enforces explicit lifecycle states defined in `DeviceLifecycleState`:
- `PROVISIONED`: Configured but not yet in active operation. Telemetry is rejected (`DEVICE_NOT_ACTIVE`).
- `ACTIVE`: Fully operational. Authorized to submit telemetry.
- `SUSPENDED`: Temporarily deactivated (e.g., during field maintenance). Telemetry is rejected (`DEVICE_NOT_ACTIVE`).
- `REVOKED`: Permanently decommissioned due to security incident or key compromise. Telemetry is rejected (`DEVICE_NOT_ACTIVE`).
- `RETIRED`: Gracefully decommissioned end-of-life hardware. Telemetry is rejected (`DEVICE_NOT_ACTIVE`).

Only devices in the `ACTIVE` state pass identity verification.

---

## 6. Freshness, Replay Protection, and Authorized Recovery

1. **Timestamp Freshness**:
   Packets must have an observation timestamp within $[T_{\text{now}} - 30\text{s},\, T_{\text{now}} + 5\text{s}]$. Future-dated packets exceed clock skew limits and are rejected with `TIMESTAMP_IN_FUTURE`. Old packets are rejected with `FRESHNESS_EXPIRED`.
2. **Replay Detection**:
   Every packet identifier is tracked in memory per device: `(device_id, packet_id)`. Duplicates trigger `REPLAY_DETECTED`.
3. **Monotonic Sequence Enforcement**:
   For each `(device_id, boot_id)`, sequence numbers must strictly increase ($S_{k+1} > S_k$). Regressive or repeated sequence numbers trigger `SEQUENCE_REPLAY_DETECTED`.
4. **Authorized Recovery Bypass**:
   Under component C2 (automated recovery), backlogged packets replayed during link restoration are authorized via a signed `RecoveryContext` specifying `recovery_request_id`, device identity, and a bounded time window $[T_{\text{start}}, T_{\text{end}}]$. Packets matching an active recovery context receive `AUTHORIZED_REPLAY_FRESHNESS_EXCEPTION` and are exempted from standard replay rejection.

---

## 7. Firmware and Configuration Approval

Field devices report non-secret hardware integrity hashes in `SecurityMetadata`:
- `firmware_hash`: SHA-256 digest of active firmware binary.
- `config_hash`: SHA-256 digest of operational calibration parameters.

When `require_firmware_approval=True` or `require_config_approval=True` is enabled:
- If the device record lacks approval metadata, `FIRMWARE_APPROVAL_MISSING` or `CONFIG_APPROVAL_MISSING` routes to `SECURITY_REVIEW`.
- If the packet lacks hash evidence, `FIRMWARE_EVIDENCE_MISSING` or `CONFIG_EVIDENCE_MISSING` routes to `SECURITY_REVIEW`.
- If the packet hash contradicts the registry's approved hash, `FIRMWARE_UNAPPROVED` or `CONFIG_MISMATCH` immediately rejects the packet as `UNTRUSTED`.

---

## 8. Behavioral ML Scoring and Immutability of Security Gates

C4 integrates behavioral machine learning models (e.g., Random Forest, Logistic Regression, Isolation Forest) trained on transmission intervals, reception delay, radio link quality (RSSI, SNR, deviation), retry counts, packet sizes, battery voltage, and rolling statistics.

### Why ML Cannot Override Cryptographic Failures
1. **Mathematical Authority vs. Statistical Heuristics**: Cryptographic signatures and monotonic counters provide mathematical certainty regarding message integrity and freshness. A statistical machine learning model provides probabilistic inference regarding anomaly likelihood.
2. **Adversarial Resilience**: If an ML anomaly score could override a cryptographic mismatch, an attacker could spoof telemetry with valid physical properties (e.g., plausible battery voltage and standard 30-second interval) to inject forged landslide measurements.
3. **Contractual Pydantic Enforcement**: The contract model `C4TrustAssessment` strictly asserts:
   ```python
   if not self.mandatory_security_pass and self.trust_label in {C4TrustLabel.TRUSTED, C4TrustLabel.SUSPICIOUS}:
       raise ValueError("A packet cannot be TRUSTED or SUSPICIOUS when mandatory security fails")
   ```
4. **Architectural Gating**: In `C4TrustService.assess()`, behavioral inference is evaluated *only* after `failures` and `security_unknowns` are verified to be empty. If mandatory checks fail, `trust_label` is immediately `UNTRUSTED` or `UNKNOWN` and the routing outcome is forced to `REJECT` or `SECURITY_REVIEW`.

---

## 9. Test Execution and Verification Commands

All security checks and automated regression suites can be executed with standard commands inside the project's environment:

### Ruff Linter Check
```bash
python -m ruff check components/c4_trust tests/security
```

### Targeted Security Suite
```bash
python -m pytest tests/security/test_c4_ecdsa_signatures.py tests/security/test_c4_trust_service.py tests/security/test_c4_device_registry.py -q
```

### Integration Gate Suite
```bash
python -m pytest tests/integration/test_c4_simulation_gate.py tests/integration/test_telemetry_persistence.py -q
```

### Full Repository Test Suite
```bash
python -m pytest tests/ -q
```

### Git Diff Whitespace & Hygiene Check
```bash
git diff --check
```

---

## 10. Actual Measured Test Results

Execution logs from the validation runs on the `feature/c4` branch:

- **Targeted Security Tests**:
  - `tests/security/test_c4_ecdsa_signatures.py`: **26 passed** (valid signatures, tampered payloads, key mismatch, malformed PEM, invalid hex/DER, algorithm fallback prevention, fresh key pairs, ML override immunity, registry lifecycle).
  - `tests/security/test_c4_trust_service.py`: **32 passed** (replay detection, sequence checking, revoked/retired states, firmware/config hash mismatch, hub validation, credential validities, fail-closed behavioral scorers).
  - `tests/security/test_c4_device_registry.py`: **20 passed** (device registration, lifecycle transitions, state filtering, credential updates).
  - **Total Targeted Security**: **78 passed in 0.36s**.
- **Full Test Suite**: **251 passed in 5.67s** across all test categories (contracts, security, unit, integration, simulation).
- **Ruff Linting**: **All checks passed** with zero errors or warnings.
- **Git Hygiene**: `git diff --check` exited cleanly with no trailing whitespace or merge conflict markers.

---

## 11. Implemented Features vs. Planned Future Work

### Implemented Features (Verified in Code & Tests)
- Canonical telemetry serialization for deterministic digest calculation.
- HMAC-SHA256 signing and constant-time verification.
- ECDSA-SHA256 (NIST P-256) signing and public-key verification via `cryptography`.
- Complete public-key validation with rejection of missing, malformed, or non-EC PEM keys.
- Safe handling of malformed hex and corrupt DER signatures without unhandled exceptions.
- Fail-closed isolation preventing HMAC fallback on ECDSA-configured devices.
- Comprehensive device lifecycle states (`PROVISIONED`, `ACTIVE`, `SUSPENDED`, `REVOKED`, `RETIRED`).
- Windowed timestamp freshness and future-timestamp tolerance bounds.
- In-memory duplicate packet and monotonic sequence replay protection.
- Authorized recovery replay context mechanism for network restoration.
- Firmware hash and configuration hash approval enforcement.
- Hub/Gateway ID and Zone ID topology validation.
- Behavioral anomaly score integration with quarantine routing.
- Architectural and contractual prohibition of ML overriding mandatory security failures.
- Ingestion telemetry persistence compatibility with behavioral metadata.

### Planned Features / Current Limitations (Future Work)
- **Certificate-Chain Validation**: Current implementation uses pinned subject public keys (`SubjectPublicKeyInfo` PEM); X.509 PKI certificate chain hierarchy and CRL/OCSP validation are planned for enterprise gateway rollouts.
- **Hardware-Backed Key Storage**: In the current software simulation, private keys are generated in test memory; integration with hardware secure elements (e.g., ATECC608A / TPM 2.0 / ARM TrustZone) on physical nodes is planned for field deployment.
- **Persistent Anti-Replay Store**: Replay caches and sequence histories are currently thread-safe in-memory collections; distributed Redis/PostgreSQL sequence tracking will be used in multi-instance clustering.
- **Cryptographic Attestation Verification**: Hardware attestation tokens are verified against simulated validators; full TPM Quote validation with remote quote verification will be integrated with hardware deployment.

---

## 12. Viva Examination Guide

### Q1: What does Component 4 (C4) do in the GeoNex system?
> **Answer**: C4 is the trust admission gate for all incoming landslide telemetry. It performs deterministic security assessment (verifying sensor identity, cryptographic integrity, timestamp freshness, replay protection, gateway binding, and firmware/config approvals) and pairs this with behavioral ML anomaly scoring. Packets that pass are forwarded to the C1 geological analysis component; failing or suspicious packets are quarantined or rejected.

### Q2: Why are both HMAC-SHA256 and ECDSA-SHA256 supported?
> **Answer**: GeoNex accommodates heterogeneous IoT field hardware. HMAC-SHA256 provides efficient, low-overhead symmetric authentication suited for battery-powered, resource-constrained sensor microcontrollers. ECDSA-SHA256 provides asymmetric public-key cryptography with non-repudiation for high-priority primary sensor nodes and gateways. The service enforces strict algorithm isolation so ECDSA credentials never fall back to HMAC.

### Q3: What happens when telemetry is tampered with in transit?
> **Answer**: Even a single bit modification to measurements, sensor IDs, zone IDs, or message types changes the canonical JSON digest. The signature verification fails (`InvalidSignature`), resulting in `INTEGRITY_INVALID`. The packet is assigned the `UNTRUSTED` trust label, given a trust score of 0.0, routed to `REJECT`, and quarantined with reason `SECURITY_FAILURE`. It is completely blocked from reaching downstream geological models.

### Q4: Why can machine learning not override cryptographic integrity failures?
> **Answer**: Cryptography provides mathematical proof of integrity, whereas machine learning provides probabilistic anomaly detection. If an ML model could override a signature mismatch, an attacker could easily bypass authentication by transmitting sensor values that mimic normal conditions. C4 enforces a strict hierarchical security model: ML scoring is only evaluated after all deterministic checks pass.

### Q5: What do the automated tests demonstrate?
> **Answer**: The test suite substantiates end-to-end security compliance across 251 tests (including 78 dedicated security tests). It proves that valid HMAC and ECDSA signatures are accepted; tampered, wrong-key, malformed, or replayed packets are rejected; missing credentials or unapproved configurations are quarantined for security review; ML scores cannot overturn security rejections; and runtime simulation pipelines cleanly quarantine invalid data without persisting secrets.
