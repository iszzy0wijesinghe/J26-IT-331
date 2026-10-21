/** @format */

import { useEffect, useState } from "react";
import {
  generateOperationalM5,
  listGoldenDevices,
  getLatestGoldenObservation,
  type M5OperationalResponse,
} from "../api/c3M5Api";
import C3M5ForecastResults from "../components/C3M5ForecastResults";
import "../styles/c3ActiveForecasting.css";

function localInputToIso(value: string): string {
  const parsed = new Date(value);
  if (!value || Number.isNaN(parsed.getTime()))
    throw new Error("Enter a valid date and time.");
  return parsed.toISOString();
}
export function C3ActiveForecasting() {
  const [devices, setDevices] = useState<string[]>([]);
  const [device, setDevice] = useState("");
  const [origin, setOrigin] = useState("");
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [originLoading, setOriginLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<M5OperationalResponse | null>(null);
  useEffect(() => {
    let active = true;
    listGoldenDevices()
      .then((items) => {
        if (active) {
          setDevices(items);
          setDevice((v) => v || items[0] || "");
        }
      })
      .catch((e) => {
        if (active)
          setError(
            e instanceof Error
              ? e.message
              : "Cannot load Golden Database devices.",
          );
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!device) {
      setOrigin("");
      return;
    }
    let active = true;
    setOriginLoading(true);
    getLatestGoldenObservation(device)
      .then((timestamp) => {
        if (active) {
          const date = new Date(timestamp);
          const local = new Date(
            date.getTime() - date.getTimezoneOffset() * 60000,
          );
          setOrigin(local.toISOString().slice(0, 19));
          setTarget("");
          setResult(null);
        }
      })
      .catch((e) => {
        if (active)
          setError(
            e instanceof Error ? e.message : "Cannot load latest observation.",
          );
      })
      .finally(() => {
        if (active) setOriginLoading(false);
      });
    return () => {
      active = false;
    };
  }, [device]);
  async function run() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      if (!device) throw new Error("Select a Golden Database device.");
      const payload = {
        device_id: device,
        forecast_origin: localInputToIso(origin),
        ...(target ? { target_timestamp: localInputToIso(target) } : {}),
      };
      const response = await generateOperationalM5(payload);
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Forecast failed.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="c3-active-forecasting">
      <section className="c3-af-intro">
        <div>
          <span className="section-overline">
            COMPONENT 03 · GOLDEN DATABASE
          </span>
          <h2>Operational sensor forecasting</h2>
          <p>
            Use Golden Database observations as model inputs. Training dataset
            selection is not required.
          </p>
        </div>
        <span className="c3-af-research-badge">SYNTHETIC RESEARCH</span>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">FORECAST CONFIGURATION</span>
            <h2>Choose device and date/time</h2>
          </div>
        </div>
        <p className="c3-af-description">
          Forecast origin defaults to the latest actual Golden Database
          observation (not the current clock time). Optional target time must be
          exactly +15, +30 or +60 minutes for the currently available
          checkpoint. Leave it blank to display all three.
        </p>
        <div className="c3-af-form">
          <label className="c3-af-field">
            <span>Golden Database device</span>
            <select
              value={device}
              onChange={(e) => {
                setDevice(e.target.value);
                setResult(null);
              }}
              disabled={busy}>
              <option value="">Select device</option>
              {devices.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
          <label className="c3-af-field">
            <span>Forecast origin (your local time)</span>
            <input
              type="datetime-local"
              step="1"
              value={origin}
              onChange={(e) => {
                setOrigin(e.target.value);
                setResult(null);
              }}
              disabled={busy}
            />
          </label>
          <label className="c3-af-field">
            <span>Target date/time (optional)</span>
            <input
              type="datetime-local"
              step="1"
              value={target}
              onChange={(e) => {
                setTarget(e.target.value);
                setResult(null);
              }}
              disabled={busy}
            />
          </label>
        </div>
        <div className="c3-af-actions">
          <button
            type="button"
            className="c3-af-generate-button"
            onClick={() => void run()}
            disabled={busy || originLoading || !device || !origin}>
            {busy
              ? "Generating..."
              : originLoading
                ? "Loading observations..."
                : "Generate model forecasts"}
          </button>
        </div>
        {error && (
          <p className="c3-af-error" role="alert">
            {error}
          </p>
        )}
      </section>
      {result && <C3M5ForecastResults result={result} />}
      <section className="panel c3-af-limitation">
        <strong>Research boundaries</strong>
        <p>
          The currently available checkpoint forecasts seven sensors at fixed
          horizons only. Arbitrary timestamps, landslide risk classification,
          and operational alerts require separately developed and validated
          models and decision logic. Predictions are not emergency warnings.
        </p>
      </section>
    </div>
  );
}
