import { useEffect, useState, type ReactNode } from 'react';
import './C2Page.css';

const API = 'http://127.0.0.1:8032';

type ModelInfo = {
  status: string;
  component: string;
  model_status: string;
  model_type: string;
};

type ModelDetails = {
  feature_count: number;
  features: string[];
  classes: string[];
};

type Prediction = {
  diagnosis: string;
  feature_count: number;
  class_probabilities: Record<string, number>;
};

type BackupResult = {
  verified: boolean;
  reason: string;
  maximum_deviation: number | null;
  verification_method: string;
  note: string;
};

type FeatureMap = Record<string, number>;

const initialFeatures: FeatureMap = {
  rainfall_mm: 3.8,
  soil_moisture_1: 32.8,
  soil_moisture_2: 34.9,
  tilt_x: 1.36,
  tilt_y: 0.7,
  vibration: 0.104,
  temperature_c: 24.8,
  battery_voltage: 3.954,
  rssi: -65.9,
  snr: 15,
  packet_loss_rate: 0.016,
  heartbeat_interval_sec: 58.4,
  last_heartbeat_age: 120,
  missed_heartbeat_count: 2,
  pre_silence_tilt_change: -0.162,
  pre_silence_vibration_change: 0.078,
  pre_silence_packet_loss_trend: 0.0005,
  pre_silence_battery_trend: -0.0069,
  deviation_from_pre_silence: 0.922,
  backup_reachable: 1,
  backup_response_time_ms: 573,
  backup_tilt_x: 1.52,
  backup_tilt_y: 0.84,
  backup_vibration: 0.145,
  primary_backup_deviation: 0.467,
};

const sensorFields = [
  'rainfall_mm',
  'soil_moisture_1',
  'soil_moisture_2',
  'tilt_x',
  'tilt_y',
  'vibration',
  'temperature_c',
  'battery_voltage',
  'rssi',
  'snr',
  'packet_loss_rate',
  'heartbeat_interval_sec',
  'last_heartbeat_age',
  'missed_heartbeat_count',
];

function label(value: string) {
  return value.replaceAll('_', ' ');
}

function pretty(value: string) {
  return label(value).replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    pulse: <><path d="M3 12h4l3-8 4 16 3-8h4" /></>,
    database: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></>,
    activity: <><path d="M3 12h4l2.5-7 5 14 2.5-7h4" /></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
    arrow: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
    refresh: <><path d="M20 7v5h-5" /><path d="M4 17v-5h5" /><path d="M5.6 9a7 7 0 0 1 11.6-2L20 12M4 12l2.8 5a7 7 0 0 0 11.6-2" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    warning: <><path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4m0 4h.01" /></>,
    sliders: <><path d="M4 21v-7m0-4V3m8 18v-9m0-4V3m8 18v-5m0-4V3" /><path d="M2 14h4m4-6h4m4 8h4" /></>,
  };

  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name] ?? paths.activity}
    </svg>
  );
}

function Panel({
  eyebrow,
  title,
  subtitle,
  action,
  children,
  className = '',
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`c2-panel ${className}`}>
      <div className="c2-panel-heading">
        <div>
          <span className="c2-panel-eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function Metric({
  icon,
  label: metricLabel,
  value,
  detail,
  tone,
}: {
  icon: string;
  label: string;
  value: string;
  detail: string;
  tone: 'teal' | 'blue' | 'amber' | 'slate';
}) {
  return (
    <article className="c2-metric">
      <div className={`c2-metric-icon c2-tone-${tone}`}>
        <Icon name={icon} size={19} />
      </div>
      <div className="c2-metric-copy">
        <span>{metricLabel}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
      <span className={`c2-metric-indicator c2-tone-${tone}`} />
    </article>
  );
}

