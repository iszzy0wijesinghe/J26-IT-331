import React, { useState } from 'react';
import { CommandCenter } from '../components/CommandCenter';
import { ScenarioButtons } from '../components/ScenarioButtons';
import { TelemetryExplorer } from '../components/TelemetryExplorer';
import { ThreatInvestigation } from '../components/ThreatInvestigation';
import { Authentication } from '../components/Authentication';
import MLExplorer from '../components/MLExplorer';
import { Registry } from '../components/Registry';
import { Storage } from '../components/Storage';
import { Policy } from '../components/Policy';
import { HowC4Works } from '../components/HowC4Works';
import { C4AssessmentResult } from '../types';
import './C4Page.css';

type TabType =
  | 'how-c4-works'
  | 'command-center'
  | 'telemetry-explorer'
  | 'threat-investigation'
  | 'authentication'
  | 'ml-explorer'
  | 'registry'
  | 'storage'
  | 'policy';

const tabs: { key: TabType; label: string; icon: string }[] = [
  { key: 'how-c4-works', label: 'How C4 Works', icon: '⌘' },
  { key: 'command-center', label: 'Command Center', icon: '▦' },
  { key: 'telemetry-explorer', label: 'Telemetry Explorer', icon: '◉' },
  { key: 'threat-investigation', label: 'Threat Investigation', icon: '⚠' },
  { key: 'authentication', label: 'Authentication & Device Trust', icon: '⛨' },
  { key: 'ml-explorer', label: 'ML Model Explorer', icon: '◇' },
  { key: 'registry', label: 'Device Registry & Policy', icon: '▤' },
  { key: 'storage', label: 'Data Storage & Diagnostics', icon: '▣' },
  { key: 'policy', label: 'Model & Policy', icon: '⚙' },
];

