import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import C1Page from "../pages/C1Page";
import { FEATURE_KEYS } from "../types";

const MODEL = { name: "C1", version: "v1", trained_at: null, format: "xgboost-json", objective: "multi:softprob", n_features: 18,
  features: [...FEATURE_KEYS], classes: ["CLEAN", "ANOMALY", "VALID_EVENT"], class_order_source: "meta file", class_order_verified: true };
const METRICS = { available: true, macro_f1: 0.91, anomaly_recall: 0.83, valid_event_recall: 0.88, evaluated_on: "test split" };
const PREDICTION = { model_version: "v1", count: 1, latency_ms: 4.2, results: [
  { label: "VALID_EVENT", confidence: 0.87, probabilities: { CLEAN: 0.08, ANOMALY: 0.05, VALID_EVENT: 0.87 }, missing_features: [] }] };

const json = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
let calls: { url: string; init?: RequestInit }[] = [];

function mockApi(overrides: Record<string, () => Promise<Response>> = {}) {
  vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => {
    calls.push({ url, init });
    const path = url.replace("http://127.0.0.1:8033", "");
    const key = Object.keys(overrides).find((k) => path.startsWith(k));
    if (key) return overrides[key]();
    if (path.startsWith("/health")) return json({ status: "ok", model_loaded: true, model_version: "v1", uptime_s: 3, error: null });
    if (path.startsWith("/models")) return json(MODEL);
    if (path.startsWith("/metrics")) return json(METRICS);
    if (path.startsWith("/predictions/recent")) return json([]);
    if (path.startsWith("/predict")) return json(PREDICTION);
    return json({}, 404);
  }));
}

beforeEach(() => { calls = []; });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("C1Page", () => {
  it("shows the offline state and mock rows when the API is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))));
    render(<C1Page />);
    expect(await screen.findByText("API offline")).toBeTruthy();
    expect(screen.getByText(/these rows are mock data/i)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Run prediction" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows metrics from the API and sends all 18 features on predict", async () => {
    mockApi();
    render(<C1Page />);
    expect(await screen.findByText("API connected")).toBeTruthy();
    expect(await screen.findByText("91.0%")).toBeTruthy();      // macro f1 from /metrics
    expect(screen.getByText("83.0%")).toBeTruthy();
    expect(screen.getByText("88.0%")).toBeTruthy();
    expect(screen.getAllByText("18").length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: "Run prediction" }));
    expect(await screen.findByText("Valid environmental event")).toBeTruthy();
    expect(screen.getByText("87.0%", { selector: "strong" })).toBeTruthy();

    const post = calls.find((c) => c.url.endsWith("/predict"))!;
    const body = JSON.parse(String(post.init!.body));
    expect(Object.keys(body).sort()).toEqual([...FEATURE_KEYS].sort());
    expect(body.value).toBe(32.8);
  });

  it("sends null for an emptied box and fills value minus baseline automatically", async () => {
    mockApi();
    render(<C1Page />);
    await screen.findByText("API connected");
    const soil = screen.getByLabelText(/Soil moisture/) as HTMLInputElement;
    await userEvent.clear(soil); await userEvent.type(soil, "40");
    expect((screen.getByLabelText(/^Value minus baseline/) as HTMLInputElement).value).toBe("7.3");   // 40 - 32.7
    await userEvent.clear(screen.getByLabelText(/Rain 1 h/));
    await userEvent.click(screen.getByRole("button", { name: "Run prediction" }));
    await screen.findByText("Valid environmental event");
    const body = JSON.parse(String(calls.find((c) => c.url.endsWith("/predict"))!.init!.body));
    expect(body.rain_1h_mm).toBeNull(); expect(body.value).toBe(40);
  });

  it("blocks out-of-range input before calling the API", async () => {
    mockApi();
    render(<C1Page />);
    await screen.findByText("API connected");
    const frac = screen.getByLabelText(/Neighbours rising/);
    await userEvent.clear(frac); await userEvent.type(frac, "1.5");
    await userEvent.click(screen.getByRole("button", { name: "Run prediction" }));
    expect(await screen.findByText(/must be at most 1/)).toBeTruthy();
    expect(calls.some((c) => c.url.endsWith("/predict"))).toBe(false);
  });

  it("shows the API's validation error text", async () => {
    mockApi({ "/predict": () => json({ detail: [{ loc: ["body", "dt_s"], msg: "Input should be greater than 0" }] }, 422) });
    render(<C1Page />);
    await screen.findByText("API connected");
    await userEvent.click(screen.getByRole("button", { name: "Run prediction" }));
    expect(await screen.findByText(/dt_s: Input should be greater than 0/)).toBeTruthy();
  });

  it("runs all presets as one batch request", async () => {
    mockApi({ "/predict": () => json({ ...PREDICTION, count: 4, results: Array(4).fill(PREDICTION.results[0]) }) });
    render(<C1Page />);
    await screen.findByText("API connected");
    await userEvent.click(screen.getByRole("button", { name: /Run all presets/ }));
    await waitFor(() => expect(screen.getByText("Batch result")).toBeTruthy());
    const body = JSON.parse(String(calls.find((c) => c.url.endsWith("/predict"))!.init!.body));
    expect(Array.isArray(body) && body.length === 4).toBe(true);
  });

  it("warns when the class order is not confirmed", async () => {
    mockApi({ "/models": () => json({ ...MODEL, class_order_source: "default", class_order_verified: false }) });
    render(<C1Page />);
    expect(await screen.findByText(/Class order is not confirmed/)).toBeTruthy();
  });
});
