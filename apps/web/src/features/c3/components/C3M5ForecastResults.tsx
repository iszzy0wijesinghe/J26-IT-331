/** @format */

import type { M5OperationalResponse } from "../api/c3M5Api";
const LABELS: Record<string, string> = {
  soil_moisture_pct: "Soil moisture (%)",
  rainfall_proxy_counts: "Rainfall proxy (counts)",
  tilt_deg: "Ground tilt (°)",
  vibration_g: "Vibration (g)",
  fsr_adc: "Force sensor (ADC)",
  air_temperature_c: "Air temperature (°C)",
  humidity_pct: "Humidity (%)",
};
export default function C3M5ForecastResults({
  result,
}: {
  result: M5OperationalResponse;
}) {
  return (
    <section className="panel" aria-label="Model predictions">
      <div className="panel-heading">
        <div>
          <span className="section-overline">MODEL OUTPUT</span>
          <h2>Seven-sensor predictions</h2>
        </div>
      </div>
      <p className="c3-af-description">
        {result.model} · {result.sequence_length} Golden Database observations ·{" "}
        {result.model_version}
      </p>
      <div className="c3-af-history">
        <table>
          <thead>
            <tr>
              <th>Sensor</th>
              {result.predictions.map((p) => (
                <th key={p.horizon_minutes}>
                  +{p.horizon_minutes} min
                  <br />
                  {new Date(p.target_timestamp).toLocaleString()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.sensor_features.map((sensor) => (
              <tr key={sensor}>
                <td>{LABELS[sensor] ?? sensor}</td>
                {result.predictions.map((p) => (
                  <td key={p.horizon_minutes}>
                    {typeof p.sensors[sensor] === "number"
                      ? p.sensors[sensor].toFixed(
                          sensor === "vibration_g" ? 4 : 2,
                        )
                      : "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="c3-af-description">
        <strong>Landslide risk:</strong> Not available — no validated risk
        model. <strong>Alerts:</strong> Not available — no validated decision
        engine.
      </p>
      <p className="c3-af-description">{result.warning}</p>
    </section>
  );
}
