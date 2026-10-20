
import React, { useMemo, useState } from 'react';
import { C4AssessmentResult } from '../types';
import '../../../styles/c4/c4-TelemetryExplorer.css';

interface TelemetryExplorerProps {
  results: C4AssessmentResult[];
}

export const TelemetryExplorer: React.FC<TelemetryExplorerProps> = ({
  results,
}) => {
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>([]);
  const [selectedSecurityStatus, setSelectedSecurityStatus] = useState<string[]>([]);
  const [selectedMLStatus, setSelectedMLStatus] = useState<string[]>([]);
  const [selectedPacketId, setSelectedPacketId] = useState<string | null>(null);

  const allDevices = useMemo(
    () =>
      [...new Set(results.map((r) => r.assessment.device_id))].sort(),
    [results],
  );

  const allScenarios = useMemo(
    () =>
      [
        ...new Set(
          results
            .map((r) => r.scenario)
            .filter((s): s is string => s !== undefined),
        ),
      ].sort(),
    [results],
  );

  const allSecurityStatuses = useMemo(
    () =>
      [
        ...new Set(
          results
            .map((r) => r.security_status)
            .filter((s): s is 'PASS' | 'FAIL' | 'REVIEW' => s !== undefined),
        ),
      ].sort(),
    [results],
  );

  const allMLStatuses = useMemo(
    () =>
      [
        ...new Set(
          results
            .map((r) => r.ml_status)
            .filter((s): s is 'COMPLETED' | 'SKIPPED - SECURITY FAILURE' | 'SKIPPED - REVIEW' | 'UNAVAILABLE - MISSING FEATURES' => s !== undefined),
        ),
      ].sort(),
    [results],
  );

  const filteredResults = useMemo(
    () =>
      results.filter((result) => {
        if (
          selectedDevices.length > 0 &&
          !selectedDevices.includes(result.assessment.device_id)
        ) {
          return false;
        }

        if (
          selectedScenarios.length > 0 &&
          !selectedScenarios.includes(result.scenario ?? '')
        ) {
          return false;
        }

        if (
          selectedSecurityStatus.length > 0 &&
          !selectedSecurityStatus.includes(result.security_status ?? '')
        ) {
          return false;
        }

        if (
          selectedMLStatus.length > 0 &&
          !selectedMLStatus.includes(result.ml_status ?? '')
        ) {
          return false;
        }

        return true;
      }),
    [results, selectedDevices, selectedScenarios, selectedSecurityStatus, selectedMLStatus],
  );

  const selectedPacket = useMemo(
    () =>
      filteredResults.find(
        (result) => result.assessment.assessment_id === selectedPacketId,
      ) ?? null,
    [filteredResults, selectedPacketId],
  );

  const toggleSelection = (
    value: string,
    current: string[],
    setter: React.Dispatch<React.SetStateAction<string[]>>,
  ) => {
    setter(
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    );
  };

  const clearFilters = () => {
    setSelectedDevices([]);
    setSelectedScenarios([]);
    setSelectedSecurityStatus([]);
    setSelectedMLStatus([]);
  };

  if (results.length === 0) {
    return (
      <div className="c4-telemetry-explorer">
        <div className="c4-telemetry-empty">
          <h3>No session assessments yet</h3>
          <p>
            Use a sidebar scenario such as{' '}
            <strong>Run Valid Telemetry (HMAC)</strong> or{' '}
            <strong>Run Valid X.509 + ECDSA</strong>. Each click generates
            synthetic packets and processes them through the C4 trust gate.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="c4-telemetry-explorer">
      <div className="c4-telemetry-help">
        <h4>What happens when I click a scenario button?</h4>
        <p>
          C4DemoBackend creates synthetic packets, signs them, and calls
          C4TelemetryGate.process(). The assessment is appended to session
          memory. It is not loaded from the C4 CSV dataset and is not written
          to PostgreSQL by this demo flow.
        </p>
      </div>

      <div className="c4-telemetry-filters">
        <FilterGroup
          title="Device"
          options={allDevices}
          selected={selectedDevices}
          onToggle={(value) =>
            toggleSelection(value, selectedDevices, setSelectedDevices)
          }
        />

        <FilterGroup
          title="Scenario"
          options={allScenarios}
          selected={selectedScenarios}
          onToggle={(value) =>
            toggleSelection(value, selectedScenarios, setSelectedScenarios)
          }
        />

        <FilterGroup
          title="Security Status"
          options={allSecurityStatuses as string[]}
          selected={selectedSecurityStatus}
          onToggle={(value) =>
            toggleSelection(value, selectedSecurityStatus, setSelectedSecurityStatus)
          }
        />

        <FilterGroup
          title="ML Status"
          options={allMLStatuses as string[]}
          selected={selectedMLStatus}
          onToggle={(value) =>
            toggleSelection(value, selectedMLStatus, setSelectedMLStatus)
          }
        />
      </div>

      <div className="c4-telemetry-result-count">
        <span>
          <strong>{filteredResults.length}</strong> of{' '}
          <strong>{results.length}</strong> packet assessment(s) match the
          selected filters.
        </span>

        {(selectedDevices.length > 0 ||
          selectedScenarios.length > 0 ||
          selectedSecurityStatus.length > 0 ||
          selectedMLStatus.length > 0) && (
          <button
            type="button"
            className="c4-telemetry-view-button"
            onClick={clearFilters}
          >
            Clear filters
          </button>
        )}
      </div>

      <button
  type="button"
  className="c4-telemetry-view-button"
  onClick={() => {
    const headers = [
      'Scenario',
      'Packet ID',
      'Device',
      'Security Status',
      'Trust Label',
      'Routing',
      'ML Status',
      'Score',
      'Mandatory Security',
      'Eligible for C1',
      'Quarantined',
      'Persisted to Database',
      'Reason Codes',
    ];

    const escapeCsv = (value: unknown) => {
      const text = String(value ?? '');
      return `"${text.replace(/"/g, '""')}"`;
    };

    const rows = filteredResults.map((result) => {
      const assessment = result.assessment;

      return [
        result.scenario ?? '',
        assessment.packet_id,
        assessment.device_id,
        result.security_status ?? '',
        assessment.trust_label ?? '',
        assessment.routing_outcome ?? 'N/A',
        result.ml_status ?? '',
        assessment.behavioural_score ?? '',
        assessment.mandatory_security_pass,
        result.eligible_for_c1,
        result.quarantined,
        result.persisted_to_database,
        assessment.reason_codes.join(', '),
      ];
    });

    const csv = [headers, ...rows]
      .map((row) => row.map(escapeCsv).join(','))
      .join('\r\n');

    const blob = new Blob(['\uFEFF', csv], {
      type: 'text/csv;charset=utf-8;',
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = 'geonex_c4_telemetry_assessments.csv';
    link.click();

    URL.revokeObjectURL(url);
  }}
  disabled={filteredResults.length === 0}
>
  Download Assessment CSV
</button>

      <button
  type="button"
  className="c4-telemetry-view-button"
  onClick={() => {
    // Filter only PASS results for ML prediction
    const passResults = filteredResults.filter(r => r.security_status === 'PASS');

    if (passResults.length === 0) {
      alert('No PASS results available for ML prediction. Filter for Security Status = PASS first.');
      return;
    }

    const headers = [
      'packet_id',
      'device_id',
      'device_timestamp',
      'received_timestamp',
      'tx_interval_s',
      'rssi_dbm',
      'freshness_status',
      'snr_db',
      'retry_count',
      'packet_size_bytes',
      'battery_pct',
      'battery_voltage_v',
      'current_ma',
      'reboot_count_24h',
      'sensor_fault_flag',
      'full_packet_json',
    ];

    const escapeCsv = (value: unknown) => {
      const text = String(value ?? '');
      return `"${text.replace(/"/g, '""')}"`;
    };

    const rows = passResults.map((result) => {
      const packet = result.packet;

      return [
        packet.packet_id,
        packet.device_id,
        packet.observed_at,
        packet.received_at,
        packet.tx_interval_s ?? 0,
        packet.transport.rssi_dbm ?? 0,
        packet.freshness_status ?? 'fresh',
        packet.transport.snr_db ?? 0,
        packet.transport.retry_count ?? 0,
        packet.transport.packet_size_bytes ?? 256,
        packet.device_health.battery_pct ?? 0,
        packet.device_health.battery_voltage ?? 0,
        packet.device_health.supply_current ?? 0,
        packet.device_health.reboot_count_24h ?? 0,
        packet.device_health.sensor_fault_flag ? 1 : 0,
        JSON.stringify(packet),
      ];
    });

    const csv = [headers, ...rows]
      .map((row) => row.map(escapeCsv).join(','))
      .join('\r\n');

    const blob = new Blob(['\uFEFF', csv], {
      type: 'text/csv;charset=utf-8;',
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = 'geonex_c4_ml_prediction_ready.csv';
    link.click();

    URL.revokeObjectURL(url);
  }}
  disabled={filteredResults.length === 0}
>
  Download ML-Ready CSV (PASS only)
</button>

      <div className="c4-telemetry-table-card">
        <h3 className="c4-telemetry-section-title">Assessment results</h3>

        <ResultsTable
          results={filteredResults}
          selectedPacketId={selectedPacketId}
          onSelect={setSelectedPacketId}
        />
      </div>

      {selectedPacket && (
        <PacketDetail
          key={selectedPacket.assessment.assessment_id}
          packet={selectedPacket}
        />
      )}
    </div>
  );
};

interface FilterGroupProps {
  title: string;
  options: string[];
  selected: string[];
  onToggle: (value: string) => void;
}

const FilterGroup: React.FC<FilterGroupProps> = ({
  title,
  options,
  selected,
  onToggle,
}) => (
  <div className="c4-telemetry-filter-group">
    <div className="c4-telemetry-filter-label">
      <span>{title}</span>
      {selected.length > 0 && (
        <span className="c4-telemetry-filter-count">
          {selected.length}
        </span>
      )}
    </div>

    <div className="c4-telemetry-filter-options">
      {options.length > 0 ? (
        options.map((option) => (
          <label key={option} className="c4-telemetry-filter-option">
            <input
              type="checkbox"
              checked={selected.includes(option)}
              onChange={() => onToggle(option)}
            />
            <span>{option}</span>
          </label>
        ))
      ) : (
        <span className="c4-telemetry-no-reasons">
          No options available.
        </span>
      )}
    </div>
  </div>
);

interface ResultsTableProps {
  results: C4AssessmentResult[];
  selectedPacketId: string | null;
  onSelect: (assessmentId: string) => void;
}

const ResultsTable: React.FC<ResultsTableProps> = ({
  results,
  selectedPacketId,
  onSelect,
}) => (
  <div className="c4-telemetry-table-wrapper">
    <table className="c4-telemetry-table">
      <thead>
        <tr>
          <th>Scenario</th>
          <th>Packet ID</th>
          <th>Device</th>
          <th>Security</th>
          <th>Trust Label</th>
          <th>Routing</th>
          <th>ML</th>
          <th>Score</th>
          <th>Action</th>
        </tr>
      </thead>

      <tbody>
        {results.length === 0 ? (
          <tr>
            <td colSpan={9} className="c4-telemetry-no-results">
              No assessments match the selected filters.
            </td>
          </tr>
        ) : (
          results.map((result, index) => {
            const assessmentId = result.assessment.assessment_id;
            const isSelected = assessmentId === selectedPacketId;

            return (
              <tr
                key={`${assessmentId}-${index}`}
                aria-selected={isSelected}
              >
                <td>{result.scenario || '-'}</td>
                <td className="c4-telemetry-packet-id">
                  {result.assessment.packet_id}
                </td>
                <td>{result.assessment.device_id}</td>
                <td>
                  <span className={`c4-telemetry-badge ${result.security_status === 'PASS' ? 'c4-telemetry-badge-trusted' : 'c4-telemetry-badge-untrusted'}`}>
                    {result.security_status || '-'}
                  </span>
                </td>
                <td>
                  <span className={`c4-telemetry-badge ${result.assessment.trust_label === 'TRUSTED' ? 'c4-telemetry-badge-trusted' : result.assessment.trust_label === 'UNTRUSTED' ? 'c4-telemetry-badge-untrusted' : result.assessment.trust_label === 'SUSPICIOUS' ? 'c4-telemetry-badge-suspicious' : 'c4-telemetry-badge-unknown'}`}>
                    {result.assessment.trust_label || '-'}
                  </span>
                </td>
                <td>{result.assessment.routing_outcome || 'N/A'}</td>
                <td>{result.ml_status || '-'}</td>
                <td className="c4-telemetry-score">
                  {result.assessment.behavioural_score !== null &&
                  result.assessment.behavioural_score !== undefined
                    ? result.assessment.behavioural_score.toFixed(4)
                    : 'N/A'}
                </td>
                <td>
                  <button
                    type="button"
                    className="c4-telemetry-view-button"
                    aria-pressed={isSelected}
                    onClick={() => onSelect(assessmentId)}
                  >
                    {isSelected ? 'Viewing' : 'View'}
                  </button>
                </td>
              </tr>
            );
          })
        )}
      </tbody>
    </table>
  </div>
);

interface PacketDetailProps {
  packet: C4AssessmentResult;
}

const PacketDetail: React.FC<PacketDetailProps> = ({ packet }) => {
  const assessment = packet.assessment;
  const telemetryPacket = packet.packet;

  return (
    <div className="c4-telemetry-packet-detail">
      <div>
        <h3 className="c4-telemetry-section-title">Packet lifecycle</h3>
        <p className="c4-telemetry-detail-intro">
          Fields below come from the simulated TelemetryPacket and
          C4TrustAssessment.
        </p>
      </div>

      <div className="c4-telemetry-detail-grid">
        <MetricCard
          label="Data origin"
          value={packet.data_origin || 'Unavailable'}
        />
        <MetricCard
          label="Stored in"
          value={packet.storage || 'Unavailable'}
        />
        <MetricCard
          label="Assessment ID"
          value={assessment.assessment_id}
        />
      </div>

      {packet.origin_explanation && (
        <div className="c4-telemetry-notice c4-telemetry-notice-origin">
          {packet.origin_explanation}
        </div>
      )}

      {packet.storage_explanation && (
        <div className="c4-telemetry-notice c4-telemetry-notice-storage">
          {packet.storage_explanation}
        </div>
      )}

      <div className="c4-telemetry-detail-grid c4-telemetry-detail-grid-four">
        <MetricCard
          label="Trust label"
          value={assessment.trust_label}
        />
        <MetricCard
          label="Routing"
          value={assessment.routing_outcome || 'Unavailable'}
        />
        <MetricCard
          label="Mandatory security"
          value={assessment.mandatory_security_pass ? 'PASS' : 'FAIL'}
          outcome={assessment.mandatory_security_pass ? 'yes' : 'no'}
        />
        <MetricCard
          label="Behavioral score"
          value={
            assessment.behavioural_score !== null &&
            assessment.behavioural_score !== undefined
              ? assessment.behavioural_score.toFixed(4)
              : 'Unavailable / not scored'
          }
        />
      </div>

      <section className="c4-telemetry-detail-section">
        <h4 className="c4-telemetry-detail-heading">
          Identity and timing
        </h4>

        <div className="c4-telemetry-detail-rows">
          <DetailRow label="packet_id" value={assessment.packet_id} />
          <DetailRow label="device_id" value={assessment.device_id} />
          <DetailRow label="zone_id" value={telemetryPacket.zone_id} />
          <DetailRow
            label="hub_id"
            value={telemetryPacket.transport.gateway_id || 'N/A'}
          />
          <DetailRow
            label="sequence_no"
            value={telemetryPacket.sequence_no?.toString() || 'N/A'}
          />
          <DetailRow
            label="observed_at"
            value={String(telemetryPacket.observed_at)}
          />
          <DetailRow
            label="received_at"
            value={String(telemetryPacket.received_at)}
          />
          <DetailRow
            label="source_origin"
            value={String(telemetryPacket.source_origin)}
          />
          <DetailRow
            label="credential_id"
            value={telemetryPacket.security.credential_id || 'N/A'}
          />
          <DetailRow
            label="certificate_present"
            value={
              telemetryPacket.security.certificate_pem ? 'Yes' : 'No'
            }
          />
        </div>
      </section>

      <section className="c4-telemetry-detail-section">
        <h4 className="c4-telemetry-detail-heading">Reason codes</h4>

        <div className="c4-telemetry-reason-list">
          {assessment.reason_codes.length > 0 ? (
            assessment.reason_codes.map((code, index) => (
              <code
                key={`${code}-${index}`}
                className="c4-telemetry-reason-code"
              >
                {code}
              </code>
            ))
          ) : (
            <p className="c4-telemetry-no-reasons">
              No reason codes recorded.
            </p>
          )}
        </div>
      </section>

      <section className="c4-telemetry-detail-section">
        <h4 className="c4-telemetry-detail-heading">
          Routing and quarantine
        </h4>

        <div className="c4-telemetry-detail-grid">
          <MetricCard
            label="Eligible for C1"
            value={packet.eligible_for_c1 ? 'YES' : 'NO'}
            outcome={packet.eligible_for_c1 ? 'yes' : 'no'}
          />
          <MetricCard
            label="Quarantined"
            value={packet.quarantined ? 'YES' : 'NO'}
            outcome={packet.quarantined ? 'no' : 'neutral'}
          />
          <MetricCard
            label="Quarantine ID"
            value={packet.quarantine_id || 'None'}
          />
        </div>
      </section>

      <section className="c4-telemetry-detail-section">
        <h4 className="c4-telemetry-detail-heading">
          Processing and persistence
        </h4>

        <div className="c4-telemetry-detail-grid c4-telemetry-detail-grid-two">
          <MetricCard
            label="ML ran"
            value={
              assessment.behavioural_score !== null &&
              assessment.behavioural_score !== undefined
                ? 'YES'
                : 'NO'
            }
          />
          <MetricCard
            label="Saved to PostgreSQL"
            value={packet.persisted_to_database ? 'YES' : 'NO'}
            outcome={packet.persisted_to_database ? 'yes' : 'neutral'}
          />
        </div>
      </section>
    </div>
  );
};

interface MetricCardProps {
  label: string;
  value: string;
  outcome?: 'yes' | 'no' | 'neutral';
}

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  outcome,
}) => {
  const outcomeClass =
    outcome === 'yes'
      ? 'c4-telemetry-outcome-yes'
      : outcome === 'no'
        ? 'c4-telemetry-outcome-no'
        : outcome === 'neutral'
          ? 'c4-telemetry-outcome-neutral'
          : '';

  return (
    <div className="c4-telemetry-metric-card">
      <div className={`c4-telemetry-metric-value ${outcomeClass}`}>
        {value}
      </div>
      <div className="c4-telemetry-metric-label">{label}</div>
    </div>
  );
};

interface DetailRowProps {
  label: string;
  value: string;
}

const DetailRow: React.FC<DetailRowProps> = ({ label, value }) => (
  <div className="c4-telemetry-detail-row">
    <span className="c4-telemetry-detail-label">{label}:</span>
    <span className="c4-telemetry-detail-value">{value}</span>
  </div>
);
