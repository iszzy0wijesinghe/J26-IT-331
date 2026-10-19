
import React, { useState, useMemo } from 'react';
import { C4AssessmentResult } from '../types';
import '../../../styles/c4/c4-ThreatInvestigation.css';

interface ThreatInvestigationProps {
  results: C4AssessmentResult[];
}

export const ThreatInvestigation: React.FC<ThreatInvestigationProps> = ({ results }) => {
  const [selectedPacket, setSelectedPacket] = useState<number | null>(null);

  const incidents = useMemo(() => {
    return results.filter(
      r =>
        r.assessment.trust_label !== 'TRUSTED' ||
        r.quarantined ||
        !r.assessment.mandatory_security_pass
    );
  }, [results]);

  const integrityFailures = useMemo(() => {
    return incidents.filter(r => r.assessment.reason_codes.includes('INTEGRITY_INVALID')).length;
  }, [incidents]);

  const replayDetections = useMemo(() => {
    return incidents.filter(r => r.assessment.reason_codes.some(code => code.includes('REPLAY'))).length;
  }, [incidents]);

  const reasonCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    incidents.forEach(r => {
      r.assessment.reason_codes.forEach(code => {
        counts[code] = (counts[code] || 0) + 1;
      });
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [incidents]);

  if (results.length === 0) {
    return (
      <div className="c4-threat-investigation">
        <div className="c4-threat-empty">
          <h3>No session assessments yet</h3>
          <p>
            Use a sidebar scenario such as <strong>Run Valid Telemetry (HMAC)</strong> or{' '}
            <strong>Run Valid X.509 + ECDSA</strong>. Each click generates synthetic packets and
            processes them through the real C4 trust gate.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="c4-threat-investigation">
      <h3 className="c4-threat-title">Threat Investigation</h3>
      <p className="c4-threat-description">
        Rejected, suspicious, unknown or quarantined session assessments.
      </p>

      <div className="c4-threat-metrics">
        <MetricCard label="Flagged assessments" value={incidents.length} />
        <MetricCard label="Integrity failures" value={integrityFailures} />
        <MetricCard label="Replay detections" value={replayDetections} />
      </div>

      {incidents.length === 0 ? (
        <div className="c4-threat-no-incidents">
          No flagged assessments in this session.
        </div>
      ) : (
        <>
          <div className="c4-threat-panel">
            <h3 className="c4-threat-panel-title">Flagged assessments</h3>
            <ResultsTable results={incidents} onSelect={setSelectedPacket} />
          </div>

          <div className="c4-threat-panel">
            <h3 className="c4-threat-panel-title">Incident reason frequency</h3>
            <p className="c4-threat-panel-description">
              Counted from flagged session rows only.
            </p>

            <div className="c4-threat-frequency-list">
              {reasonCounts.slice(0, 12).map(([code, count]) => (
                <div key={code} className="c4-threat-frequency-row">
                  <div className="c4-threat-frequency-code">{code}</div>

                  <div className="c4-threat-frequency-track">
                    <div
                      className="c4-threat-frequency-bar"
                      style={{
                        width: `${
                          reasonCounts[0]?.[1]
                            ? (count / reasonCounts[0][1]) * 100
                            : 0
                        }%`,
                      }}
                    />
                  </div>

                  <div className="c4-threat-frequency-count">{count}</div>
                </div>
              ))}
            </div>
          </div>

          {selectedPacket !== null && incidents[selectedPacket] && (
            <PacketDetail packet={incidents[selectedPacket]} />
          )}
        </>
      )}
    </div>
  );
};

const MetricCard: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="c4-threat-metric-card">
    <div className="c4-threat-metric-value">{value.toLocaleString()}</div>
    <div className="c4-threat-metric-label">{label}</div>
  </div>
);

const ResultsTable: React.FC<{
  results: C4AssessmentResult[];
  onSelect: (index: number) => void;
}> = ({ results, onSelect }) => {
  return (
    <div className="c4-threat-table-wrapper">
      <table className="c4-threat-table">
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Packet ID</th>
            <th>Device</th>
            <th>Trust</th>
            <th>Routing</th>
            <th>Score</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result, index) => (
            <tr key={index}>
              <td className="c4-threat-scenario">{result.scenario || '-'}</td>
              <td className="c4-threat-packet-id">{result.assessment.packet_id}</td>
              <td>{result.assessment.device_id}</td>
              <td>
                <span
                  className={
                    result.assessment.trust_label === 'TRUSTED'
                      ? 'c4-threat-badge c4-threat-badge-trusted'
                      : result.assessment.trust_label === 'UNTRUSTED'
                      ? 'c4-threat-badge c4-threat-badge-untrusted'
                      : result.assessment.trust_label === 'SUSPICIOUS'
                      ? 'c4-threat-badge c4-threat-badge-suspicious'
                      : 'c4-threat-badge c4-threat-badge-unknown'
                  }
                >
                  {result.assessment.trust_label}
                </span>
              </td>
              <td>{result.assessment.routing_outcome}</td>
              <td className="c4-threat-score">
                {result.assessment.behavioural_score !== null
                  ? result.assessment.behavioural_score.toFixed(4)
                  : 'N/A'}
              </td>
              <td>
                <button
                  type="button"
                  onClick={() => onSelect(index)}
                  className="c4-threat-view-button"
                >
                  View
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const PacketDetail: React.FC<{ packet: C4AssessmentResult }> = ({ packet }) => {
  return (
    <div className="c4-threat-detail">
      <h3 className="c4-threat-detail-title">Packet detail</h3>

      <div className="c4-threat-detail-grid c4-threat-detail-grid-three">
        <MetricCardSmall label="Data origin" value={packet.data_origin || 'Unavailable'} />
        <MetricCardSmall label="Stored in" value={packet.storage || 'Unavailable'} />
        <MetricCardSmall label="Assessment ID" value={packet.assessment.assessment_id} />
      </div>

      <div className="c4-threat-detail-grid c4-threat-detail-grid-four">
        <MetricCardSmall label="Trust label" value={packet.assessment.trust_label} />
        <MetricCardSmall label="Routing" value={packet.assessment.routing_outcome || 'Unavailable'} />
        <MetricCardSmall
          label="Mandatory security"
          value={packet.assessment.mandatory_security_pass ? 'PASS' : 'FAIL'}
        />
        <MetricCardSmall
          label="Behavioral score"
          value={
            packet.assessment.behavioural_score !== null
              ? packet.assessment.behavioural_score.toFixed(4)
              : 'Unavailable'
          }
        />
      </div>

      <div className="c4-threat-detail-section">
        <h4 className="c4-threat-section-title">Reason codes</h4>
        <div className="c4-threat-detail-rows">
          {packet.assessment.reason_codes.length > 0 ? (
            packet.assessment.reason_codes.map((code, i) => (
              <div key={i} className="c4-threat-detail-row">
                <code className="c4-threat-detail-value">{code}</code>
              </div>
            ))
          ) : (
            <p className="c4-threat-no-reasons">No reason codes recorded.</p>
          )}
        </div>
      </div>

      <div className="c4-threat-notice c4-threat-notice-origin">
        This view reports simulation outcomes. It does not release quarantine records.
      </div>
    </div>
  );
};

const MetricCardSmall: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="c4-threat-metric-card">
    <div className="c4-threat-metric-value">{value}</div>
    <div className="c4-threat-metric-label">{label}</div>
  </div>
);
