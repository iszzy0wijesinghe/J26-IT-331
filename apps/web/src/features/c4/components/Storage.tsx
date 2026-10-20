
import React, { useState, useEffect } from 'react';
import '../../../styles/c4/c4-Storage.css';

interface DatabaseInfo {
  configured: boolean;
  reachable: boolean;
  host: string | null;
  port: number | null;
  name: string | null;
  user: string | null;
  telemetry_packets: number | null;
  error: string | null;
}

interface Diagnostics {
  model_path: string;
  model_available: boolean;
  holdout_path: string;
  database: DatabaseInfo;
}

interface QuarantineRecord {
  quarantine_id: string;
  packet_id: string;
  device_id: string;
  trust_label: string;
  routing_outcome: string;
  reason_codes: string[];
  quarantine_reason: string;
  quarantined_at: string;
  packet_data: Record<string, any>;
  assessment: any;
  released: boolean;
  released_at: string | null;
  release_reason: string | null;
  reviewed_by: string | null;
  metadata: Record<string, any>;
}

interface QuarantineData {
  count: number;
  records: QuarantineRecord[];
  statistics: {
    total: number;
    released: number;
    unreleased: number;
    by_reason: Record<string, number>;
  };
  message: string;
}

export const Storage: React.FC = () => {
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error] = useState<string | null>(null);
  const [quarantineData, setQuarantineData] = useState<QuarantineData | null>(null);
  const [quarantineLoading, setQuarantineLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState<QuarantineRecord | null>(null);

  const API_BASE = "http://127.0.0.1:8000";

  useEffect(() => {
    let cancelled = false;

    const loadDiagnostics = async () => {
      const mockDiagnostics: Diagnostics = {
        model_path:
          'experiments/c4/models/random_forest_corrected.joblib',
        model_available: true,
        holdout_path:
          'experiments/c4/data/C4_test_corrected.csv',
        database: {
          configured: true,
          reachable: false,
          host: 'localhost',
          port: 5432,
          name: 'geonex',
          user: 'geonex_user',
          telemetry_packets: null,
          error: 'Connection refused',
        },
      };

      if (!cancelled) {
        setDiagnostics(mockDiagnostics);
        setLoading(false);
      }
    };

    void loadDiagnostics();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadQuarantineData = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/c4/quarantine`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        if (!cancelled) {
          setQuarantineData(data);
          setQuarantineLoading(false);
        }
      } catch (err) {
        console.error('Failed to load quarantine data:', err);
        if (!cancelled) {
          setQuarantineData({
            count: 0,
            records: [],
            statistics: { total: 0, released: 0, unreleased: 0, by_reason: {} },
            message: 'Failed to load quarantine data',
          });
          setQuarantineLoading(false);
        }
      }
    };

    void loadQuarantineData();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="c4-storage c4-storage-state">
        <div className="c4-storage-spinner" />
        <p>Loading diagnostics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="c4-storage c4-storage-state">
        <div className="c4-storage-alert c4-storage-alert-error">
          <span className="c4-storage-alert-icon">!</span>
          <div>
            <strong>Diagnostics error</strong>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!diagnostics) {
    return (
      <div className="c4-storage c4-storage-state">
        <div className="c4-storage-empty-icon">!</div>
        <h3>No diagnostics available</h3>
        <p>System diagnostic information could not be loaded.</p>
      </div>
    );
  }

  const db = diagnostics.database;

  return (
    <div className="c4-storage">
      <header className="c4-storage-header">
        <div>
          <div className="c4-storage-eyebrow">
            C4 / SYSTEM INFRASTRUCTURE
          </div>
          <h3>Data Storage and System Diagnostics</h3>
          <p>
            Where each data category lives in this repository.
            Passwords and secrets are not shown.
          </p>
        </div>

        <div className="c4-storage-header-badge">
          <span className="c4-storage-status-dot" />
          Diagnostic Overview
        </div>
      </header>

      <section className="c4-storage-metrics">
        <MetricCard
          label="Runtime model file"
          value={diagnostics.model_available ? 'FOUND' : 'MISSING'}
          status={diagnostics.model_available ? 'success' : 'danger'}
          description="Model artifact status"
        />

        <MetricCard
          label="PostgreSQL"
          value={db.reachable ? 'REACHABLE' : 'NOT REACHABLE'}
          status={db.reachable ? 'success' : 'danger'}
          description="Database connection status"
        />

        <MetricCard
          label="telemetry_packets rows"
          value={
            db.telemetry_packets !== null
              ? db.telemetry_packets.toLocaleString()
              : 'Unavailable'
          }
          status="neutral"
          description="Persisted telemetry records"
        />
      </section>

      <section className="c4-storage-panel">
        <div className="c4-storage-panel-heading">
          <div className="c4-storage-section-icon">ML</div>
          <div>
            <h4>Model Artifact</h4>
            <p>Location of the saved C4 behavioral model</p>
          </div>
          <span
            className={`c4-storage-badge ${
              diagnostics.model_available
                ? 'c4-storage-badge-success'
                : 'c4-storage-badge-danger'
            }`}
          >
            {diagnostics.model_available ? 'Available' : 'Missing'}
          </span>
        </div>

        <div className="c4-storage-path-label">MODEL PATH</div>
        <code className="c4-storage-path">
          {diagnostics.model_path}
        </code>

        <div className="c4-storage-secondary-path">
          <span>Holdout dataset</span>
          <code>{diagnostics.holdout_path}</code>
        </div>
      </section>

      <section className="c4-storage-panel">
        <div className="c4-storage-panel-heading">
          <div className="c4-storage-section-icon">DB</div>
          <div>
            <h4>Configured Database</h4>
            <p>PostgreSQL connection diagnostics</p>
          </div>
          <span
            className={`c4-storage-badge ${
              db.reachable
                ? 'c4-storage-badge-success'
                : 'c4-storage-badge-danger'
            }`}
          >
            {db.reachable ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <div className="c4-storage-details-grid">
          <DetailRow label="Host" value={db.host || 'N/A'} />
          <DetailRow
            label="Port"
            value={db.port?.toString() || 'N/A'}
          />
          <DetailRow label="Database name" value={db.name || 'N/A'} />
          <DetailRow label="Database user" value={db.user || 'N/A'} />
          <DetailRow
            label="Configured"
            value={db.configured ? 'Yes' : 'No'}
          />
          <DetailRow
            label="Reachable"
            value={db.reachable ? 'Yes' : 'No'}
          />
        </div>

        {db.error && (
          <div className="c4-storage-alert c4-storage-alert-warning">
            <span className="c4-storage-alert-icon">!</span>
            <div>
              <strong>Connection information</strong>
              <p>{db.error}</p>
            </div>
          </div>
        )}
      </section>

      <section className="c4-storage-panel c4-storage-inventory-panel">
        <div className="c4-storage-panel-heading">
          <div className="c4-storage-section-icon">ST</div>
          <div>
            <h4>Storage Inventory</h4>
            <p>
              Storage locations, data flow, and persistence behavior
            </p>
          </div>
        </div>

        <div className="c4-storage-table-wrapper">
          <table className="c4-storage-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Exact source or path</th>
                <th>How data gets there</th>
                <th>How it is read</th>
                <th>Survives restart?</th>
              </tr>
            </thead>

            <tbody>
              <tr>
                <td>
                  <strong>Dashboard assessments</strong>
                  <span className="c4-storage-cell-subtitle">
                    Runtime session
                  </span>
                </td>
                <td>
                  <code>st.session_state.c4_results</code>
                </td>
                <td>Scenario buttons</td>
                <td>This UI</td>
                <td>
                  <PersistenceBadge persistent={false} />
                </td>
              </tr>

              <tr>
                <td>
                  <strong>Dashboard quarantine files</strong>
                  <span className="c4-storage-cell-subtitle">
                    Temporary storage
                  </span>
                </td>
                <td>
                  <code>TemporaryDirectory inside C4DemoBackend</code>
                </td>
                <td>
                  <code>C4TelemetryGate.process()</code>
                </td>
                <td>Deleted by <code>backend.close()</code></td>
                <td>
                  <PersistenceBadge persistent={false} />
                </td>
              </tr>

              <tr>
                <td>
                  <strong>Default C4 quarantine JSON</strong>
                  <span className="c4-storage-cell-subtitle">
                    Local disk
                  </span>
                </td>
                <td>
                  <code>quarantine/c4/</code>
                </td>
                <td>
                  QuarantineManager when no temp directory is supplied
                </td>
                <td>JSON files</td>
                <td>
                  <PersistenceBadge persistent />
                </td>
              </tr>

              <tr>
                <td>
                  <strong>Offline C4 dataset</strong>
                  <span className="c4-storage-cell-subtitle">
                    CSV files
                  </span>
                </td>
                <td>
                  <code>experiments/c4/data/*.csv</code>
                </td>
                <td>Preparation and split scripts</td>
                <td>pandas / ML Explorer</td>
                <td>
                  <PersistenceBadge persistent />
                </td>
              </tr>

              <tr>
                <td>
                  <strong>Saved models</strong>
                  <span className="c4-storage-cell-subtitle">
                    Model artifacts
                  </span>
                </td>
                <td>
                  <code>experiments/c4/models/*.joblib</code>
                </td>
                <td>Training scripts</td>
                <td>
                  <code>TrainedModel.load</code>
                </td>
                <td>
                  <PersistenceBadge persistent />
                </td>
              </tr>

              <tr>
                <td>
                  <strong>Demo registry</strong>
                  <span className="c4-storage-cell-subtitle">
                    Application memory
                  </span>
                </td>
                <td>
                  <code>In-memory DeviceRegistry</code>
                </td>
                <td>
                  <code>C4DemoBackend.__init__</code>
                </td>
                <td>
                  <code>list_safe_devices()</code>
                </td>
                <td>
                  <PersistenceBadge persistent={false} />
                </td>
              </tr>

              <tr>
                <td>
                  <strong>PostgreSQL telemetry</strong>
                  <span className="c4-storage-cell-subtitle">
                    Database storage
                  </span>
                </td>
                <td>
                  <code>
                    geonex.telemetry_packets /
                    sensor_observations
                  </code>
                </td>
                <td>
                  <code>apps/ingestion/persistence.py</code> via{' '}
                  <code>load_demo_simulation.py</code>
                </td>
                <td>SQLAlchemy</td>
                <td>
                  <PersistenceBadge persistent />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="c4-storage-alert c4-storage-alert-info">
          <span className="c4-storage-alert-icon">i</span>
          <div>
            <strong>Important distinction</strong>
            <p>
              A packet count in PostgreSQL does not mean this dashboard
              is displaying those database rows. The Command Center
              counts session assessments separately from persisted
              telemetry records.
            </p>
          </div>
        </div>
      </section>

      <section className="c4-storage-panel c4-storage-inventory-panel">
        <div className="c4-storage-panel-heading">
          <div className="c4-storage-section-icon">Q</div>
          <div>
            <h4>Quarantine File Viewer</h4>
            <p>
              View detailed information about quarantined telemetry packets
              stored in quarantine/c4/
            </p>
          </div>
        </div>

        {quarantineLoading ? (
          <div className="c4-storage-state">
            <div className="c4-storage-spinner" />
            <p>Loading quarantine files...</p>
          </div>
        ) : (
          <>
            <div className="c4-storage-metrics">
              <MetricCard
                label="Total Records"
                value={quarantineData?.statistics.total?.toString() || '0'}
                status="neutral"
                description="Total quarantine records"
              />
              <MetricCard
                label="Released"
                value={quarantineData?.statistics.released?.toString() || '0'}
                status="success"
                description="Released records"
              />
              <MetricCard
                label="Unreleased"
                value={quarantineData?.statistics.unreleased?.toString() || '0'}
                status="danger"
                description="Unreleased records"
              />
            </div>

            {quarantineData && quarantineData.records.length > 0 && (
              <>
                <div className="c4-storage-table-wrapper">
                  <table className="c4-storage-table">
                    <thead>
                      <tr>
                        <th>Quarantine ID</th>
                        <th>Packet ID</th>
                        <th>Device ID</th>
                        <th>Trust Label</th>
                        <th>Routing Outcome</th>
                        <th>Quarantine Reason</th>
                        <th>Released</th>
                        <th>Quarantined At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {quarantineData.records.map((record) => (
                        <tr
                          key={record.quarantine_id}
                          onClick={() => setSelectedRecord(record)}
                          style={{ cursor: 'pointer' }}
                          className={
                            selectedRecord?.quarantine_id === record.quarantine_id
                              ? 'c4-storage-table-row-selected'
                              : ''
                          }
                        >
                          <td>
                            <code>{record.quarantine_id}</code>
                          </td>
                          <td>{record.packet_id}</td>
                          <td>{record.device_id}</td>
                          <td>
                            <span
                              className={`c4-storage-badge ${
                                record.trust_label === 'TRUSTED'
                                  ? 'c4-storage-badge-success'
                                  : record.trust_label === 'UNTRUSTED'
                                  ? 'c4-storage-badge-danger'
                                  : 'c4-storage-badge-warning'
                              }`}
                            >
                              {record.trust_label}
                            </span>
                          </td>
                          <td>{record.routing_outcome}</td>
                          <td>{record.quarantine_reason}</td>
                          <td>
                            <PersistenceBadge persistent={record.released} />
                          </td>
                          <td>
                            {new Date(record.quarantined_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {selectedRecord && (
                  <div className="c4-storage-detail-panel">
                    <h5>Quarantine Record Details</h5>
                    <div className="c4-storage-details-grid">
                      <DetailRow
                        label="Quarantine ID"
                        value={selectedRecord.quarantine_id}
                      />
                      <DetailRow
                        label="Packet ID"
                        value={selectedRecord.packet_id}
                      />
                      <DetailRow
                        label="Device ID"
                        value={selectedRecord.device_id}
                      />
                      <DetailRow
                        label="Trust Label"
                        value={selectedRecord.trust_label}
                      />
                      <DetailRow
                        label="Routing Outcome"
                        value={selectedRecord.routing_outcome}
                      />
                      <DetailRow
                        label="Released"
                        value={selectedRecord.released ? 'Yes' : 'No'}
                      />
                    </div>

                    <div className="c4-storage-secondary-path">
                      <span>Quarantined At</span>
                      <code>
                        {new Date(selectedRecord.quarantined_at).toLocaleString()}
                      </code>
                    </div>

                    {selectedRecord.reason_codes.length > 0 && (
                      <>
                        <div className="c4-storage-path-label">
                          Reason Codes
                        </div>
                        <div className="c4-storage-reason-codes">
                          {selectedRecord.reason_codes.map((code, idx) => (
                            <code key={idx}>{code}</code>
                          ))}
                        </div>
                      </>
                    )}

                    <div className="c4-storage-path-label">
                      Quarantine Reason
                    </div>
                    <code className="c4-storage-path">
                      {selectedRecord.quarantine_reason}
                    </code>

                    {Object.keys(selectedRecord.packet_data).length > 0 && (
                      <>
                        <div className="c4-storage-path-label">
                          Packet Data
                        </div>
                        <pre className="c4-storage-json">
                          {JSON.stringify(
                            selectedRecord.packet_data,
                            null,
                            2
                          )}
                        </pre>
                      </>
                    )}

                    {selectedRecord.released && (
                      <>
                        <div className="c4-storage-path-label">
                          Release Information
                        </div>
                        <div className="c4-storage-details-grid">
                          <DetailRow
                            label="Released At"
                            value={
                              selectedRecord.released_at
                                ? new Date(
                                    selectedRecord.released_at
                                  ).toLocaleString()
                                : 'N/A'
                            }
                          />
                          <DetailRow
                            label="Release Reason"
                            value={selectedRecord.release_reason || 'N/A'}
                          />
                          <DetailRow
                            label="Reviewed By"
                            value={selectedRecord.reviewed_by || 'N/A'}
                          />
                        </div>
                      </>
                    )}

                    {selectedRecord.assessment && (
                      <>
                        <div className="c4-storage-path-label">
                          Assessment Data
                        </div>
                        <pre className="c4-storage-json">
                          {JSON.stringify(selectedRecord.assessment, null, 2)}
                        </pre>
                      </>
                    )}
                  </div>
                )}

                {Object.keys(quarantineData.statistics.by_reason).length >
                  0 && (
                    <>
                      <h5>Quarantine Reason Distribution</h5>
                      <div className="c4-storage-reason-distribution">
                        {Object.entries(
                          quarantineData.statistics.by_reason
                        ).map(([reason, count]) => (
                          <div
                            key={reason}
                            className="c4-storage-reason-bar"
                          >
                            <span className="c4-storage-reason-label">
                              {reason}
                            </span>
                            <div className="c4-storage-reason-bar-fill">
                              <div
                                className="c4-storage-reason-bar-progress"
                                style={{
                                  width: `${(count / quarantineData.statistics.total) * 100}%`,
                                }}
                              />
                              <span className="c4-storage-reason-count">
                                {count}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
              </>
            )}
          </>
        )}
      </section>

      <footer className="c4-storage-footer">
        <span>GEO NEX / C4 TRUSTED TELEMETRY</span>
        <span>Storage and diagnostics overview</span>
      </footer>
    </div>
  );
};

interface MetricCardProps {
  label: string;
  value: string;
  status: 'success' | 'danger' | 'neutral';
  description: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  status,
  description,
}) => (
  <div className="c4-storage-metric-card">
    <div className="c4-storage-metric-top">
      <span className="c4-storage-metric-label">{label}</span>
      <span
        className={`c4-storage-metric-indicator c4-storage-metric-indicator-${status}`}
      />
    </div>
    <div
      className={`c4-storage-metric-value c4-storage-metric-value-${status}`}
    >
      {value}
    </div>
    <div className="c4-storage-metric-description">
      {description}
    </div>
  </div>
);

const DetailRow: React.FC<{ label: string; value: string }> = ({
  label,
  value,
}) => (
  <div className="c4-storage-detail-row">
    <span className="c4-storage-detail-label">{label}</span>
    <code className="c4-storage-detail-value">{value}</code>
  </div>
);

const PersistenceBadge: React.FC<{ persistent: boolean }> = ({
  persistent,
}) => (
  <span
    className={`c4-storage-persistence ${
      persistent
        ? 'c4-storage-persistence-yes'
        : 'c4-storage-persistence-no'
    }`}
  >
    <span className="c4-storage-persistence-dot" />
    {persistent ? 'Yes' : 'No'}
  </span>
);
