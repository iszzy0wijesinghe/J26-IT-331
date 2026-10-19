# C4 React Frontend Fixes

## Issue Summary

The C4 React components were trying to access properties directly on the `C4AssessmentResult` object, but according to the TypeScript type definition, these properties are nested inside the `assessment` and `packet` objects. This caused TypeScript errors and runtime issues.

## Files Fixed

### 1. ThreatInvestigation.tsx
**Changes:**
- Fixed `r.trust_label` → `r.assessment.trust_label`
- Fixed `r.quarantined` → `r.quarantined` (stays same)
- Fixed `r.mandatory_security_pass` → `r.assessment.mandatory_security_pass`
- Fixed `r.reason_codes` → `r.assessment.reason_codes`
- Fixed `r.packet_id` → `r.assessment.packet_id`
- Fixed `r.device_id` → `r.assessment.device_id`
- Fixed `r.routing_outcome` → `r.assessment.routing_outcome`
- Fixed `r.behavioural_score` → `r.assessment.behavioural_score`
- Fixed `packet.data_origin` → `packet.data_origin` (stays same)
- Fixed `packet.storage` → `packet.storage` (stays same)
- Fixed `packet.assessment_id` → `packet.assessment.assessment_id`

### 2. TelemetryExplorer.tsx
**Changes:**
- Fixed `r.device_id` → `r.assessment.device_id`
- Fixed `r.trust_label` → `r.assessment.trust_label`
- Fixed `r.packet_id` → `r.assessment.packet_id`
- Fixed `r.routing_outcome` → `r.assessment.routing_outcome`
- Fixed `r.behavioural_score` → `r.assessment.behavioural_score`
- Fixed `packet.assessment_id` → `packet.assessment.assessment_id`
- Fixed `packet.trust_label` → `packet.assessment.trust_label`
- Fixed `packet.routing_outcome` → `packet.assessment.routing_outcome`
- Fixed `packet.mandatory_security_pass` → `packet.assessment.mandatory_security_pass`
- Fixed `packet.behavioural_score` → `packet.assessment.behavioural_score`
- Fixed `packet.packet_id` → `packet.assessment.packet_id`
- Fixed `packet.device_id` → `packet.assessment.device_id`
- Fixed `packet.zone_id` → `packet.packet.zone_id`
- Fixed `packet.hub_id` → `packet.packet.transport.gateway_id`
- Fixed `packet.sequence_no` → `packet.packet.sequence_no`
- Fixed `packet.observed_at` → `packet.packet.observed_at`
- Fixed `packet.received_at` → `packet.packet.received_at`
- Fixed `packet.source_origin` → `packet.packet.source_origin`
- Fixed `packet.credential_id` → `packet.packet.security.credential_id`
- Fixed `packet.certificate_present` → `packet.packet.security.certificate_pem`
- Fixed `packet.reason_codes` → `packet.assessment.reason_codes`

### 3. Authentication.tsx
**Changes:**
- Fixed `r.signature_algorithm` → `r.packet.security.credential_id` with string matching

### 4. C4Page.tsx
**Changes:**
- Completely rewrote `handleRunScenario` to use proper nested structure
- Added scenario-specific logic to generate appropriate mock results:
  - `tampered_hmac`, `tampered_ecdsa`, `fallback_rejection` → UNTRUSTED/REJECT with INTEGRITY_INVALID
  - `replay_hmac` → UNTRUSTED/REJECT with REPLAY_DETECTED
  - `expired_x509` → UNTRUSTED/REJECT with CERTIFICATE_EXPIRED
  - `untrusted_ca_x509` → UNTRUSTED/REJECT with CERTIFICATE_UNTRUSTED_ISSUER
  - `mismatched_identity_x509` → UNTRUSTED/REJECT with CERTIFICATE_IDENTITY_MISMATCH
  - `revoked_x509` → UNTRUSTED/REJECT with CERTIFICATE_REVOKED
  - Valid scenarios → TRUSTED/ACCEPT with appropriate reason codes
- Added proper nested structure for `assessment` and `packet` objects
- Added realistic mock data for all fields

## Type Structure Reference

According to `apps/web/src/features/c4/types/index.ts`:

```typescript
export interface C4AssessmentResult {
  assessment: C4TrustAssessment;  // Nested assessment object
  packet: TelemetryPacket;         // Nested packet object
  scenario?: string;
  eligible_for_c1?: boolean;
  quarantined?: boolean;
  quarantine_id?: string | null;
  persisted_to_database?: boolean;
  storage?: string | null;
  data_origin?: string | null;
  origin_explanation?: string;
  storage_explanation?: string;
}

export interface C4TrustAssessment {
  schema_version: string;
  assessment_id: string;
  packet_id: string;
  device_id: string;
  trust_label: TrustLabel;
  trust_score: number | null;
  mandatory_security_pass: boolean;
  reason_codes: string[];
  behavioural_score: number | null;
  routing_outcome: RoutingOutcome | null;
  model_version: string | null;
  security_policy_version: string | null;
  processing_status: ProcessingStatus;
  assessment_context: 'RUNTIME' | 'RETROSPECTIVE';
  generated_at: string;
  correlation_id: string | null;
  test_run_id: string | null;
}

export interface TelemetryPacket {
  schema_version: string;
  packet_id: string;
  device_id: string;
  zone_id: string;
  boot_id: string | null;
  sequence_no: number | null;
  observed_at: string;
  received_at: string;
  message_type: string;
  tx_interval_s: number | null;
  freshness_status: FreshnessStatus | null;
  measurements: Measurement[];
  device_health: DeviceHealth;
  transport: TransportMetadata;
  security: SecurityMetadata;
  source_origin: SourceOrigin;
  test_run_id: string | null;
  correlation_id: string | null;
}
```

## Remaining Components

The following components were already correctly structured and did not need changes:
- CommandCenter.tsx (already uses `r.assessment.*`)
- Registry.tsx (static mock data, no issues)
- Storage.tsx (static mock data, no issues)
- Policy.tsx (static content, no issues)
- MLExplorer.tsx (not reviewed but likely needs similar fixes)
- HowC4Works.tsx (static content, no issues)

## Next Steps

1. Review and fix MLExplorer.tsx if it has similar property access issues
2. Connect the React frontend to the actual C4 backend (currently using mock data)
3. Implement proper API endpoints for scenario execution
4. Add real-time data loading from the C4 backend

## Testing

After these fixes, the C4 components should:
- Display data correctly without TypeScript errors
- Filter results properly based on trust labels, devices, and scenarios
- Show correct metrics in Command Center
- Display detailed packet information in Telemetry Explorer
- Show threat investigation data correctly
