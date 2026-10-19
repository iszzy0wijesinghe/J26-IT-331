
import React, { useState, useEffect } from 'react';
import '../../../styles/c4/c4-Registry.css';

interface Device {
  device_id: string;
  device_kind: string;
  zone_id: string;
  hub_id: string;
  lifecycle_state: string;
  credential_id: string | null;
  signature_algorithm: string | null;
  has_certificate: boolean;
  has_public_key: boolean;
  secret_material_present: boolean;
}

interface Pipe {
  device_id: string;
  zone_id: string;
  role: string;
}

export const Registry: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [topology, setTopology] = useState<Pipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadRegistry = () => {
      const mockDevices: Device[] = [
        {
          device_id: 'PIPE_A1',
          device_kind: 'TYPE_A',
          zone_id: 'ZONE_01',
          hub_id: 'H001',
          lifecycle_state: 'ACTIVE',
          credential_id: 'DEMO-CRED-PIPE_A1',
          signature_algorithm: 'hmac-sha256',
          has_certificate: false,
          has_public_key: false,
          secret_material_present: true,
        },
        {
          device_id: 'PIPE_B1',
          device_kind: 'TYPE_B',
          zone_id: 'ZONE_02',
          hub_id: 'H002',
          lifecycle_state: 'ACTIVE',
          credential_id: 'DEMO-CRED-PIPE_B1',
          signature_algorithm: 'hmac-sha256',
          has_certificate: false,
          has_public_key: false,
          secret_material_present: true,
        },
      ];

      const mockTopology: Pipe[] = [
        { device_id: 'PIPE_A1', zone_id: 'ZONE_01', role: 'TYPE_A' },
        { device_id: 'PIPE_B1', zone_id: 'ZONE_02', role: 'TYPE_B' },
      ];

      if (!cancelled) {
        setDevices(mockDevices);
        setTopology(mockTopology);
        setLoading(false);
      }
    };

    loadRegistry();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="c4-registry-state" role="status">
        <span className="c4-registry-spinner" aria-hidden="true" />
        <p>Loading device registry...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="c4-registry-state c4-registry-state-error" role="alert">
        <h3>Unable to load registry</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <section className="c4-registry">
      <header className="c4-registry-header">
        <div>
          <span className="c4-registry-eyebrow">C4 DEVICE MANAGEMENT</span>
          <h2 className="c4-registry-title">Device Registry and Policy</h2>
          <p className="c4-registry-description">
            In-memory demonstration registry created by C4DemoBackend. Secrets
            are not displayed.
          </p>
        </div>

        <span className="c4-registry-demo-badge">
          <span className="c4-registry-demo-dot" />
          Simulation data
        </span>
      </header>

      <section className="c4-registry-lifecycle">
        <div className="c4-registry-lifecycle-icon" aria-hidden="true">
          i
        </div>
        <div className="c4-registry-lifecycle-content">
          <h3>Lifecycle states</h3>
          <p>
            PROVISIONED: registered but not yet allowed to send. ACTIVE:
            authorized. SUSPENDED: temporarily blocked. REVOKED: permanently
            untrusted. RETIRED: decommissioned. Dashboard devices are
            registered then activated.
          </p>

          <div className="c4-registry-lifecycle-legend">
            <LifecycleBadge state="PROVISIONED" />
            <LifecycleBadge state="ACTIVE" />
            <LifecycleBadge state="SUSPENDED" />
            <LifecycleBadge state="REVOKED" />
            <LifecycleBadge state="RETIRED" />
          </div>
        </div>
      </section>

      <section className="c4-registry-panel">
        <div className="c4-registry-panel-header">
          <div>
            <h3>Device registry</h3>
            <p>Registered device identity and credential metadata.</p>
          </div>
          <span className="c4-registry-count">
            {devices.length} devices
          </span>
        </div>

        <div className="c4-registry-table-wrapper">
          <table className="c4-registry-table">
            <thead>
              <tr>
                <th scope="col">Device ID</th>
                <th scope="col">Kind</th>
                <th scope="col">Zone</th>
                <th scope="col">Hub</th>
                <th scope="col">Lifecycle</th>
                <th scope="col">Credential ID</th>
                <th scope="col">Algorithm</th>
                <th scope="col">Cert</th>
                <th scope="col">Public Key</th>
              </tr>
            </thead>
            <tbody>
              {devices.map(device => (
                <tr key={device.device_id}>
                  <td>
                    <code className="c4-registry-device-id">
                      {device.device_id}
                    </code>
                  </td>
                  <td>
                    <span className="c4-registry-kind">
                      {device.device_kind}
                    </span>
                  </td>
                  <td>{device.zone_id}</td>
                  <td>{device.hub_id}</td>
                  <td>
                    <LifecycleBadge state={device.lifecycle_state} />
                  </td>
                  <td>
                    <code className="c4-registry-credential">
                      {device.credential_id || 'N/A'}
                    </code>
                  </td>
                  <td>
                    <span className="c4-registry-algorithm">
                      {device.signature_algorithm || 'N/A'}
                    </span>
                  </td>
                  <td>
                    <BooleanBadge value={device.has_certificate} />
                  </td>
                  <td>
                    <BooleanBadge value={device.has_public_key} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="c4-registry-security-note">
          <span className="c4-registry-security-icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="4" y="10" width="16" height="11" rx="2" />
              <path d="M8 10V7a4 4 0 0 1 8 0v3" />
              <path d="M12 14v3" />
            </svg>
          </span>
          <p>
            <strong>Credential protection:</strong>{' '}
            <code>secret_material_present</code> is a boolean only. HMAC
            secrets and private keys are never shown.
          </p>
        </div>
      </section>

      <section className="c4-registry-panel">
        <div className="c4-registry-panel-header">
          <div>
            <h3>Demonstration topology</h3>
            <p>
              From shared/simulation/topology.py. These are simulated pipes,
              not physical sensors.
            </p>
          </div>
          <span className="c4-registry-count">
            {topology.length} pipes
          </span>
        </div>

        <div className="c4-registry-topology-summary">
          {topology.map(pipe => (
            <article
              key={pipe.device_id}
              className="c4-registry-topology-card"
            >
              <div className="c4-registry-pipe-icon" aria-hidden="true">
                <svg
                  viewBox="0 0 24 24"
                  width="22"
                  height="22"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M4 8h16v8H4z" />
                  <path d="M8 8V5h8v3M8 16v3h8v-3" />
                </svg>
              </div>
              <div className="c4-registry-topology-info">
                <span className="c4-registry-topology-role">
                  {pipe.role}
                </span>
                <strong>{pipe.device_id}</strong>
                <span>{pipe.zone_id}</span>
              </div>
              <span className="c4-registry-simulated-tag">Simulated</span>
            </article>
          ))}
        </div>

        <div className="c4-registry-table-wrapper">
          <table className="c4-registry-table c4-registry-topology-table">
            <thead>
              <tr>
                <th scope="col">Device ID</th>
                <th scope="col">Zone ID</th>
                <th scope="col">Role</th>
              </tr>
            </thead>
            <tbody>
              {topology.map(pipe => (
                <tr key={pipe.device_id}>
                  <td>
                    <code className="c4-registry-device-id">
                      {pipe.device_id}
                    </code>
                  </td>
                  <td>{pipe.zone_id}</td>
                  <td>
                    <span className="c4-registry-kind">{pipe.role}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="c4-registry-panel">
        <div className="c4-registry-panel-header">
          <div>
            <h3>Security policy C4_POLICY_1.1</h3>
            <p>Configured mechanisms in the current C4TrustService.</p>
          </div>
          <span className="c4-registry-policy-badge">Policy reference</span>
        </div>

        <div className="c4-registry-table-wrapper">
          <table className="c4-registry-table c4-registry-policy-table">
            <thead>
              <tr>
                <th scope="col">Control</th>
                <th scope="col">Configured mechanism</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <PolicyControl name="Device identity and lifecycle" />
                </td>
                <td>
                  <PolicyCode>DeviceRegistry.is_active</PolicyCode>
                </td>
              </tr>
              <tr>
                <td>
                  <PolicyControl name="Zone and hub binding" />
                </td>
                <td>
                  <PolicyCode>
                    Compare packet.zone_id and transport.gateway_id
                  </PolicyCode>
                </td>
              </tr>
              <tr>
                <td>
                  <PolicyControl name="X.509 validation" />
                </td>
                <td>
                  <PolicyCode>X509CertificateValidator</PolicyCode>
                </td>
              </tr>
              <tr>
                <td>
                  <PolicyControl name="Packet integrity" />
                </td>
                <td>
                  <PolicyCode>HMAC-SHA256 or ECDSA-SHA256</PolicyCode>
                </td>
              </tr>
              <tr>
                <td>
                  <PolicyControl name="Freshness" />
                </td>
                <td>
                  <PolicyCode>max_age_seconds = 30</PolicyCode>
                </td>
              </tr>
              <tr>
                <td>
                  <PolicyControl name="Replay protection" />
                </td>
                <td>
                  <PolicyCode>packet_id and sequence cache</PolicyCode>
                </td>
              </tr>
              <tr>
                <td>
                  <PolicyControl name="Attestation / provenance" />
                </td>
                <td>
                  <PolicyCode>
                    Demo evidence verifiers in C4DemoBackend
                  </PolicyCode>
                </td>
              </tr>
              <tr>
                <td>
                  <PolicyControl name="Behavioral assessment" />
                </td>
                <td>
                  <PolicyCode>
                    Random Forest anomaly score, threshold 0.70
                  </PolicyCode>
                </td>
              </tr>
              <tr>
                <td>
                  <PolicyControl name="Routing" />
                </td>
                <td>
                  <PolicyCode>C4TelemetryGate</PolicyCode>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="c4-registry-policy-footer">
          <span className="c4-registry-policy-footer-icon" aria-hidden="true">
            !
          </span>
          <p>
            This page documents the configured policy mechanisms. The backend
            remains responsible for enforcing them for each telemetry packet.
          </p>
        </div>
      </section>
    </section>
  );
};

const LifecycleBadge: React.FC<{ state: string }> = ({ state }) => {
  const normalizedState = state.toUpperCase();
  const supportedStates = [
    'PROVISIONED',
    'ACTIVE',
    'SUSPENDED',
    'REVOKED',
    'RETIRED',
  ];

  const stateClass = supportedStates.includes(normalizedState)
    ? normalizedState.toLowerCase()
    : 'unknown';

  return (
    <span className={`c4-registry-lifecycle-badge is-${stateClass}`}>
      <span className="c4-registry-lifecycle-dot" />
      {state}
    </span>
  );
};

const BooleanBadge: React.FC<{ value: boolean }> = ({ value }) => (
  <span
    className={`c4-registry-boolean-badge ${
      value ? 'is-yes' : 'is-no'
    }`}
  >
    <span className="c4-registry-boolean-icon" aria-hidden="true">
      {value ? '✓' : '−'}
    </span>
    {value ? 'Yes' : 'No'}
  </span>
);

const PolicyControl: React.FC<{ name: string }> = ({ name }) => (
  <span className="c4-registry-policy-control">{name}</span>
);

const PolicyCode: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => <code className="c4-registry-policy-code">{children}</code>;
