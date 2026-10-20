export type TrustLabel = 'TRUSTED' | 'UNTRUSTED' | 'SUSPICIOUS' | 'UNKNOWN';
export type RoutingOutcome = 'ACCEPT' | 'REJECT' | 'SECURITY_REVIEW' | 'QUARANTINE';
export type SourceOrigin = 'PHYSICAL_DEMO' | 'SYNTHETIC' | 'EXTERNAL' | 'SIMULATED';
export type ProcessingStatus = 'OK' | 'PARTIAL' | 'INSUFFICIENT_DATA' | 'INVALID_SCHEMA' | 'UNSUPPORTED_VERSION' | 'MODEL_UNAVAILABLE' | 'DEPENDENCY_UNAVAILABLE' | 'PROCESSING_ERROR';
export type FreshnessStatus = 'fresh' | 'delayed' | 'stale';

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

export interface DeviceHealth {
  battery_voltage: number | null;
  supply_current: number | null;
  restart_count: number | null;
  battery_pct: number | null;
  reboot_count_24h: number | null;
  sensor_fault_flag: boolean | null;
  sensor_read_error: boolean | null;
  sd_status: string | null;
  extra_metrics: Record<string, any>;
}

export interface TransportMetadata {
  rssi_dbm: number | null;
  snr_db: number | null;
  retry_count: number | null;
  rssi_deviation_db: number | null;
  packet_size_bytes: number | null;
  gateway_id: string | null;
  extra_metadata: Record<string, any>;
}

export interface SecurityMetadata {
  credential_id: string | null;
  integrity_present: boolean | null;
  freshness_counter: number | null;
  session_id: string | null;
  firmware_hash: string | null;
  config_hash: string | null;
  certificate_pem: string | null;
  attestation_evidence: Record<string, any> | null;
  provenance_evidence: Record<string, any> | null;
  extra_metadata: Record<string, any>;
}

export interface Measurement {
  sensor_instance_id: string;
  sensor_type: string;
  channel: string | null;
  raw_value: number | null;
  value: number | null;
  unit: string | null;
  calibration_version: string | null;
}

export interface C4AssessmentResult {
  // Combined assessment + packet data for UI display
  assessment: C4TrustAssessment;
  packet: TelemetryPacket;
  scenario?: string; // For demo/simulation scenarios
  eligible_for_c1?: boolean;
  quarantined?: boolean;
  quarantine_id?: string | null;
  persisted_to_database?: boolean;
  storage?: string | null;
  data_origin?: string | null;
  origin_explanation?: string;
  storage_explanation?: string;
  // Security gate status and ML status fields
  security_status?: 'PASS' | 'FAIL' | 'REVIEW';
  ml_status?: 'COMPLETED' | 'SKIPPED - SECURITY FAILURE' | 'SKIPPED - REVIEW' | 'UNAVAILABLE - MISSING FEATURES';
}

export interface SecurityAudit {
  control: string;
  result: 'PASS' | 'FAIL' | 'NOT REPORTED';
  evidence: string;
}

export interface CommandCenterMetrics {
  total_packets: number;
  trusted: number;
  accepted: number;
  auth_failures: number;
  untrusted: number;
  suspicious: number;
  unknown: number;
  quarantined: number;
  ml_ran: number;
}

export interface ScenarioType {
  key: string;
  label: string;
  description: string;
  category: 'hmac' | 'ecdsa' | 'certificate';
}



export interface SecurityAudit {
  control: string;
  result: 'PASS' | 'FAIL' | 'NOT REPORTED';
  evidence: string;
}

export interface CommandCenterMetrics {
  total_packets: number;
  trusted: number;
  accepted: number;
  auth_failures: number;
  untrusted: number;
  suspicious: number;
  unknown: number;
  quarantined: number;
  ml_ran: number;
}

export interface ScenarioType {
  key: string;
  label: string;
  description: string;
  category: 'hmac' | 'ecdsa' | 'certificate';
}
