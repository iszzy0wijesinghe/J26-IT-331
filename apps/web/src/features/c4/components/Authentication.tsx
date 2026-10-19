
import React, { useMemo } from 'react';
import { C4AssessmentResult } from '../types';
import '../../../styles/c4/c4-Authentication.css';

interface AuthenticationProps {
  results: C4AssessmentResult[];
}

export const Authentication: React.FC<AuthenticationProps> = ({ results }) => {
  const { hmacCount, ecdsaCount, integrityInvalid } = useMemo(() => {
    const hmac = results.filter(
      result =>
        result.packet.security.credential_id?.startsWith('hmac')
    ).length;

    const ecdsa = results.filter(
      result =>
        result.packet.security.credential_id?.startsWith('ecdsa')
    ).length;

    const integrityFailures = results.filter(result =>
      result.assessment.reason_codes.includes('INTEGRITY_INVALID')
    ).length;

    return {
      hmacCount: hmac,
      ecdsaCount: ecdsa,
      integrityInvalid: integrityFailures,
    };
  }, [results]);

  return (
    <section className="c4-authentication">
      <header className="c4-auth-header">
        <div>
          <span className="c4-auth-eyebrow">C4 SECURITY CONTROLS</span>
          <h3 className="c4-auth-title">
            Authentication and Device Trust
          </h3>
          <p className="c4-auth-description">
            Mandatory cryptographic checks. Behavioral ML cannot override a
            failure here.
          </p>
        </div>

        <span className="c4-auth-status">
          <span className="c4-auth-status-dot" />
          Mandatory checks
        </span>
      </header>

      <section className="c4-auth-help" aria-labelledby="c4-auth-help-title">
        <div className="c4-auth-help-icon" aria-hidden="true">
          <span>i</span>
        </div>
        <div>
          <h4 id="c4-auth-help-title" className="c4-auth-section-title">
            Which checks are mandatory?
          </h4>
          <p className="c4-auth-help-text">
            Device identity and ACTIVE lifecycle, zone and hub match,
            credential ID, HMAC or ECDSA integrity, freshness, replay,
            attestation and provenance. X.509 validation runs when a
            certificate is present or required.
          </p>
        </div>
      </section>

      <section
        className="c4-auth-panel"
        aria-labelledby="c4-auth-controls-title"
      >
        <div className="c4-auth-panel-header">
          <div>
            <h4 id="c4-auth-controls-title" className="c4-auth-section-title">
              Mandatory cryptographic controls
            </h4>
            <p className="c4-auth-panel-description">
              Security checks applied by the C4 trust gate.
            </p>
          </div>
          <span className="c4-auth-control-count">5 controls</span>
        </div>

        <div className="c4-auth-table-wrapper">
          <table className="c4-auth-table">
            <thead>
              <tr>
                <th scope="col">Control</th>
                <th scope="col">Simple meaning</th>
                <th scope="col">Code location</th>
                <th scope="col">When it applies</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <span className="c4-auth-control-name">HMAC-SHA256</span>
                  <span className="c4-auth-control-type c4-auth-type-symmetric">
                    Symmetric
                  </span>
                </td>
                <td>Symmetric shared secret</td>
                <td>
                  <code>C4TrustService.sign_packet / _verify_signature</code>
                </td>
                <td>Mandatory if credential algorithm is HMAC</td>
              </tr>
              <tr>
                <td>
                  <span className="c4-auth-control-name">
                    ECDSA-SHA256 P-256
                  </span>
                  <span className="c4-auth-control-type c4-auth-type-asymmetric">
                    Asymmetric
                  </span>
                </td>
                <td>Asymmetric public-key signature</td>
                <td>
                  <code>sign_packet_ecdsa / _verify_signature</code>
                </td>
                <td>Mandatory if credential algorithm is ECDSA</td>
              </tr>
              <tr>
                <td>
                  <span className="c4-auth-control-name">X.509 certificate</span>
                  <span className="c4-auth-control-type c4-auth-type-certificate">
                    Certificate
                  </span>
                </td>
                <td>Identity binding and CA trust</td>
                <td>
                  <code>X509CertificateValidator.validate</code>
                </td>
                <td>When certificate_pem is present</td>
              </tr>
              <tr>
                <td>
                  <span className="c4-auth-control-name">Freshness</span>
                  <span className="c4-auth-control-type c4-auth-type-validation">
                    Validation
                  </span>
                </td>
                <td>Packet age versus max_age_seconds=30</td>
                <td>
                  <code>C4TrustService.assess</code>
                </td>
                <td>Mandatory</td>
              </tr>
              <tr>
                <td>
                  <span className="c4-auth-control-name">Replay</span>
                  <span className="c4-auth-control-type c4-auth-type-validation">
                    Validation
                  </span>
                </td>
                <td>Duplicate packet_id or non-increasing sequence</td>
                <td>
                  <code>C4TrustService.assess</code>
                </td>
                <td>Mandatory</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {results.length > 0 && (
        <section className="c4-auth-metrics" aria-label="Session metrics">
          <MetricCard
            label="HMAC assessments"
            value={hmacCount}
            variant="hmac"
            description="Credential ID starts with hmac"
          />
          <MetricCard
            label="ECDSA assessments"
            value={ecdsaCount}
            variant="ecdsa"
            description="Credential ID starts with ecdsa"
          />
          <MetricCard
            label="Integrity invalid"
            value={integrityInvalid}
            variant="integrity"
            description="INTEGRITY_INVALID reason code"
          />
        </section>
      )}

      {results.length === 0 && (
        <section className="c4-auth-empty" aria-live="polite">
          <div className="c4-auth-empty-icon" aria-hidden="true">
            !
          </div>
          <h3 className="c4-auth-empty-title">
            No session assessments yet
          </h3>
          <p className="c4-auth-empty-text">
            Use a sidebar scenario such as{' '}
            <strong>Run Valid Telemetry (HMAC)</strong> or{' '}
            <strong>Run Valid X.509 + ECDSA</strong>.
          </p>
        </section>
      )}
    </section>
  );
};

interface MetricCardProps {
  label: string;
  value: number;
  variant: 'hmac' | 'ecdsa' | 'integrity';
  description: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  variant,
  description,
}) => (
  <article className={`c4-auth-metric-card c4-auth-metric-${variant}`}>
    <div className="c4-auth-metric-top">
      <span className="c4-auth-metric-label">{label}</span>
      <span className="c4-auth-metric-indicator" aria-hidden="true" />
    </div>
    <div className="c4-auth-metric-value">{value.toLocaleString()}</div>
    <p className="c4-auth-metric-description">{description}</p>
  </article>
);
