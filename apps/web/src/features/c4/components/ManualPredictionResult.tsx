export interface ManualResult {
  label: string;
  score: number;
  warnings: string[];
  assumptions: Record<string, string>;
}

export default function ManualPredictionResult({ result }: { result: ManualResult }) {
  return (
    <div className="c4-ml-manual-result" style={{ marginTop: 20, padding: 20 }}>
      <h4>ML Model Prediction Result</h4>
      <p>Predicted Label: <strong>{result.label}</strong></p>
      <p>Anomaly Score (1 - P(Trusted)): <strong>{result.score.toFixed(4)}</strong></p>
      <p>Model class: {result.label}. This behavioral prediction does not establish device identity or confirm healthy telemetry.</p>
      {result.warnings.length > 0 && (
        <div role="alert" style={{ background: "#fef3c7", color: "#92400e", padding: 12 }}>
          <strong>Input-health warning (separate from model prediction)</strong>
          <ul>{result.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul>
        </div>
      )}
      
      
    </div>
  );
}
