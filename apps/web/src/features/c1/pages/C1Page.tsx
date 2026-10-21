import { useMemo, useRef, useState } from "react";
import { C1_API_BASE } from "../api/c1Client";
import { MetricCard } from "../components/MetricCard";
import { ChartIcon, LayersIcon, PulseIcon, ShieldIcon, WarnIcon } from "../components/icons";
import { RecentTable } from "../components/RecentTable";
import { ResultPanel } from "../components/ResultPanel";
import { SignalInputs } from "../components/SignalInputs";
import { PRESETS } from "../constants";
import { useC1 } from "../hooks/useC1";
import { emptyForm, formFromObservation, parseForm, setField } from "../observation";
import type { Connection, FeatureKey, FormValues } from "../types";
import "../c1.css";

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${(v * 100).toFixed(1)}%`);

const CONNECTION_TEXT: Record<Connection, [string, string]> = {
  checking: ["Checking API", "Contacting the local research service"],
  online: ["API connected", "Local research service"],
  degraded: ["Model not loaded", "API is up, the model is not"],
  offline: ["API offline", `Expected at ${C1_API_BASE}`],
};

function C1Page() {
  const c1 = useC1();
  const [form, setForm] = useState<FormValues>(() => formFromObservation(PRESETS[0].values));
  const [activePreset, setActivePreset] = useState<string | null>(PRESETS[0].id);
  const [autoDerive, setAutoDerive] = useState(true);
  const [problems, setProblems] = useState<string[]>([]);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [csvUploading, setCsvUploading] = useState(false);
  const [csvMessage, setCsvMessage] = useState<string | null>(null);

  const [connLabel, connNote] = CONNECTION_TEXT[c1.connection];
  const metrics = c1.metrics;
  const latestLabel = c1.response?.results[0]?.label ?? "No run yet";
  const apiBlocked = c1.connection === "offline" || c1.connection === "degraded";

  const metricNote = useMemo(
    () => (metrics?.available ? metrics.evaluated_on ?? "Held-out evaluation" : "Add metrics to the model meta file"),
    [metrics],
  );

  function onChange(key: FeatureKey, raw: string) {
    setActivePreset(null);
    setProblems([]);
    setForm((f) => setField(f, key, raw, autoDerive));
  }

  function onPreset(id: string) {
    const preset = PRESETS.find((p) => p.id === id);
    if (!preset) return;
    setActivePreset(id);
    setProblems([]);
    setForm(formFromObservation(preset.values));
  }

  async function onRun() {
    const { observation, problems: found } = parseForm(form);
    setProblems(found);
    if (observation) await c1.predict(observation);
  }

  async function onRunBatch() {
    setProblems([]);
    await c1.predict(PRESETS.map((p) => p.values));
  }

  async function onCsvUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setCsvMessage(null);
    setCsvUploading(true);
    setProblems([]);

    try {
      await c1.predictCsv(file);
      setCsvMessage(`Processed ${file.name} successfully.`);
    } catch (err: any) {
      setCsvMessage(`Upload failed: ${err.message}`);
    } finally {
      setCsvUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  return (
    <div className="c1-page">
      <section className="c1-hero">
        <div className="c1-hero__text">
          <span className="c1-hero__eyebrow">GeoNex research / Component 01</span>
          <h1>Data credibility<span>.</span></h1>
          <p>Classify each sensor reading as clean, anomalous or a valid environmental event, using rainfall, temporal and neighbour context.</p>
          <div className="c1-hero__tags">
            <span><PulseIcon /> Context-aware classification</span>
            <span><ShieldIcon /> XGBoost model</span>
          </div>
        </div>
        <div className={`c1-conn c1-conn--${c1.connection}`}>
          <i />
          <div><strong>{connLabel}</strong><small>{connNote}</small></div>
        </div>
      </section>

      <div className="c1-notice">
        <WarnIcon />
        <div>
          <strong>Research demonstration</strong> Preset readings are simulated. This workspace is not connected to live field hardware and does not issue validated safety alerts.
        </div>
      </div>

      <div className="c1-stats">
        <MetricCard icon={<ChartIcon />} tone="teal" label="Macro-F1" value={pct(metrics?.macro_f1)} note={metricNote} />
        <MetricCard icon={<ShieldIcon />} tone="red" label="ANOMALY recall" value={pct(metrics?.anomaly_recall)} note="Faults that were caught" />
        <MetricCard icon={<PulseIcon />} tone="blue" label="VALID_EVENT recall" value={pct(metrics?.valid_event_recall)} note="Real events kept as valid" />
        <MetricCard icon={<LayersIcon />} tone="amber" label="Total features" value={String(c1.model?.n_features ?? 18)} note={c1.model ? `Model ${c1.model.version}` : "Model input columns"} />
      </div>

      <div className="c1-layout">
        <SignalInputs
          values={form}
          activePreset={activePreset}
          autoDerive={autoDerive}
          running={c1.running}
          disabled={apiBlocked}
          onChange={onChange}
          onPreset={onPreset}
          onAutoDerive={setAutoDerive}
          onRun={onRun}
          onRunBatch={onRunBatch}
          onClear={() => { setForm(emptyForm()); setActivePreset(null); setProblems([]); }}
        />
        <div className="c1-side">
          <ResultPanel
            response={c1.response}
            running={c1.running}
            error={c1.error}
            problems={problems}
            connection={c1.connection}
            classOrderVerified={c1.model ? c1.model.class_order_verified : null}
          />
          <div className="c1-latest">Latest label <strong>{latestLabel}</strong></div>
        </div>
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <h3>Batch CSV Upload</h3>
        <p style={{ fontSize: "0.9rem", color: "#666", marginBottom: "0.5rem" }}>
          Upload a CSV containing multiple observations (must include feature columns). The model will predict all rows in one batch.
        </p>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            type="button"
            className="c1-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={csvUploading || apiBlocked}
          >
            {csvUploading ? "Processing..." : "Upload CSV"}
          </button>
          <input
            type="file"
            accept=".csv"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={onCsvUpload}
          />
          {csvMessage && <span style={{ fontSize: "0.9rem", color: csvMessage.startsWith("Upload failed") ? "red" : "green" }}>{csvMessage}</span>}
        </div>
      </div>

      <RecentTable rows={c1.recent} offline={c1.connection === "offline"} />
    </div>
  );
}

// both export styles, so it works with whichever one your router already imports
export { C1Page };
export default C1Page;