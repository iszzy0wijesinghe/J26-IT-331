/**
 * F10.4.1: explicit synthetic-only training admission.
 *
 * @format
 */

import { useEffect, useState } from "react";
import {
  c3ExperimentApi,
  type C3ExperimentAdmission,
} from "../api/c3TrainingApi";

type Props = { datasetId: string; onChanged?: () => void };
export function C3SyntheticExperiment({ datasetId, onChanged }: Props) {
  const [admission, setAdmission] = useState<C3ExperimentAdmission | null>(
    null,
  );
  const [researcher, setResearcher] = useState("");
  const [reason, setReason] = useState(
    "Synthetic dataset for C3 pipeline and forecasting model comparison testing.",
  );
  const [declared, setDeclared] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    setAdmission(null);
    setError("");
    setNotice("");
    setDeclared(false);
    setAcknowledged(false);
    if (datasetId)
      void c3ExperimentApi
        .admission(datasetId)
        .then((v) => {
          if (active) setAdmission(v);
        })
        .catch((e) => {
          if (active) setError(String(e));
        });
    return () => {
      active = false;
    };
  }, [datasetId]);
  async function run(action: "authorize" | "revoke") {
    if (!datasetId || busy) return;
    if (
      action === "authorize" &&
      (!declared ||
        !acknowledged ||
        researcher.trim().length < 2 ||
        reason.trim().length < 12)
    )
      return;
    if (
      !window.confirm(
        action === "authorize"
          ? "Authorize this dataset for SYNTHETIC EXPERIMENTS ONLY? This does not verify provenance or approve field use."
          : "Revoke synthetic experiment authorization?",
      )
    )
      return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (action === "authorize") {
        await c3ExperimentApi.prepare(datasetId);
        await c3ExperimentApi.authorize(
          datasetId,
          researcher.trim(),
          reason.trim(),
        );
        setNotice(
          "Synthetic experiment authorized. No training job has been started.",
        );
      } else {
        await c3ExperimentApi.revoke(datasetId);
        setNotice("Experiment authorization revoked.");
      }
      setAdmission(await c3ExperimentApi.admission(datasetId));
      onChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  if (!datasetId) return null;
  return (
    <section
      className="c3-training-card"
      aria-label="Synthetic experiment admission"
      style={{ marginTop: 18, padding: 20 }}>
      <span className="c3-training-eyebrow">
        F10.4.1 · EXPERIMENT ADMISSION
      </span>
      <h4>Synthetic research experiment</h4>
      <p className="c3-training-footnote">
        Separate from field approval. This self-declaration permits local model
        experimentation only; it does not verify sensor provenance, safety, or
        operational suitability.
      </p>
      <p>
        <strong>Temporal readiness:</strong>{" "}
        {admission?.temporal_ready ? "PASSED" : "NOT VERIFIED"} ·{" "}
        <strong>Synthetic authorization:</strong>{" "}
        {admission?.synthetic_experiment_authorized
          ? "AUTHORIZED"
          : "NOT AUTHORIZED"}{" "}
        · <strong>Field approval:</strong> NO
      </p>
      {error && (
        <p role="alert" style={{ color: "#c2410c" }}>
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {!admission?.synthetic_experiment_authorized ? (
        <>
          <label className="c3-training-label" htmlFor="c3-exp-researcher">
            Researcher / operator
          </label>
          <input
            id="c3-exp-researcher"
            value={researcher}
            maxLength={120}
            onChange={(e) => setResearcher(e.target.value)}
            style={{ width: "100%", padding: 10, marginBottom: 12 }}
          />
          <label className="c3-training-label" htmlFor="c3-exp-reason">
            Experiment purpose
          </label>
          <textarea
            id="c3-exp-reason"
            value={reason}
            maxLength={500}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            style={{ width: "100%", padding: 10 }}
          />
          <label style={{ display: "block", marginTop: 12 }}>
            <input
              type="checkbox"
              checked={declared}
              onChange={(e) => setDeclared(e.target.checked)}
            />{" "}
            I declare this dataset is synthetic and have authority to use it for
            testing.
          </label>
          <label style={{ display: "block", marginTop: 10 }}>
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
            />{" "}
            I acknowledge this is NOT approved for field use, safety alerts, or
            real-world reliability claims.
          </label>
          <button
            className="c3-training-primary"
            type="button"
            disabled={
              busy ||
              !admission?.temporal_ready ||
              !declared ||
              !acknowledged ||
              researcher.trim().length < 2 ||
              reason.trim().length < 12
            }
            onClick={() => void run("authorize")}
            style={{ marginTop: 14 }}>
            {busy
              ? "Preparing and authorizing…"
              : "Prepare export & authorize synthetic experiment"}
          </button>
        </>
      ) : (
        <button
          className="c3-training-secondary"
          type="button"
          disabled={busy}
          onClick={() => void run("revoke")}>
          Revoke authorization
        </button>
      )}
      <p className="c3-training-footnote">
        After authorization, start a training job separately. A queued job still
        requires the backend worker to execute it.
      </p>
    </section>
  );
}
