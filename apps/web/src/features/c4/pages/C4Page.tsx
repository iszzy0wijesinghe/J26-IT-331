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
      const normalizedScenario = scenario.toLowerCase().replace(/-/g, '_');
      const timestamp = Date.now();
      const packetId = `packet-${timestamp}`;
      const deviceId = 'PIPE_A1';
      const generatedAt = new Date().toISOString();

      const isTampered = normalizedScenario.includes('tampered');
      const isReplay = normalizedScenario.includes('replay');
      const isExpired = normalizedScenario.includes('expired');
      const isUntrustedCA =
        normalizedScenario.includes('untrusted_ca') ||
        normalizedScenario.includes('untrusted ca');
      const isIdentityMismatch =
        normalizedScenario.includes('mismatched') ||
        normalizedScenario.includes('identity_mismatch') ||
        normalizedScenario.includes('identity mismatch');
      const isRevoked = normalizedScenario.includes('revoked');
      const isFallback = normalizedScenario.includes('fallback');
      const isEcdsa = normalizedScenario.includes('ecdsa');
      const isHmac = normalizedScenario.includes('hmac');

      let trustLabel: 'TRUSTED' | 'UNTRUSTED' | 'SUSPICIOUS' | 'UNKNOWN' =
        'TRUSTED';

      let routingOutcome:
        | 'ACCEPT'
        | 'REJECT'
        | 'QUARANTINE'
        | 'SECURITY_REVIEW' = 'ACCEPT';

      let mandatorySecurityPass = true;
      let reasonCodes = [
        'ZONE_VALID',
        'IDENTITY_VALID',
        'INTEGRITY_VALID',
      ];
      let behaviouralScore: number | null = Math.random() * 0.5;
      let quarantined = false;

      if (isTampered || isFallback) {
        trustLabel = 'UNTRUSTED';
        routingOutcome = 'REJECT';
        mandatorySecurityPass = false;
        reasonCodes = [
          isFallback ? 'ALGORITHM_FALLBACK_REJECTED' : 'INTEGRITY_INVALID',
        ];
        behaviouralScore = null;
        quarantined = true;
      } else if (isReplay) {
        trustLabel = 'UNTRUSTED';
        routingOutcome = 'REJECT';
        mandatorySecurityPass = false;
        reasonCodes = ['REPLAY_DETECTED'];
        behaviouralScore = null;
        quarantined = true;
      } else if (isExpired) {
        trustLabel = 'UNTRUSTED';
        routingOutcome = 'REJECT';
        mandatorySecurityPass = false;
        reasonCodes = ['CERTIFICATE_EXPIRED'];
        behaviouralScore = null;
        quarantined = true;
      } else if (isUntrustedCA) {
        trustLabel = 'UNTRUSTED';
        routingOutcome = 'REJECT';
        mandatorySecurityPass = false;
        reasonCodes = ['CERTIFICATE_UNTRUSTED_ISSUER'];
        behaviouralScore = null;
        quarantined = true;
      } else if (isIdentityMismatch) {
        trustLabel = 'UNTRUSTED';
        routingOutcome = 'REJECT';
        mandatorySecurityPass = false;
        reasonCodes = ['CERTIFICATE_IDENTITY_MISMATCH'];
        behaviouralScore = null;
        quarantined = true;
      } else if (isRevoked) {
        trustLabel = 'UNTRUSTED';
        routingOutcome = 'REJECT';
        mandatorySecurityPass = false;
        reasonCodes = ['CERTIFICATE_REVOKED'];
        behaviouralScore = null;
        quarantined = true;
      } else {
        reasonCodes = [
          'ZONE_VALID',
          'IDENTITY_VALID',
          'INTEGRITY_VALID',
          'FRESHNESS_VALID',
          'REPLAY_CHECK_VALID',
        ];

        if (isEcdsa) {
          reasonCodes.push('CERTIFICATE_VALID');
        }
      }

      const credentialId = isEcdsa
        ? `ecdsa-${normalizedScenario.replace(/\s+/g, '-')}`
        : isHmac
          ? `hmac-${normalizedScenario.replace(/\s+/g, '-')}`
          : `demo-${normalizedScenario.replace(/\s+/g, '-')}`;

      const mockResult: C4AssessmentResult = {
        scenario,
        assessment: {
          schema_version: '1.0',
          assessment_id: `assessment-${timestamp}`,
          packet_id: packetId,
          device_id: deviceId,
          trust_label: trustLabel,
          trust_score: trustLabel === 'TRUSTED' ? 0.95 : 0,
          mandatory_security_pass: mandatorySecurityPass,
          reason_codes: reasonCodes,
          behavioural_score: behaviouralScore,
          routing_outcome: routingOutcome,
          model_version: 'C4_RULE_BASELINE_001',
          security_policy_version: 'C4_POLICY_1.1',
          processing_status: 'OK',
          assessment_context: 'RUNTIME',
          generated_at: generatedAt,
          correlation_id: null,
          test_run_id: null,
        },
        packet: {
          schema_version: '1.0',
          packet_id: packetId,
          device_id: deviceId,
          zone_id: 'ZONE_01',
          boot_id: 'BOOT-001',
          sequence_no: Math.floor(Math.random() * 1000),
          observed_at: generatedAt,
          received_at: generatedAt,
          message_type: 'TELEMETRY',
          tx_interval_s: 10,
          freshness_status: 'fresh',
          measurements: [],
          device_health: {
            battery_voltage: 3.7,
            supply_current: 150,
            restart_count: 0,
            battery_pct: 85,
            reboot_count_24h: 0,
            sensor_fault_flag: false,
            sensor_read_error: false,
            sd_status: 'OK',
            extra_metrics: {},
          },
          transport: {
            rssi_dbm: -65,
            snr_db: 12,
            retry_count: 0,
            rssi_deviation_db: 0,
            packet_size_bytes: 256,
            gateway_id: 'H001',
            extra_metadata: {},
          },
          security: {
            credential_id: credentialId,
            integrity_present: true,
            freshness_counter: Math.floor(Math.random() * 1000),
            session_id: `SESSION-${timestamp}`,
            firmware_hash: null,
            config_hash: null,
            certificate_pem: isEcdsa ? 'mock-cert-pem' : null,
            attestation_evidence: { demo_attestation: deviceId },
            provenance_evidence: { demo_provenance: packetId },
            extra_metadata: {},
          },
          source_origin: 'SIMULATED',
          test_run_id: null,
          correlation_id: null,
        },
        eligible_for_c1: trustLabel === 'TRUSTED' && mandatorySecurityPass,
        quarantined,
        quarantine_id: quarantined ? `Q_${timestamp.toString(36)}` : null,
        persisted_to_database: false,
        storage: 'react_component_state',
        data_origin: 'FRONTEND_SIMULATION',
        origin_explanation:
          'Generated by the React frontend mock; not assessed by the real C4 backend.',
        storage_explanation:
          'Stored in React component state and lost when the page is refreshed.',
      };

      setResults((previousResults) => [...previousResults, mockResult]);
      setNotice(`1 simulated assessment result recorded for ${scenario}.`);
    } catch (err) {
      setError(
        `Error running scenario: ${
          err instanceof Error ? err.message : 'Unknown error'
        }`,
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