function FeatureInput({
  name,
  value,
  onChange,
}: {
  name: string;
  value: number;
  onChange: (value: string) => void;
}) {
  return (
    <label className="c2-field">
      <span>{pretty(name)}</span>
      <input
        type="number"
        step="any"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function errorMessage(result: unknown) {
  if (typeof result === 'object' && result !== null && 'detail' in result) {
    const detail = (result as { detail: unknown }).detail;
    return typeof detail === 'string' ? detail : JSON.stringify(detail);
  }
  return JSON.stringify(result);
}

export function C2Page() {
  const [api, setApi] = useState<ModelInfo | null>(null);
  const [model, setModel] = useState<ModelDetails | null>(null);
  const [features, setFeatures] = useState<FeatureMap>(initialFeatures);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [backup, setBackup] = useState<BackupResult | null>(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [loadingBackup, setLoadingBackup] = useState(false);
  const [error, setError] = useState('');
  const [backupTolerance, setBackupTolerance] = useState(0.5);
  const [primary, setPrimary] = useState({
    tilt_x: 1.36,
    tilt_y: 0.7,
    vibration: 0.104,
  });
  const [secondary, setSecondary] = useState({
    tilt_x: 1.52,
    tilt_y: 0.84,
    vibration: 0.145,
  });
  const [backupReachable, setBackupReachable] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadStatus() {
      try {
        const [healthResponse, modelResponse] = await Promise.all([
          fetch(`${API}/health`),
          fetch(`${API}/models`),
        ]);

        if (!healthResponse.ok || !modelResponse.ok) {
          throw new Error('C2 API is not available.');
        }

        const [health, details] = await Promise.all([
          healthResponse.json(),
          modelResponse.json(),
        ]);

        if (active) {
          setApi(health);
          setModel(details);
        }
      } catch {
        if (active) {
          setApi(null);
          setModel(null);
        }
      }
    }

    void loadStatus();
    return () => {
      active = false;
    };
  }, []);

  async function runDiagnosis() {
    setLoadingPrediction(true);
    setError('');
    setPrediction(null);

    try {
      const response = await fetch(`${API}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features }),
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(errorMessage(result));
      }

      setPrediction(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not obtain a diagnosis.');
    } finally {
      setLoadingPrediction(false);
    }
  }

  async function verifyBackup() {
    setLoadingBackup(true);
    setError('');
    setBackup(null);

    try {
      const response = await fetch(`${API}/verify-backup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backup_reachable: backupReachable,
          primary_values: primary,
          backup_values: secondary,
          tolerance: backupTolerance,
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(errorMessage(result));
      }

      setBackup(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not verify backup telemetry.');
    } finally {
      setLoadingBackup(false);
    }
  }

  function updateFeature(name: string, value: string) {
    const numericValue = Number(value);
    if (value.trim() === '' || !Number.isFinite(numericValue)) return;
    setFeatures((current) => ({ ...current, [name]: numericValue }));
  }

  const statusText = api?.model_status === 'loaded' ? 'Ready' : 'Unavailable';
  const advancedFields = Object.keys(features).filter((name) => !sensorFields.includes(name));

  return (
    <main className="c2-dashboard">
      <header className="c2-hero">
        <div className="c2-hero-content">
          <div className="c2-kicker">
            <span className="c2-kicker-line" />
            GEONEX RESEARCH / COMPONENT 02
          </div>
          <h1>Device diagnostics<span>.</span></h1>
          <p>
            Monitor silent telemetry patterns, assess device health, and validate
            backup sensor readings from one workspace.
          </p>
          <div className="c2-hero-tags">
            <span><Icon name="activity" size={15} /> Telemetry analysis</span>
            <span><Icon name="shield" size={15} /> Backup verification</span>
          </div>
        </div>
        <div className="c2-hero-art" aria-hidden="true">
          <div className="c2-orbit c2-orbit-outer" />
          <div className="c2-orbit c2-orbit-middle" />
          <div className="c2-orbit c2-orbit-inner" />
          <div className="c2-orbit-core"><Icon name="pulse" size={30} /></div>
          <span className="c2-orbit-node c2-node-top" />
          <span className="c2-orbit-node c2-node-right" />
          <span className="c2-orbit-node c2-node-bottom" />
        </div>
        <div className={`c2-api-badge ${api ? 'is-online' : 'is-offline'}`}>
          <span className="c2-live-dot" />
          <span><strong>{api ? 'API connected' : 'API offline'}</strong><small>Local research service</small></span>
        </div>
      </header>

      <div className="c2-demo-note">
        <span className="c2-note-icon"><Icon name="warning" size={17} /></span>
        <p><strong>Research demonstration</strong> Preset readings are simulated. This workspace is not connected to live field hardware and does not issue validated safety alerts.</p>
      </div>

      <section className="c2-metrics" aria-label="C2 system status">
        <Metric
          icon="activity"
          label="C2 service"
          value={api ? 'Online' : 'Offline'}
          detail="Health endpoint"
          tone={api ? 'teal' : 'slate'}
        />
        <Metric
          icon="database"
          label="Diagnostic model"
          value={statusText}
          detail={model ? `${model.feature_count} input features` : 'Waiting for backend'}
          tone={model ? 'blue' : 'slate'}
        />
        <Metric
          icon="shield"
          label="Diagnosis classes"
          value={model ? String(model.classes.length) : '—'}
          detail={model ? 'Loaded from model service' : 'Model details unavailable'}
          tone="amber"
        />
        <Metric
          icon="pulse"
          label="Latest diagnosis"
          value={prediction ? pretty(prediction.diagnosis) : 'Not run'}
          detail={prediction ? `${prediction.feature_count} features processed` : 'Run an analysis to begin'}
          tone={prediction ? 'teal' : 'slate'}
        />
      </section>

      {error && (
        <div className="c2-error" role="alert">
          <Icon name="warning" size={19} />
          <div><strong>Request failed</strong><p>{error}</p></div>
        </div>
      )}

      <div className="c2-content-grid">
        <div className="c2-primary-column">
          <Panel
            eyebrow="01 / INPUT"
            title="Telemetry signals"
            subtitle="Adjust the sample values and send them to the diagnostic model."
            action={<span className="c2-count-pill">{sensorFields.length} signals</span>}
          >
            <div className="c2-signal-grid">
              {sensorFields.map((name) => (
                <FeatureInput
                  key={name}
                  name={name}
                  value={features[name]}
                  onChange={(value) => updateFeature(name, value)}
                />
              ))}
            </div>

            <details className="c2-advanced">
              <summary>
                <span><Icon name="sliders" size={17} /> Advanced model features</span>
                <span className="c2-count-pill">{advancedFields.length} features</span>
              </summary>
              <div className="c2-signal-grid c2-advanced-grid">
                {advancedFields.map((name) => (
                  <FeatureInput
                    key={name}
                    name={name}
                    value={features[name]}
                    onChange={(value) => updateFeature(name, value)}
                  />
                ))}
              </div>
            </details>

            <div className="c2-form-actions">
              <button
                type="button"
                className="c2-button c2-button-primary"
                onClick={() => void runDiagnosis()}
                disabled={loadingPrediction || !api}
              >
                {loadingPrediction ? 'Analyzing signals…' : 'Run diagnosis'}
                {!loadingPrediction && <Icon name="arrow" size={17} />}
              </button>
              <button
                type="button"
                className="c2-button c2-button-secondary"
                onClick={() => {
                  setFeatures(initialFeatures);
                  setPrediction(null);
                  setError('');
                }}
              >
                <Icon name="refresh" size={16} /> Reset sample
              </button>
              {!api && <span className="c2-action-hint">Start the C2 service to run analysis.</span>}
            </div>
          </Panel>

          <Panel
            eyebrow="02 / ANALYSIS"
            title="Diagnostic result"
            subtitle="Prediction and class probabilities returned by the C2 model."
            className="c2-result-panel"
          >
            {!prediction ? (
              <div className="c2-empty-state">
                <div className="c2-empty-icon"><Icon name="pulse" size={24} /></div>
                <strong>Ready when you are</strong>
                <p>Submit the current telemetry signals to see the model diagnosis and class probabilities here.</p>
              </div>
            ) : (
              <div className="c2-result-content">
                <div className={`c2-diagnosis-card ${prediction.diagnosis === 'normal' ? 'is-normal' : 'is-attention'}`}>
                  <div className="c2-diagnosis-icon"><Icon name={prediction.diagnosis === 'normal' ? 'check' : 'warning'} size={22} /></div>
                  <div>
                    <span>Predicted diagnosis</span>
                    <strong>{pretty(prediction.diagnosis)}</strong>
                    <small>{prediction.feature_count} input features processed</small>
                  </div>
                  <span className="c2-result-label">{prediction.diagnosis === 'normal' ? 'NOMINAL' : 'REVIEW'}</span>
                </div>
                <div className="c2-probability-heading"><strong>Class probabilities</strong><span>Model output</span></div>
                <div className="c2-probabilities">
                  {Object.entries(prediction.class_probabilities).map(([name, probability]) => {
                    const percentage = Math.max(0, Math.min(100, probability * 100));
                    return (
                      <div className="c2-probability-row" key={name}>
                        <div className="c2-probability-label"><span>{pretty(name)}</span><strong>{percentage.toFixed(1)}%</strong></div>
                        <div className="c2-progress-track" role="progressbar" aria-label={`${pretty(name)} probability`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percentage}>
                          <span style={{ width: `${percentage}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
                <p className="c2-disclaimer">Model probabilities are not calibrated real-world landslide probabilities and do not prove a physical fault.</p>
              </div>
            )}
          </Panel>
        </div>

        <aside className="c2-secondary-column">
          <Panel
            eyebrow="03 / REDUNDANCY"
            title="Backup verification"
            subtitle="Compare primary and backup telemetry using the deterministic verifier."
          >
            <label className={`c2-reachability ${backupReachable ? 'is-reachable' : 'is-unreachable'}`}>
              <span className="c2-reach-icon"><Icon name={backupReachable ? 'check' : 'warning'} size={17} /></span>
              <span><strong>Backup sensor</strong><small>{backupReachable ? 'Reachable for this simulation' : 'Marked unavailable'}</small></span>
              <input type="checkbox" checked={backupReachable} onChange={(event) => setBackupReachable(event.target.checked)} />
            </label>

            <div className="c2-compare-grid">
              <div className="c2-compare-group">
                <div className="c2-compare-heading"><span className="c2-compare-dot primary-dot" />Primary</div>
                {Object.keys(primary).map((name) => (
                  <FeatureInput
                    key={name}
                    name={name}
                    value={primary[name as keyof typeof primary]}
                    onChange={(value) => {
                      const numericValue = Number(value);
                      if (value.trim() !== '' && Number.isFinite(numericValue)) {
                        setPrimary((current) => ({ ...current, [name]: numericValue }));
                      }
                    }}
                  />
                ))}
              </div>
              <div className="c2-compare-group">
                <div className="c2-compare-heading"><span className="c2-compare-dot backup-dot" />Backup</div>
                {Object.keys(secondary).map((name) => (
                  <FeatureInput
                    key={name}
                    name={name}
                    value={secondary[name as keyof typeof secondary]}
                    onChange={(value) => {
                      const numericValue = Number(value);
                      if (value.trim() !== '' && Number.isFinite(numericValue)) {
                        setSecondary((current) => ({ ...current, [name]: numericValue }));
                      }
                    }}
                  />
                ))}
              </div>
            </div>

            <FeatureInput
              name="comparison_tolerance"
              value={backupTolerance}
              onChange={(value) => {
                const numericValue = Number(value);
                if (value.trim() !== '' && Number.isFinite(numericValue) && numericValue >= 0) {
                  setBackupTolerance(numericValue);
                }
              }}
            />

            <button
              type="button"
              className="c2-button c2-button-dark c2-full-button"
              onClick={() => void verifyBackup()}
              disabled={loadingBackup || !api}
            >
              {loadingBackup ? 'Verifying telemetry…' : 'Verify backup readings'}
              {!loadingBackup && <Icon name="arrow" size={17} />}
            </button>

            {backup && (
              <div className={`c2-backup-result ${backup.verified ? 'is-verified' : 'is-unverified'}`} aria-live="polite">
                <div className="c2-backup-result-heading">
                  <span className="c2-result-icon"><Icon name={backup.verified ? 'check' : 'warning'} size={18} /></span>
                  <div><strong>{pretty(backup.reason)}</strong><small>{backup.verified ? 'Verification passed' : 'Verification did not pass'}</small></div>
                </div>
                <dl>
                  <div><dt>Maximum deviation</dt><dd>{backup.maximum_deviation == null ? 'Not available' : backup.maximum_deviation.toFixed(3)}</dd></div>
                  <div><dt>Method</dt><dd>{pretty(backup.verification_method)}</dd></div>
                </dl>
                <p>{backup.note}</p>
              </div>
            )}
          </Panel>

          <Panel
            eyebrow="04 / MODEL"
            title="Model profile"
            subtitle="Metadata reported by the C2 service."
          >
            {model ? (
              <div className="c2-model-profile">
                <div className="c2-model-summary">
                  <div className="c2-model-icon"><Icon name="database" size={20} /></div>
                  <div><strong>{model.feature_count === 25 ? 'Random Forest Pipeline' : 'Loaded Pipeline'}</strong><small>Diagnostic classifier</small></div>
                </div>
                <div className="c2-model-stats">
                  <div><span>Input features</span><strong>{model.feature_count}</strong></div>
                  <div><span>Classes</span><strong>{model.classes.length}</strong></div>
                </div>
                <div className="c2-class-list">
                  <span>SUPPORTED CLASSES</span>
                  <div>{model.classes.map((name) => <span key={name}>{pretty(name)}</span>)}</div>
                </div>
              </div>
            ) : (
              <div className="c2-model-unavailable">
                <span className="c2-model-icon"><Icon name="database" size={20} /></span>
                <div><strong>Model details unavailable</strong><p>Connect the C2 backend to load the model profile and supported classes.</p></div>
              </div>
            )}
          </Panel>
        </aside>
      </div>

      <footer className="c2-footer">
        <span><Icon name="shield" size={15} /> GeoNex C2 · Research demonstration</span>
        <span>Simulation output is not a validated safety alert.</span>
      </footer>
    </main>
  );
}
