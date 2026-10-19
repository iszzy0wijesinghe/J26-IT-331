
import React from 'react';
import '../../../styles/c4/c4-Policy.css';

type PolicyStatus = 'Mandatory' | 'Conditional' | 'Advisory';
type RoutingColor = 'green' | 'red' | 'yellow' | 'gray';

export const Policy: React.FC = () => {
  return (
    <div className="c4-policy">
      <header className="c4-policy-header">
        <div>
          <div className="c4-policy-eyebrow">
            C4 / TRUST GOVERNANCE
          </div>
          <h3>Model &amp; Security Policy</h3>
          <p>
            Compact reference for the runtime demonstration. Use ML
            Model Explorer for artifact inspection.
          </p>
        </div>

        <div className="c4-policy-version">
          <span className="c4-policy-version-dot" />
          C4_POLICY_1.1
        </div>
      </header>

      <section className="c4-policy-metrics">
        <MetricCard
          label="Runtime model"
          value="Random Forest"
          description="Behavioral anomaly detection"
          icon="ML"
        />
        <MetricCard
          label="Expected features"
          value="18"
          description="Model input feature count"
          icon="FE"
        />
        <MetricCard
          label="Security policy"
          value="C4_POLICY_1.1"
          description="Runtime security constraints"
          icon="SP"
        />
      </section>

      <div className="c4-policy-banner">
        <div className="c4-policy-banner-icon">i</div>
        <div>
          <strong>Mandatory security checks take priority</strong>
          <p>
            Behavioral inference cannot override a failed mandatory
            security check. This dashboard uses simulation evidence
            verifiers; it is not a production TPM deployment.
          </p>
        </div>
      </div>

      <section className="c4-policy-panel">
        <div className="c4-policy-panel-heading">
          <div className="c4-policy-section-icon">ML</div>
          <div>
            <h4>Random Forest Anomaly Detector</h4>
            <p>Behavioral analysis and model decision constraints</p>
          </div>
          <span className="c4-policy-neutral-badge">
            Behavioral ML
          </span>
        </div>

        <div className="c4-policy-model-content">
          <div className="c4-policy-info-block">
            <h5>Model Type</h5>
            <p>
              Random Forest classifier trained on the C4 telemetry
              dataset to detect anomalous device behavior.
            </p>
          </div>

          <div className="c4-policy-info-block">
            <h5>
              Features <span className="c4-policy-count">(18 total)</span>
            </h5>
            <ul className="c4-policy-feature-list">
              <li>
                <span className="c4-policy-feature-number">01</span>
                <span>
                  <strong>Communication metrics</strong>
                  <small>RSSI, SNR, retry count, TX interval</small>
                </span>
              </li>
              <li>
                <span className="c4-policy-feature-number">02</span>
                <span>
                  <strong>Health metrics</strong>
                  <small>
                    Battery percentage, voltage, sensor fault flag
                  </small>
                </span>
              </li>
              <li>
                <span className="c4-policy-feature-number">03</span>
                <span>
                  <strong>Timing metrics</strong>
                  <small>Packet age, freshness status</small>
                </span>
              </li>
              <li>
                <span className="c4-policy-feature-number">04</span>
                <span>
                  <strong>Sequence metrics</strong>
                  <small>Sequence number, boot ID</small>
                </span>
              </li>
              <li>
                <span className="c4-policy-feature-number">05</span>
                <span>
                  <strong>Identity metrics</strong>
                  <small>Zone ID, hub ID, device kind</small>
                </span>
              </li>
              <li>
                <span className="c4-policy-feature-number">06</span>
                <span>
                  <strong>Behavioral aggregates</strong>
                  <small>Recent score history, variance</small>
                </span>
              </li>
            </ul>
          </div>

          <div className="c4-policy-threshold">
            <div>
              <span className="c4-policy-threshold-label">
                Anomaly score threshold
              </span>
              <p>
                Scores above this threshold trigger
                SUSPICIOUS/QUARANTINE routing.
              </p>
            </div>
            <div className="c4-policy-threshold-value">0.70</div>
          </div>

          <div className="c4-policy-info-block">
            <h5>Security Policy Constraints</h5>
            <ul className="c4-policy-constraint-list">
              <li>
                <span className="c4-policy-check">✓</span>
                ML runs only after mandatory security checks pass
              </li>
              <li>
                <span className="c4-policy-check">✓</span>
                ML cannot override cryptographic failures
              </li>
              <li>
                <span className="c4-policy-check">✓</span>
                ML cannot override identity mismatches
              </li>
              <li>
                <span className="c4-policy-check">✓</span>
                ML cannot override certificate validation failures
              </li>
              <li>
                <span className="c4-policy-check">✓</span>
                ML can only influence packets that already passed
                mandatory checks
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="c4-policy-panel">
        <div className="c4-policy-panel-heading">
          <div className="c4-policy-section-icon">SC</div>
          <div>
            <h4>C4_POLICY_1.1 Security Controls</h4>
            <p>
              Mandatory verification, conditional validation, and
              advisory behavioral checks
            </p>
          </div>
        </div>

        <div className="c4-policy-controls">
          <PolicyItem
            control="Device Identity"
            description="Device must be registered and in ACTIVE lifecycle state"
            status="Mandatory"
            number="01"
          />
          <PolicyItem
            control="Zone/Hub Binding"
            description="Packet zone_id must match device registration, gateway_id must match hub"
            status="Mandatory"
            number="02"
          />
          <PolicyItem
            control="Credential Verification"
            description="Credential ID must be valid and associated with device"
            status="Mandatory"
            number="03"
          />
          <PolicyItem
            control="Packet Integrity"
            description="HMAC-SHA256 or ECDSA-SHA256 signature must be valid"
            status="Mandatory"
            number="04"
          />
          <PolicyItem
            control="X.509 Certificate"
            description="Certificate must be valid, not expired, from trusted CA, matching device ID"
            status="Conditional"
            number="05"
          />
          <PolicyItem
            control="Freshness"
            description="Packet age must be within max_age_seconds (30s)"
            status="Mandatory"
            number="06"
          />
          <PolicyItem
            control="Replay Protection"
            description="Packet ID must be unique, sequence must be monotonic"
            status="Mandatory"
            number="07"
          />
          <PolicyItem
            control="Attestation"
            description="Device attestation evidence must be verifiable"
            status="Mandatory"
            number="08"
          />
          <PolicyItem
            control="Provenance"
            description="Telemetry provenance evidence must be verifiable"
            status="Mandatory"
            number="09"
          />
          <PolicyItem
            control="Behavioral ML"
            description="Random Forest anomaly score below 0.70 threshold"
            status="Advisory"
            number="10"
          />
        </div>

        <div className="c4-policy-legend">
          <span>
            <i className="c4-policy-legend-dot c4-policy-dot-mandatory" />
            Mandatory
          </span>
          <span>
            <i className="c4-policy-legend-dot c4-policy-dot-conditional" />
            Conditional
          </span>
          <span>
            <i className="c4-policy-legend-dot c4-policy-dot-advisory" />
            Advisory
          </span>
        </div>
      </section>

      <section className="c4-policy-panel">
        <div className="c4-policy-panel-heading">
          <div className="c4-policy-section-icon">RT</div>
          <div>
            <h4>Routing Outcomes</h4>
            <p>
              How C4 classifies packets after security and behavioral
              evaluation
            </p>
          </div>
        </div>

        <div className="c4-policy-routing-grid">
          <RoutingCard
            label="ACCEPT"
            description="Mandatory checks passed, ML score below threshold. Eligible for C1."
            color="green"
            code="01"
          />
          <RoutingCard
            label="REJECT"
            description="Mandatory check failed. ML not consulted. Not eligible for C1."
            color="red"
            code="02"
          />
          <RoutingCard
            label="QUARANTINE"
            description="Mandatory checks passed, ML score above threshold. Requires review."
            color="yellow"
            code="03"
          />
          <RoutingCard
            label="SECURITY_REVIEW"
            description="Insufficient evidence or ML unavailable. Requires manual review."
            color="gray"
            code="04"
          />
        </div>
      </section>

      <footer className="c4-policy-footer">
        <span>GEO NEX / C4 TRUSTED TELEMETRY</span>
        <span>Policy reference: C4_POLICY_1.1</span>
      </footer>
    </div>
  );
};

