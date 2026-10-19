
import React from 'react';
import '../../../styles/c4/c4-HowC4Works.css';

export const HowC4Works: React.FC = () => {
  return (
    <div className="c4-how">
      <header className="c4-how-header">
        <div>
          <div className="c4-how-eyebrow">
            GEO NEX / C4 TRUST ARCHITECTURE
          </div>
          <h3>How C4 Works</h3>
          <p>
            Verified from the current repository. This page describes
            code that exists today.
          </p>
        </div>

        <div className="c4-how-header-badge">
          <span className="c4-how-status-dot" />
          Runtime Overview
        </div>
      </header>

      <section className="c4-how-panel">
        <div className="c4-how-panel-heading">
          <div className="c4-how-section-icon">C4</div>
          <div>
            <h4>Purpose of C4</h4>
            <p>Trusted telemetry provenance and device attestation</p>
          </div>
        </div>

        <p className="c4-how-purpose-text">
          C4 is the trust gate for GeoNex telemetry. It decides whether
          a packet is authentic enough to enter C1. Cryptographic and
          identity checks are mandatory. Behavioral ML can only
          influence packets that already passed those checks.
        </p>

        <div className="c4-how-purpose-flow">
          <div className="c4-how-purpose-step">
            <span>01</span>
            <strong>Verify identity</strong>
            <small>Device and registration checks</small>
          </div>
          <div className="c4-how-purpose-arrow">→</div>
          <div className="c4-how-purpose-step">
            <span>02</span>
            <strong>Verify integrity</strong>
            <small>Cryptographic and packet checks</small>
          </div>
          <div className="c4-how-purpose-arrow">→</div>
          <div className="c4-how-purpose-step">
            <span>03</span>
            <strong>Assess behavior</strong>
            <small>ML after mandatory checks pass</small>
          </div>
        </div>
      </section>

      <section className="c4-how-panel">
        <div className="c4-how-panel-heading">
          <div className="c4-how-section-icon">RT</div>
          <div>
            <h4>Verified Runtime Path</h4>
            <p>Execution flow used by the Streamlit demonstration</p>
          </div>
        </div>

        <div className="c4-how-runtime">
          <div className="c4-how-runtime-step">
            <span className="c4-how-runtime-number">01</span>
            <div>
              <strong>Sidebar button</strong>
              <p>Operator triggers a demo scenario.</p>
            </div>
          </div>

          <div className="c4-how-runtime-connector">
            <span>↓</span>
          </div>

          <div className="c4-how-runtime-step">
            <span className="c4-how-runtime-number">02</span>
            <div>
              <strong>
                <code>C4DemoBackend.run_simulation()</code>
              </strong>
              <p>Starts the selected simulation.</p>
            </div>
          </div>

          <div className="c4-how-runtime-connector">
            <span>↓</span>
          </div>

          <div className="c4-how-runtime-step">
            <span className="c4-how-runtime-number">03</span>
            <div>
              <strong>
                <code>generate_scheduled_demo_telemetry()</code>
              </strong>
              <p>Generates demo telemetry packets.</p>
            </div>
          </div>

          <div className="c4-how-runtime-connector">
            <span>↓</span>
          </div>

          <div className="c4-how-runtime-step">
            <span className="c4-how-runtime-number">04</span>
            <div>
              <strong>
                <code>
                  C4TrustService.sign_packet()
                </code>{' '}
                or{' '}
                <code>
                  sign_packet_ecdsa()
                </code>
              </strong>
              <p>Signs packet data using the selected demo method.</p>
            </div>
          </div>

          <div className="c4-how-runtime-connector">
            <span>↓</span>
          </div>

          <div className="c4-how-runtime-step">
            <span className="c4-how-runtime-number">05</span>
            <div>
              <strong>
                <code>C4TelemetryGate.process()</code>
              </strong>
              <p>Passes the packet into the C4 processing gate.</p>
            </div>
          </div>

          <div className="c4-how-runtime-connector">
            <span>↓</span>
          </div>

          <div className="c4-how-runtime-step c4-how-runtime-step-highlight">
            <span className="c4-how-runtime-number">06</span>
            <div>
              <strong>
                <code>C4TrustService.assess()</code>
              </strong>
              <p>
                Evaluates mandatory security evidence before behavioral
                assessment.
              </p>
            </div>
          </div>

          <div className="c4-how-runtime-branch">
            <div className="c4-how-runtime-branch-line" />
            <div className="c4-how-runtime-branch-options">
              <div className="c4-how-runtime-option">
                <span className="c4-how-option-dot c4-how-option-ml" />
                <strong>Optional behavioral ML</strong>
                <p>
                  <code>C4BehavioralModelRunner</code>
                </p>
              </div>
              <div className="c4-how-runtime-option">
                <span className="c4-how-option-dot c4-how-option-quarantine" />
                <strong>Quarantine handling</strong>
                <p>
                  <code>QuarantineManager</code>
                </p>
              </div>
            </div>
          </div>

          <div className="c4-how-runtime-connector">
            <span>↓</span>
          </div>

          <div className="c4-how-runtime-step c4-how-runtime-step-result">
            <span className="c4-how-runtime-number">07</span>
            <div>
              <strong>
                <code>session_state.c4_results</code>
              </strong>
              <p>Assessment results are stored in Streamlit session memory.</p>
            </div>
          </div>
        </div>

        <div className="c4-how-runtime-note">
          <strong>Important:</strong> The sequence above represents the
          documented demo flow. Exact call order and optional branches
          should be confirmed against the current implementation.
        </div>
      </section>

      <section className="c4-how-panel">
        <div className="c4-how-panel-heading">
          <div className="c4-how-section-icon">IO</div>
          <div>
            <h4>What This Dashboard Does Not Use</h4>
            <p>Distinguishing the simulation from other GeoNex data paths</p>
          </div>
        </div>

        <div className="c4-how-not-used-grid">
          <div className="c4-how-not-used-item">
            <span className="c4-how-not-used-icon">01</span>
            <div>
              <strong>Physical device telemetry</strong>
              <p>Physical ESP32 or LoRa packets are not used by this demo.</p>
            </div>
          </div>

          <div className="c4-how-not-used-item">
            <span className="c4-how-not-used-icon">02</span>
            <div>
              <strong>Direct CSV reads</strong>
              <p>
                The dashboard does not directly load{' '}
                <code>experiments/c4/data/*.csv</code> for each scenario.
              </p>
            </div>
          </div>

          <div className="c4-how-not-used-item">
            <span className="c4-how-not-used-icon">03</span>
            <div>
              <strong>Direct PostgreSQL writes</strong>
              <p>
                The simulation path does not directly write to{' '}
                <code>telemetry_packets</code>.
              </p>
            </div>
          </div>
        </div>

        <div className="c4-how-separate-path">
          <div className="c4-how-separate-path-icon">DB</div>
          <div>
            <strong>Separate ingestion path</strong>
            <p>
              CSV files and saved models support offline training and
              the ML Model Explorer. PostgreSQL is used by{' '}
              <code>scripts/load_demo_simulation.py</code>, a separate
              ingestion path.
            </p>
          </div>
        </div>
      </section>

      <section className="c4-how-crypto-grid">
        <article className="c4-how-crypto-card c4-how-crypto-hmac">
          <div className="c4-how-crypto-heading">
            <div className="c4-how-crypto-icon">H</div>
            <div>
              <h4>HMAC-SHA256</h4>
              <p>Symmetric message authentication</p>
            </div>
          </div>

          <div className="c4-how-crypto-concept">
            <span>Sender</span>
            <strong>Shared secret</strong>
            <span>Verifier</span>
          </div>

          <ul className="c4-how-bullet-list">
            <li>Shared secret known to sender and verifier</li>
            <li>
              <code>C4TrustService.sign_packet()</code>
            </li>
            <li>Fast symmetric integrity check</li>
            <li>
              Dashboard demo secrets stay in memory and are never shown
            </li>
          </ul>

          <div className="c4-how-crypto-footer">
            Both parties use the shared secret to calculate and verify
            the message authentication code.
          </div>
        </article>

        <article className="c4-how-crypto-card c4-how-crypto-ecdsa">
          <div className="c4-how-crypto-heading">
            <div className="c4-how-crypto-icon">E</div>
            <div>
              <h4>ECDSA-SHA256 (P-256)</h4>
              <p>Asymmetric digital signatures</p>
            </div>
          </div>

          <div className="c4-how-crypto-concept">
            <span>Device</span>
            <strong>Private key → Public key</strong>
            <span>C4 verifier</span>
          </div>

          <ul className="c4-how-bullet-list">
            <li>
              Device private key signs; C4 verifies with the public key
            </li>
            <li>
              <code>sign_packet_ecdsa()</code>
            </li>
            <li>Usually paired with an X.509 device certificate</li>
            <li>Private keys are generated in memory for the demo only</li>
          </ul>

          <div className="c4-how-crypto-footer">
            The private key signs the packet. The corresponding public
            key verifies the signature.
          </div>
        </article>
      </section>

      <section className="c4-how-panel">
        <div className="c4-how-panel-heading">
          <div className="c4-how-section-icon">GL</div>
          <div>
            <h4>Glossary</h4>
            <p>Core terminology used in the C4 implementation</p>
          </div>
        </div>

        <div className="c4-how-table-wrapper">
          <table className="c4-how-table">
            <thead>
              <tr>
                <th>Term</th>
                <th>Meaning in this repository</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <code>TelemetryPacket</code>
                </td>
                <td>
                  Normalized packet contract in{' '}
                  <code>shared/contracts/telemetry.py</code>.
                </td>
              </tr>
              <tr>
                <td>Mandatory security</td>
                <td>
                  Identity, zone/hub, certificate, signature, freshness,
                  replay, attestation, and provenance checks.
                </td>
              </tr>
              <tr>
                <td>Behavioral score</td>
                <td>
                  Anomaly score calculated as{' '}
                  <code>1 - P(Trusted)</code> from the Random Forest.
                </td>
              </tr>
              <tr>
                <td>TRUSTED / ACCEPT</td>
                <td>
                  Mandatory checks passed and score below 0.70; eligible
                  for C1.
                </td>
              </tr>
              <tr>
                <td>UNTRUSTED / REJECT</td>
                <td>
                  A mandatory check failed; ML cannot override this
                  result.
                </td>
              </tr>
              <tr>
                <td>SUSPICIOUS / QUARANTINE</td>
                <td>
                  Mandatory checks passed but the ML score is greater
                  than or equal to 0.70.
                </td>
              </tr>
              <tr>
                <td>UNKNOWN / SECURITY_REVIEW</td>
                <td>
                  Evidence is missing or the ML score is unavailable.
                </td>
              </tr>
              <tr>
                <td>Session result</td>
                <td>
                  A row in Streamlit memory; lost when the session is
                  reset or cleared.
                </td>
              </tr>
              <tr>
                <td>Quarantine JSON</td>
                <td>
                  Evidence file; the dashboard uses a temporary folder
                  that is deleted after the relevant run closes.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <footer className="c4-how-footer">
        <span>GEO NEX / C4 TRUSTED TELEMETRY</span>
        <span>Architecture and runtime reference</span>
      </footer>
    </div>
  );
};
