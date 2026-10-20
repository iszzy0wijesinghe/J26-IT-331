import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, c1Api } from "../api/c1Client";
import { MOCK_RECENT } from "../constants";
import type {
  Connection, HealthResponse, Metrics, ModelInfo, Observation, PredictResponse, RecentPrediction,
} from "../types";

const HEALTH_POLL_MS = 10_000;

/** All C1 API state in one place: connection, model info, metrics, last result, recent table. */
export function useC1() {
  const [connection, setConnection] = useState<Connection>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [recent, setRecent] = useState<RecentPrediction[]>(MOCK_RECENT);
  const [response, setResponse] = useState<PredictResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const alive = useRef(true);

  const loadRecent = useCallback(async () => {
    try {
      const rows = await c1Api.recent(10);
      if (alive.current) setRecent(rows.length ? rows : []);
    } catch {
      /* table keeps what it has */
    }
  }, []);

  const loadModelDetails = useCallback(async () => {
    const [info, m] = await Promise.allSettled([c1Api.model(), c1Api.metrics()]);
    if (!alive.current) return;
    if (info.status === "fulfilled") setModel(info.value);
    if (m.status === "fulfilled") setMetrics(m.value);
    await loadRecent();
  }, [loadRecent]);

  const checkHealth = useCallback(async () => {
    try {
      const h = await c1Api.health();
      if (!alive.current) return;
      setHealth(h);
      const next: Connection = h.model_loaded ? "online" : "degraded";
      setConnection((prev) => {
        if (prev !== next && next === "online") void loadModelDetails();
        return next;
      });
    } catch {
      if (!alive.current) return;
      setHealth(null);
      setConnection("offline");
      setRecent((rows) => (rows.some((r) => r.source === "api") ? rows : MOCK_RECENT));
    }
  }, [loadModelDetails]);

  useEffect(() => {
    alive.current = true;
    void checkHealth();
    const timer = window.setInterval(() => void checkHealth(), HEALTH_POLL_MS);
    return () => {
      alive.current = false;
      window.clearInterval(timer);
    };
  }, [checkHealth]);

  /** One observation or a batch. Returns true when the API answered. */
  const predict = useCallback(
    async (input: Observation | Observation[]): Promise<boolean> => {
      setRunning(true);
      setError(null);
      try {
        const res = await c1Api.predict(input);
        if (!alive.current) return false;
        setResponse(res);
        setConnection("online");
        await loadRecent();
        return true;
      } catch (err) {
        if (!alive.current) return false;
        setError(err instanceof ApiError ? err.message : "Prediction failed.");
        if (err instanceof ApiError && err.status === null) setConnection("offline");
        return false;
      } finally {
        if (alive.current) setRunning(false);
      }
    },
    [loadRecent],
  );

  return { connection, health, model, metrics, recent, response, running, error, predict, refresh: checkHealth };
}