export const C4Page: React.FC = () => {
  const [results, setResults] = useState<C4AssessmentResult[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('command-center');
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunScenario = async (scenario: string): Promise<void> => {
    setNotice(null);
    setError(null);

    try {
      // Map frontend button labels to backend scenario keys
      const scenarioMapping: Record<string, string> = {
        'Run Valid Telemetry (HMAC)': 'valid_hmac',
        'Test Tampered': 'tampered_hmac',
        'Test Replay Attack': 'replay_hmac',
        'Run Valid X.509 + ECDSA': 'valid_ecdsa',
        'Test Tampered ECDSA': 'tampered_ecdsa',
        'Test Alg Fallback Rejection': 'fallback_rejection',
        'Test Expired': 'expired_x509',
        'Test Untrusted CA': 'untrusted_ca_x509',
        'Test Identity Mismatch Cert': 'mismatched_identity_x509',
        'Test Revoked': 'revoked_x509',
      };

      const normalizedScenario = scenarioMapping[scenario] || scenario.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_');

      // Call the backend API
      const response = await fetch('http://localhost:8000/api/c4/scenarios/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ scenario: normalizedScenario }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const data = await response.json();

      // Convert backend results to frontend format
      const apiResults = data.results.map((apiResult: any) => ({
        scenario: apiResult.scenario,
        assessment: {
          schema_version: '1.0',
          assessment_id: apiResult.assessment_id,
          packet_id: apiResult.packet_id,
          device_id: apiResult.device_id,
          trust_label: apiResult.trust_label,
          trust_score: apiResult.trust_score,
          mandatory_security_pass: apiResult.mandatory_security_pass,
          reason_codes: apiResult.reason_codes,
          behavioural_score: apiResult.behavioural_score,
          routing_outcome: apiResult.routing_outcome,
          model_version: 'C4_RULE_BASELINE_001',
          security_policy_version: 'C4_POLICY_1.1',
          processing_status: 'OK',
          assessment_context: 'RUNTIME',
          generated_at: new Date().toISOString(),
          correlation_id: null,
          test_run_id: null,
        },
        packet: {
          schema_version: '1.0',
          packet_id: apiResult.packet_id,
          device_id: apiResult.device_id,
          zone_id: apiResult.zone_id,
          boot_id: apiResult.boot_id,
          sequence_no: apiResult.sequence_no,
          observed_at: apiResult.observed_at,
          received_at: apiResult.received_at,
          message_type: apiResult.message_type,
          tx_interval_s: apiResult.tx_interval_s,
          freshness_status: apiResult.freshness_status,
          measurements: apiResult.measurements || [],
          device_health: {
            battery_voltage: apiResult.battery_voltage,
            supply_current: apiResult.supply_current ?? 150,
            restart_count: 0,
            battery_pct: apiResult.battery_pct,
            reboot_count_24h: apiResult.reboot_count_24h ?? 0,
            sensor_fault_flag: apiResult.sensor_fault_flag,
            sensor_read_error: false,
            sd_status: 'OK',
            extra_metrics: {},
          },
          transport: {
            rssi_dbm: apiResult.rssi_dbm,
            snr_db: apiResult.snr_db,
            retry_count: apiResult.retry_count,
            rssi_deviation_db: 0,
            packet_size_bytes: apiResult.packet_size_bytes ?? 256,
            gateway_id: apiResult.hub_id,
            extra_metadata: {},
          },
          security: {
            credential_id: apiResult.credential_id,
            integrity_present: true,
            freshness_counter: apiResult.sequence_no,
            session_id: 'DEMO-SESSION',
            firmware_hash: null,
            config_hash: null,
            certificate_pem: apiResult.certificate_present ? 'cert-present' : null,
            attestation_evidence: { demo_attestation: apiResult.device_id },
            provenance_evidence: { demo_provenance: apiResult.packet_id },
            extra_metadata: {},
          },
          source_origin: apiResult.source_origin,
          test_run_id: null,
          correlation_id: null,
        },
        eligible_for_c1: apiResult.eligible_for_c1,
        quarantined: apiResult.quarantined,
        quarantine_id: apiResult.quarantine_id,
        persisted_to_database: apiResult.persisted_to_database,
        storage: apiResult.storage,
        data_origin: apiResult.data_origin,
        origin_explanation: apiResult.origin_explanation,
        storage_explanation: apiResult.storage_explanation,
        // Add new fields from API
        security_status: apiResult.security_status,
        ml_status: apiResult.ml_status,
      }));

      setResults((previousResults) => [...previousResults, ...apiResults]);
      setNotice(
        `${data.count} assessment result(s) recorded for ${scenario}. ` +
          `Security verification complete. ML is disabled in scenario mode. ` +
          `Download ML-Ready CSV (PASS only) and upload to ML Explorer for predictions.`
      );
    } catch (err) {
      setError(
        `Error running scenario: ${
          err instanceof Error ? err.message : 'Unknown error'
        }`
      );
    }
  };

  const handleClearResults = (): void => {
    setResults([]);
    setNotice(null);
    setError(null);
  };

  const renderActiveTab = (): React.ReactNode => {
    switch (activeTab) {
      case 'how-c4-works':
        return <HowC4Works />;
      case 'command-center':
        return <CommandCenter results={results} />;
      case 'telemetry-explorer':
        return <TelemetryExplorer results={results} />;
      case 'threat-investigation':
        return <ThreatInvestigation results={results} />;
      case 'authentication':
        return <Authentication results={results} />;
      case 'ml-explorer':
        return <MLExplorer />;
      case 'registry':
        return <Registry />;
      case 'storage':
        return <Storage />;
      case 'policy':
        return <Policy />;
      default:
        return <CommandCenter results={results} />;
    }
  };

  const activeLabel =
    tabs.find((tab) => tab.key === activeTab)?.label ?? 'Command Center';

  return (
    <div className="c4-dropdown-layout" style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      
      {/* C4 DROPDOWN HEADER */}
      <div className="c4-dropdown-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', background: '#10233a', padding: '16px 24px', borderRadius: '12px', color: 'white' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
           <span style={{ background: '#14b8a6', padding: '8px 12px', borderRadius: '8px', fontWeight: 'bold' }}>C4</span>
           <div>
             <h2 style={{ margin: 0, fontSize: '18px' }}>Trusted Telemetry</h2>
             <span style={{ fontSize: '12px', color: '#94a3b8' }}>Security Platform</span>
           </div>
        </div>

        {/* THE MAIN DROPDOWN MENU */}
        <select 
          value={activeTab} 
          onChange={(e) => setActiveTab(e.target.value as TabType)}
          style={{ padding: '10px 16px', borderRadius: '8px', background: '#1e293b', color: 'white', border: '1px solid #334155', fontSize: '14px', cursor: 'pointer', outline: 'none' }}
        >
          {tabs.map((tab) => (
            <option key={tab.key} value={tab.key}>
              {tab.icon} {tab.label}
            </option>
          ))}
        </select>
      </div>

      {/* MAIN C4 CONTENT */}
      <div className="c4-main-content-wrapper">
        {notice && (
          <div className="c4-alert c4-alert-success" role="status">
            <span className="c4-alert-icon" aria-hidden="true">
              ✓
            </span>
            <div className="c4-alert-message">{notice}</div>
            <button
              className="c4-alert-dismiss"
              type="button"
              onClick={() => setNotice(null)}
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        )}

        {error && (
          <div className="c4-alert c4-alert-danger" role="alert">
            <span className="c4-alert-icon" aria-hidden="true">
              !
            </span>
            <div className="c4-alert-message">{error}</div>
            <button
              className="c4-alert-dismiss"
              type="button"
              onClick={() => setError(null)}
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        <section className="c4-page-content-heading">
          <div>
            <span className="c4-section-eyebrow">
              IT4010 · GEONEX RESEARCH PROJECT
            </span>

            <h3>{activeLabel}</h3>

            <p>
              Verify telemetry integrity, device identity and trust decisions.
            </p>
          </div>

          <div className="c4-section-number" aria-hidden="true">
            C4
          </div>
        </section>

        {/* 1. MAIN AUTHENTICATION SCENARIOS DROPDOWN */}
        {activeTab === 'command-center' && (
          <details 
            style={{ 
              background: 'white', 
              border: '1px solid #e2e8f0', 
              borderRadius: '12px', 
              marginBottom: '24px', 
              overflow: 'hidden',
              boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
            }}
          >
            <summary 
              style={{ 
                padding: '16px 20px', 
                cursor: 'pointer', 
                backgroundColor: '#f8fafc',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div>
                <span style={{ fontSize: '10px', fontWeight: 800, color: '#14b8a6', letterSpacing: '1px', display: 'block', marginBottom: '4px' }}>
                  TELEMETRY SECURITY TESTING
                </span>
                <span style={{ fontSize: '16px', fontWeight: 600, color: '#1e293b' }}>
                  Authentication Scenarios
                </span>
                <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#64748b' }}>
                  Run the available demonstration scenarios to inspect simulated C4 trust decisions.
                </p>
              </div>
              <span style={{ padding: '4px 8px', background: '#fff8e8', color: '#996313', fontSize: '10px', fontWeight: 800, borderRadius: '4px', border: '1px solid #f5dfaa' }}>
                DEMO MODE
              </span>
            </summary>
            
            {/* 2. INNER CONTENT: HMAC, ECDSA, CERT DROPDOWNS LIVE IN HERE */}
            <div style={{ padding: '20px', borderTop: '1px solid #e2e8f0' }}>
              <ScenarioButtons
                onRunScenario={handleRunScenario}
                onClearResults={handleClearResults}
              />
            </div>
          </details>
        )}

        <section className="c4-active-page" key={activeTab}>
          {renderActiveTab()}
        </section>
      </div>
    </div>
  );
};