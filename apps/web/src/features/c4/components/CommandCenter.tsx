import React from 'react';
import { C4AssessmentResult, CommandCenterMetrics } from '../types';

interface CommandCenterProps {
  results: C4AssessmentResult[];
}

export const CommandCenter: React.FC<CommandCenterProps> = ({ results }) => {
  const metrics = React.useMemo(() => {
    if (results.length === 0) {
      return {
        total_packets: 0,
        trusted: 0,
        accepted: 0,
        auth_failures: 0,
        untrusted: 0,
        suspicious: 0,
        unknown: 0,
        quarantined: 0,
        ml_ran: 0,
      };
    }

    return {
      total_packets: results.length,
      trusted: results.filter(r => r.assessment.trust_label === 'TRUSTED').length,
      accepted: results.filter(r => r.assessment.routing_outcome === 'ACCEPT').length,
      auth_failures: results.filter(r => !r.assessment.mandatory_security_pass).length,
      untrusted: results.filter(r => r.assessment.trust_label === 'UNTRUSTED').length,
      suspicious: results.filter(r => r.assessment.trust_label === 'SUSPICIOUS').length,
      unknown: results.filter(r => r.assessment.trust_label === 'UNKNOWN').length,
      quarantined: results.filter(r => r.quarantined).length,
      ml_ran: results.filter(r => r.assessment.behavioural_score !== null).length,
    };
  }, [results]);

  const trustDistribution = React.useMemo(() => {
    const distribution = {
      TRUSTED: 0,
      UNTRUSTED: 0,
      SUSPICIOUS: 0,
      UNKNOWN: 0,
    };
    results.forEach(r => {
      distribution[r.assessment.trust_label]++;
    });
    return distribution;
  }, [results]);

  const routingDistribution = React.useMemo(() => {
    const distribution: Record<string, number> = {};
    results.forEach(r => {
      if (r.assessment.routing_outcome) {
        distribution[r.assessment.routing_outcome] = (distribution[r.assessment.routing_outcome] || 0) + 1;
      }
    });
    return distribution;
  }, [results]);

  if (results.length === 0) {
    return (
      <div className="p-6">
        <div className="c4-alert c4-alert-warning">
          <div className="c4-alert-title">No session assessments yet</div>
          <div className="c4-alert-message">
            Use a sidebar scenario such as <strong>Run Valid Telemetry (HMAC)</strong> or{' '}
            <strong>Run Valid X.509 + ECDSA</strong>. Each click generates synthetic packets and
            processes them through the real C4 trust gate.
          </div>
        </div>
      </div>
    );
  }

  // Shared style for the dropdown boxes to make them look clean
  const dropdownStyle: React.CSSProperties = {
    background: 'white',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    marginBottom: '16px',
    overflow: 'hidden',
    boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
  };

  const summaryStyle: React.CSSProperties = {
    padding: '16px 20px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '16px',
    color: '#1e293b',
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
    borderBottom: '1px solid transparent',
  };

  const contentStyle: React.CSSProperties = {
    padding: '20px',
    borderTop: '1px solid #e2e8f0',
  };

  return (
    <div className="p-6 space-y-6">
      
      {/* 1. Data Provenance Dropdown */}
      <details style={dropdownStyle}>
        <summary style={summaryStyle}>
          <span style={{ marginRight: '8px', color: '#14b8a6' }}>▶</span> Data shown on this dashboard
        </summary>
        <div style={contentStyle}>
          <p style={{ margin: 0, color: '#475569', lineHeight: 1.6 }}>
            Command Center, Telemetry Explorer and Threat Investigation metrics are counted from
            session assessments created by the scenario buttons. They are not live ESP32
            packets and they are not PostgreSQL rows unless a separate ingestion script was run.
          </p>
        </div>
      </details>

      {/* 2. Metrics Grid Dropdown */}
      <details style={dropdownStyle}>
        <summary style={summaryStyle}>
          <span style={{ marginRight: '8px', color: '#14b8a6' }}>▶</span> Session Metrics Overview
        </summary>
        <div style={contentStyle}>
          <div className="c4-metrics-grid">
            <MetricCard label="Assessed" value={metrics.total_packets.toLocaleString()} help="session results length" type="info" />
            <MetricCard label="Trusted" value={metrics.trusted.toLocaleString()} help="trust_label == TRUSTED" type="success" />
            <MetricCard label="Accepted" value={metrics.accepted.toLocaleString()} help="routing_outcome == ACCEPT" type="success" />
            <MetricCard label="Auth failures" value={metrics.auth_failures.toLocaleString()} help="mandatory_security_pass is false" type="danger" />
            <MetricCard label="Rejected" value={metrics.untrusted.toLocaleString()} type="danger" />
            <MetricCard label="Suspicious" value={metrics.suspicious.toLocaleString()} type="warning" />
            <MetricCard label="Unknown" value={metrics.unknown.toLocaleString()} type="info" />
            <MetricCard label="Quarantined" value={metrics.quarantined.toLocaleString()} type="warning" />
          </div>
          {metrics.ml_ran > 0 && (
            <p className="text-sm text-gray-600" style={{ marginTop: '16px', marginBottom: 0 }}>
              Behavioral model produced a score for {metrics.ml_ran} of {metrics.total_packets} session packets.
            </p>
          )}
        </div>
      </details>

      {/* 3. Trust & Routing Charts Dropdown */}
      <details style={dropdownStyle}>
        <summary style={summaryStyle}>
          <span style={{ marginRight: '8px', color: '#14b8a6' }}>▶</span> Trust & Routing Distributions
        </summary>
        <div style={contentStyle}>
          <div className="grid grid-cols-2 gap-6">
            <div className="c4-chart-container">
              <h3>Trust distribution</h3>
              <p className="text-sm text-gray-600 mb-4">Labels returned by C4TrustService.assess()</p>
              <SimpleBarChart data={trustDistribution} />
            </div>
            <div className="c4-chart-container">
              <h3>Routing outcomes</h3>
              <p className="text-sm text-gray-600 mb-4">Decisions from C4TelemetryGate</p>
              <SimpleBarChart data={routingDistribution} />
            </div>
          </div>
        </div>
      </details>

      {/* 4. Recent Activity Dropdown */}
      <details style={dropdownStyle}>
        <summary style={summaryStyle}>
          <span style={{ marginRight: '8px', color: '#14b8a6' }}>▶</span> Recent Session Activity
        </summary>
        <div style={contentStyle}>
          <p className="text-sm text-gray-600 mb-4">
            Last 30 behavioral scores. Missing scores appear as gaps.
          </p>
          <RecentActivityChart results={results.slice(-30)} />
        </div>
      </details>

      {/* 5. Recent Results Table Dropdown */}
      <details style={dropdownStyle}>
        <summary style={summaryStyle}>
          <span style={{ marginRight: '8px', color: '#14b8a6' }}>▶</span> Recent Assessments Table
        </summary>
        <div style={contentStyle}>
          <ResultsTable results={results.slice(-10).reverse()} />
        </div>
      </details>

    </div>
  );
};

