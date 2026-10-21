import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { C1_API_BASE } from "../api/c1Client";

interface HistoryData {
  train_loss: number[];
  val_loss: number[];
  metric: string;
}

interface ChartPoint {
  epoch: number;
  train: number;
  val: number;
}

export function TrainingChart() {
  const [data, setData] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${C1_API_BASE}/training-history`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load training history");
        return res.json();
      })
      .then((history: HistoryData) => {
        const chartData = history.train_loss.map((train, i) => ({
          epoch: i + 1,
          train: Number(train.toFixed(4)),
          val: Number((history.val_loss[i] ?? train).toFixed(4)),
        }));
        setData(chartData);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ marginTop: "1rem" }}>Loading training chart...</div>;
  if (error) return <div style={{ marginTop: "1rem", color: "#b91c1c" }}>Chart error: {error}</div>;

  return (
    <div
      style={{
        marginTop: "1.5rem",
        border: "1px solid #e5e7eb",
        borderRadius: "0.75rem",
        padding: "1.5rem",
        background: "white",
      }}
    >
      <h3 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.25rem" }}>
        Training progress (XGBoost log loss)
      </h3>
      <p style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: "1rem" }}>
        Lower is better. Each point is one boosting round. A widening gap between the two curves may indicate overfitting.
      </p>

      <div style={{ width: "100%", height: 360 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="epoch"
              label={{ value: "Boosting round", position: "insideBottom", offset: -10 }}
            />
            <YAxis
              label={{ value: "Log loss", angle: -90, position: "insideLeft" }}
              domain={["auto", "auto"]}
            />
            <Tooltip />
            <Legend verticalAlign="top" height={36} />
            <Line
              type="monotone"
              dataKey="train"
              name="Training loss"
              stroke="#0f766e"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="val"
              name="Validation loss"
              stroke="#b91c1c"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}