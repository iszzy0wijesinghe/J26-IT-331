/** @format */

import { useCallback, useEffect, useState } from "react";

import {
  c3DatabaseApi,
  c3GoldenApi,
  type C3DatabaseBackup,
} from "../api/c3Api";

import "../styles/c3DatabaseManagement.css";

/* ============================================================
   Helpers
   ============================================================ */

function formatDate(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "An unexpected database operation error occurred.";
}

/* ============================================================
   Types
   ============================================================ */

type DatabaseOverview = {
  datasets: number;
  observations: number;
  devices: number;
  episodes: number;
};

/* ============================================================
   Component
   ============================================================ */

export function C3DatabaseManagement() {
  const [overview, setOverview] = useState<DatabaseOverview | null>(null);

  const [backups, setBackups] = useState<C3DatabaseBackup[]>([]);

  const [loading, setLoading] = useState(true);

  const [creating, setCreating] = useState(false);

  const [verifyingId, setVerifyingId] = useState<string | null>(null);

  const [verifiedIds, setVerifiedIds] = useState<string[]>([]);

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");

  /* ==========================================================
     Load Database Overview
     ========================================================== */

  const loadOverview = useCallback(async (signal?: AbortSignal) => {
    const response = await c3GoldenApi.list(signal);

    if (signal?.aborted) return;

    const datasets = response.datasets;

    const observations = datasets.reduce(
      (sum, dataset) => sum + dataset.total_rows,
      0,
    );

    /*
     * Device and episode counts are sums of per-dataset
     * counts. They are not necessarily globally unique.
     */
    const devices = datasets.reduce(
      (sum, dataset) => sum + dataset.device_count,
      0,
    );

    const episodes = datasets.reduce(
      (sum, dataset) => sum + dataset.episode_count,
      0,
    );

    setOverview({
      datasets: response.total,
      observations,
      devices,
      episodes,
    });
  }, []);

  /* ==========================================================
     Load Backup History
     ========================================================== */

  const loadBackups = useCallback(async (signal?: AbortSignal) => {
    const response = await c3DatabaseApi.listBackups(signal);

    if (signal?.aborted) return;

    setBackups(response.backups);
  }, []);

  /* ==========================================================
     Initial Loading
     ========================================================== */

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);

    Promise.all([
      loadOverview(controller.signal),
      loadBackups(controller.signal),
    ])
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(getErrorMessage(cause));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [loadOverview, loadBackups]);

  /* ==========================================================
     Refresh
     ========================================================== */

  async function handleRefresh() {
    setLoading(true);
    setError("");

    try {
      await Promise.all([loadOverview(), loadBackups()]);
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setLoading(false);
    }
  }

  /* ==========================================================
     Create Backup
     ========================================================== */

  async function handleCreateBackup() {
    if (creating) return;

    setCreating(true);
    setError("");
    setSuccess("");

    try {
      const response = await c3DatabaseApi.createBackup();

      setSuccess(
        `Backup ${response.backup.backup_id} was created and verified successfully.`,
      );

      await loadBackups();
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setCreating(false);
    }
  }

  /* ==========================================================
     Verify Backup
     ========================================================== */

  async function handleVerifyBackup(backupId: string) {
    if (verifyingId) return;

    setVerifyingId(backupId);
    setError("");
    setSuccess("");

    try {
      const backup = await c3DatabaseApi.verifyBackup(backupId);

      setVerifiedIds((current) =>
        current.includes(backupId) ? current : [...current, backupId],
      );

      setSuccess(
        `Backup ${backup.backup_id} passed checksum and SQLite integrity verification.`,
      );
    } catch (cause) {
      setVerifiedIds((current) => current.filter((id) => id !== backupId));

      setError(getErrorMessage(cause));
    } finally {
      setVerifyingId(null);
    }
  }

  /* ==========================================================
     Download Backup
     ========================================================== */

  function handleDownloadBackup(backupId: string) {
    /*
     * The backend verifies the checksum and SQLite integrity
     * before returning the file.
     *
     * The browser handles the actual file download.
     */
    window.location.assign(c3DatabaseApi.downloadBackup(backupId));
  }

  /* ==========================================================
     Render
     ========================================================== */

  return (
    <div className="c3-db-management">
      {/* ======================================================
          Overview
          ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">
              GEONEX C3 · PERSISTENT STORAGE
            </span>

            <h2>Golden Database</h2>
          </div>

          <span className="live-chip">SQLite · Persistent</span>
        </div>

        <p className="panel-subtitle">
          Manage persistent C3 research data, create verified database
          snapshots, and inspect backup history.
        </p>

        <div className="c3-db-overview">
          <div className="c3-db-stat">
            <span>GOLDEN DATASETS</span>

            <strong>{loading ? "…" : (overview?.datasets ?? "—")}</strong>
          </div>

          <div className="c3-db-stat">
            <span>SENSOR OBSERVATIONS</span>

            <strong>
              {loading ? "…" : (overview?.observations.toLocaleString() ?? "—")}
            </strong>
          </div>

          <div className="c3-db-stat">
            <span>DEVICE ENTRIES</span>

            <strong>{loading ? "…" : (overview?.devices ?? "—")}</strong>
          </div>

          <div className="c3-db-stat">
            <span>EPISODE ENTRIES</span>

            <strong>{loading ? "…" : (overview?.episodes ?? "—")}</strong>
          </div>
        </div>

        <p className="c3-db-footnote">
          Device and episode totals are summed across registered datasets; they
          are not globally deduplicated counts.
        </p>

        <div className="c3-db-actions">
          <button
            type="button"
            className="c3-db-button secondary"
            onClick={() => void handleRefresh()}
            disabled={loading || creating}>
            {loading ? "Refreshing…" : "Refresh Database"}
          </button>
        </div>
      </section>

      {/* ======================================================
          Backup Control
          ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">DATA PROTECTION</span>

            <h2>Database Backup</h2>
          </div>

          <span className="c3-db-status-chip">Native SQLite Backup</span>
        </div>

        <p className="panel-subtitle">
          Create a consistent database snapshot using SQLite's backup mechanism.
          Each completed backup is checked for integrity and assigned a SHA-256
          checksum.
        </p>

        <div className="c3-db-backup-control">
          <div className="c3-db-backup-symbol">▣</div>

          <div className="c3-db-backup-description">
            <strong>Create a Verified Snapshot</strong>

            <span>
              Includes Golden datasets, observations, training history, model
              registry, forecasts, and advisory records currently stored in
              SQLite.
            </span>
          </div>

          <button
            type="button"
            className="c3-db-button primary"
            disabled={creating || loading}
            onClick={() => void handleCreateBackup()}>
            {creating ? "Creating Backup…" : "Create Backup"}
          </button>
        </div>

        {creating && (
          <div className="c3-db-progress" role="status">
            <span className="c3-db-spinner" />
            Creating and verifying database snapshot…
          </div>
        )}
      </section>

      {/* ======================================================
          Backup History
          ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">DATABASE SNAPSHOT REGISTRY</span>

            <h2>Backup History</h2>
          </div>

          <span className="live-chip">{backups.length} backups</span>
        </div>

        <p className="panel-subtitle">
          Available database snapshots created through the GeoNex C3 backup
          service.
        </p>

        {loading ? (
          <div className="c3-db-loading">
            <span className="c3-db-spinner" />
            Loading backup history…
          </div>
        ) : backups.length === 0 ? (
          <div className="c3-db-empty">
            <strong>No backups available</strong>

            <p>Create your first verified Golden Database snapshot.</p>
          </div>
        ) : (
          <div className="c3-db-backup-list">
            {backups.map((backup) => {
              const verified = verifiedIds.includes(backup.backup_id);

              return (
                <article key={backup.backup_id} className="c3-db-backup-item">
                  <div className="c3-db-backup-main">
                    <div className="c3-db-backup-item-icon">▤</div>

                    <div className="c3-db-backup-info">
                      <strong>{backup.filename}</strong>

                      <span>{formatDate(backup.created_at)}</span>

                      <code>{backup.backup_id}</code>
                    </div>
                  </div>

                  <div className="c3-db-backup-meta">
                    <span>{formatBytes(backup.size_bytes)}</span>

                    <span
                      className={`c3-db-backup-status ${
                        verified ? "verified" : ""
                      }`}>
                      {verified ? "VERIFIED NOW" : backup.status}
                    </span>
                  </div>

                  <div className="c3-db-backup-buttons">
                    <button
                      type="button"
                      className="c3-db-button secondary"
                      disabled={verifyingId !== null}
                      onClick={() => void handleVerifyBackup(backup.backup_id)}>
                      {verifyingId === backup.backup_id
                        ? "Verifying…"
                        : "Verify"}
                    </button>

                    <button
                      type="button"
                      className="c3-db-button primary"
                      onClick={() => handleDownloadBackup(backup.backup_id)}>
                      Download
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* ======================================================
          Restore Information
          ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">DATABASE RECOVERY</span>

            <h2>Restore Database</h2>
          </div>

          <span className="c3-db-maintenance-chip">OFFLINE ONLY</span>
        </div>

        <p className="panel-subtitle">
          Database restoration is intentionally restricted to offline
          administration. The active API and all SQLite clients must be stopped
          before restoration.
        </p>

        <div className="c3-db-restore-note">
          <strong>Restoration Procedure</strong>

          <ol>
            <li>Select and verify the required database backup.</li>

            <li>Stop the GeoNex C3 backend and close other SQLite clients.</li>

            <li>Execute the offline restoration utility.</li>

            <li>
              Restart the backend and verify the restored dataset history.
            </li>
          </ol>

          <p>
            Restoration replaces the current database snapshot. Records created
            after the selected backup may be lost. A pre-restoration safety
            snapshot is created by the restoration utility.
          </p>
        </div>

        <div className="c3-db-command">
          <span>OFFLINE RESTORE COMMAND</span>

          <code>
            python -m apps.c3_workbench.golden_restore --backup-id BACKUP_ID{" "}
            --confirm "RESTORE GOLDEN DATABASE"
          </code>
        </div>
      </section>

      {/* ======================================================
          Operation Feedback
          ====================================================== */}

      {success && (
        <div className="c3-db-feedback success" role="status">
          {success}
        </div>
      )}

      {error && (
        <div className="c3-db-feedback error" role="alert">
          {error}
        </div>
      )}

      <p className="c3-research-warning">
        Golden Database storage and backup verification protect research
        records, but do not establish the scientific validity of synthetic
        sensor observations or landslide forecasting performance.
      </p>
    </div>
  );
}