const MetricCard: React.FC<{
  label: string;
  value: string;
  description: string;
  icon: string;
}> = ({ label, value, description, icon }) => (
  <div className="c4-policy-metric-card">
    <div className="c4-policy-metric-top">
      <span className="c4-policy-metric-icon">{icon}</span>
      <span className="c4-policy-metric-label">{label}</span>
    </div>
    <div className="c4-policy-metric-value">{value}</div>
    <div className="c4-policy-metric-description">{description}</div>
  </div>
);

const PolicyItem: React.FC<{
  control: string;
  description: string;
  status: PolicyStatus;
  number: string;
}> = ({ control, description, status, number }) => (
  <div className="c4-policy-control-row">
    <span className="c4-policy-control-number">{number}</span>
    <div className="c4-policy-control-content">
      <strong>{control}</strong>
      <p>{description}</p>
    </div>
    <span
      className={`c4-policy-status c4-policy-status-${status.toLowerCase()}`}
    >
      {status}
    </span>
  </div>
);

const RoutingCard: React.FC<{
  label: string;
  description: string;
  color: RoutingColor;
  code: string;
}> = ({ label, description, color, code }) => (
  <div className={`c4-policy-routing-card c4-policy-routing-${color}`}>
    <div className="c4-policy-routing-top">
      <span className="c4-policy-routing-code">{code}</span>
      <span className="c4-policy-routing-indicator" />
    </div>
    <h5>{label}</h5>
    <p>{description}</p>
  </div>
);
