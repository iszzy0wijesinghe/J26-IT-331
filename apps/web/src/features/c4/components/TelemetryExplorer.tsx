
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
  const [selectedTrust, setSelectedTrust] = useState<string[]>([]);
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>([]);
  const [selectedPacketId, setSelectedPacketId] = useState<string | null>(null);

  const allDevices = useMemo(
    () =>
      [...new Set(results.map((r) => r.assessment.device_id))].sort(),
    [results],
  );

  const allTrustLabels = useMemo(
    () =>
      [...new Set(results.map((r) => r.assessment.trust_label))].sort(),
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
          selectedTrust.length > 0 &&
          !selectedTrust.includes(result.assessment.trust_label)
        ) {
          return false;
        }

        if (
          selectedScenarios.length > 0 &&
          !selectedScenarios.includes(result.scenario ?? '')
        ) {
          return false;
        }

        return true;
      }),
    [results, selectedDevices, selectedTrust, selectedScenarios],
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
    setSelectedTrust([]);
    setSelectedScenarios([]);
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
          title="Trust label"
          options={allTrustLabels}
          selected={selectedTrust}
          onToggle={(value) =>
            toggleSelection(value, selectedTrust, setSelectedTrust)
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
      </div>

      <div className="c4-telemetry-result-count">
        <span>
          <strong>{filteredResults.length}</strong> of{' '}
          <strong>{results.length}</strong> packet assessment(s) match the
          selected filters.
        </span>

        {(selectedDevices.length > 0 ||
          selectedTrust.length > 0 ||
          selectedScenarios.length > 0) && (
          <button
            type="button"
            className="c4-telemetry-view-button"
            onClick={clearFilters}
          >
            Clear filters
          </button>
        )}
      </div>

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

const getTrustBadgeClass = (trust: string): string => {
  switch (trust) {
    case 'TRUSTED':
      return 'c4-telemetry-badge c4-telemetry-badge-trusted';
    case 'UNTRUSTED':
      return 'c4-telemetry-badge c4-telemetry-badge-untrusted';
    case 'SUSPICIOUS':
      return 'c4-telemetry-badge c4-telemetry-badge-suspicious';
    default:
      return 'c4-telemetry-badge c4-telemetry-badge-unknown';
  }
};

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
          <th>Trust</th>
          <th>Routing</th>
          <th>Score</th>
          <th>Action</th>
        </tr>
      </thead>

      <tbody>
        {results.length === 0 ? (
          <tr>
            <td colSpan={7} className="c4-telemetry-no-results">
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
                  <span
                    className={getTrustBadgeClass(
                      result.assessment.trust_label,
                    )}
                  >
                    {result.assessment.trust_label}
                  </span>
                </td>
                <td>{result.assessment.routing_outcome || 'N/A'}</td>
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