const MetricCard: React.FC<{ label: string; value: string; help?: string; type?: 'success' | 'warning' | 'danger' | 'info' }> = ({
  label,
  value,
  help,
  type,
}) => (
  <div className={`c4-metric-card ${type || ''}`} title={help}>
    <div className="c4-metric-value">{value}</div>
    <div className="c4-metric-label">{label}</div>
    {help && <div className="c4-metric-help">{help}</div>}
  </div>
);

const SimpleBarChart: React.FC<{ data: Record<string, number> }> = ({ data }) => {
  const maxValue = Math.max(...Object.values(data), 1);

  return (
    <div className="c4-bar-chart">
      {Object.entries(data).map(([label, value]) => (
        <div key={label} className="c4-bar-row">
          <div className="c4-bar-label">{label}</div>
          <div className="c4-bar-track">
            <div
              className="c4-bar-fill"
              style={{ width: `${(value / maxValue) * 100}%` }}
            />
          </div>
          <div className="c4-bar-value">{value}</div>
        </div>
      ))}
    </div>
  );
};

const RecentActivityChart: React.FC<{ results: C4AssessmentResult[] }> = ({ results }) => {
  return (
    <div className="c4-activity-chart">
      {results.length === 0 ? (
        <p className="text-gray-500 text-center py-10">No data available</p>
      ) : (
        <div>
          {results.map((result, index) => (
            <div key={index} className="c4-activity-row">
              <div className="c4-activity-index">{index + 1}</div>
              <div className="c4-activity-bar">
                {result.assessment.behavioural_score !== null ? (
                  <div
                    className={`c4-activity-fill ${
                      result.assessment.behavioural_score >= 0.7 ? 'high' : 'low'
                    }`}
                    style={{ width: `${result.assessment.behavioural_score * 100}%` }}
                  />
                ) : (
                  <div className="c4-activity-fill neutral" style={{ width: '100%' }} />
                )}
              </div>
              <div className="c4-activity-value">
                {result.assessment.behavioural_score !== null
                  ? result.assessment.behavioural_score.toFixed(4)
                  : 'N/A'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const ResultsTable: React.FC<{ results: C4AssessmentResult[] }> = ({ results }) => {
  return (
    <div className="overflow-x-auto">
      <table className="c4-table">
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Packet ID</th>
            <th>Device</th>
            <th>Trust</th>
            <th>Routing</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result, index) => (
            <tr key={index}>
              <td>{result.scenario || '-'}</td>
              <td><code>{result.assessment.packet_id}</code></td>
              <td>{result.assessment.device_id}</td>
              <td>
                <span
                  className={`c4-badge c4-badge-${result.assessment.trust_label.toLowerCase()}`}
                >
                  {result.assessment.trust_label}
                </span>
              </td>
              <td>{result.assessment.routing_outcome || '-'}</td>
              <td>
                {result.assessment.behavioural_score !== null
                  ? result.assessment.behavioural_score.toFixed(4)
                  : 'N/A'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};