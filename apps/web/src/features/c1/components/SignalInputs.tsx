import { FIELD_GROUPS, FIELDS, PRESETS } from "../constants";
import type { FeatureKey, FormValues } from "../types";

interface Props {
  values: FormValues;
  activePreset: string | null;
  autoDerive: boolean;
  running: boolean;
  disabled: boolean;
  onChange: (key: FeatureKey, raw: string) => void;
  onPreset: (id: string) => void;
  onAutoDerive: (on: boolean) => void;
  onRun: () => void;
  onRunBatch: () => void;
  onClear: () => void;
}

export function SignalInputs(p: Props) {
  return (
    <section className="c1-card">
      <header className="c1-card__head">
        <div>
          <span className="c1-eyebrow">01 / Input</span>
          <h2>Telemetry signals</h2>
          <p>Adjust the sample values and send them to the credibility model. Leave a box empty for a missing value.</p>
        </div>
        <span className="c1-pill">{FIELDS.length} features</span>
      </header>

      <div className="c1-presets" role="group" aria-label="Preset readings">
        {PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            className={`c1-chip ${p.activePreset === preset.id ? "is-active" : ""}`}
            onClick={() => p.onPreset(preset.id)}
            title={preset.hint}
          >
            {preset.name}
          </button>
        ))}
      </div>

      {FIELD_GROUPS.map((group) => (
        <fieldset key={group} className="c1-group">
          <legend>{group}</legend>
          <div className="c1-grid">
            {FIELDS.filter((f) => f.group === group).map((f) => (
              <label key={f.key} className="c1-field">
                <span>
                  {f.label}
                  {f.unit && <em> {f.unit}</em>}
                </span>
                <input
                  type="number"
                  inputMode="decimal"
                  step={f.step}
                  min={f.min}
                  max={f.max}
                  value={p.values[f.key]}
                  placeholder="missing"
                  onChange={(e) => p.onChange(f.key, e.target.value)}
                />
              </label>
            ))}
          </div>
        </fieldset>
      ))}

      <label className="c1-check">
        <input type="checkbox" checked={p.autoDerive} onChange={(e) => p.onAutoDerive(e.target.checked)} />
        Fill “Value minus baseline” from soil moisture and baseline mean
      </label>

      <div className="c1-actions">
        <button type="button" className="c1-btn c1-btn--primary" onClick={p.onRun} disabled={p.running || p.disabled}>
          {p.running ? "Running…" : "Run prediction"}
        </button>
        <button type="button" className="c1-btn" onClick={p.onRunBatch} disabled={p.running || p.disabled}>
          Run all presets (batch)
        </button>
        <button type="button" className="c1-btn c1-btn--ghost" onClick={p.onClear} disabled={p.running}>
          Clear
        </button>
      </div>
    </section>
  );
}
