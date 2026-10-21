
from __future__ import annotations

import asyncio
import json
import uuid
from io import BytesIO
from threading import Lock
from typing import Any
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apps.c4_frontend.ml_explorer import (
    C4ModelExplorer,
    MODEL_CATALOG,
    available_catalog_entries,
    catalog_by_key,
)
from apps.c4_frontend.c4_backend import C4DemoBackend, SUPPORTED_SCENARIOS

from apps.c4_frontend.upload_training import (
    FEATURES,
    LABELS,
    predict_uploaded_dataset,
    prepare_uploaded_dataset,
    save_candidate_model,
    train_uploaded_random_forest,
    verify_candidate_runtime_compatibility,
)

from apps.ingestion.persistence import persist_telemetry_packet
from database.session import create_database_engine
from shared.config.settings import get_settings
from shared.contracts.telemetry import TelemetryPacket

# Get the repository root (3 levels up from apps/api/)
REPO_ROOT = Path(__file__).resolve().parents[2]
QUARANTINE_DIR = REPO_ROOT / "quarantine" / "c4"

app = FastAPI(
    title="GeoNex C4 Model Explorer API",
    version="1.3.0",
)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_TRAINING_SESSIONS: dict[str, dict[str, Any]] = {}
_TRAINING_JOBS: dict[str, dict[str, Any]] = {}
_TRAINING_LOCK = Lock()


class ScenarioRequest(BaseModel):
    scenario: str


class PersistTrustedRequest(BaseModel):
    predictions: list[dict[str, Any]]
    filename: str


class ManualPredictionRequest(BaseModel):
    tx_interval_s: float
    rssi_dbm: float
    snr_db: float
    retry_count: int
    battery_pct: float
    battery_voltage_v: float
    current_ma: float
    reboot_count_24h: int
    sensor_fault_flag: bool
    freshness_status: str


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())

    if isinstance(value, np.generic):
        return json_safe(value.item())

    if isinstance(value, float) and not np.isfinite(value):
        return None

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if hasattr(value, "tolist") and callable(value.tolist):
        return json_safe(value.tolist())

    if hasattr(value, "item") and callable(value.item):
        return json_safe(value.item())

    return str(value)


def get_model_entry(model_key: str) -> Any:
    entry = catalog_by_key().get(model_key)

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown C4 model: {model_key}",
        )

    return entry


def get_model_schema(model_key: str) -> tuple[Any, list[str]]:
    try:
        explorer = C4ModelExplorer.from_catalog(model_key)
        schema = explorer.schema_table()

        if "feature" not in schema.columns:
            raise ValueError(
                "The model schema does not contain a feature column."
            )

        required_columns = (
            schema["feature"]
            .dropna()
            .astype(str)
            .tolist()
        )

        if not required_columns:
            raise ValueError(
                "The selected model has no feature columns in its schema."
            )

        return explorer, required_columns

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Model artifact not found: {exc}",
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read model feature schema: {exc}",
        ) from exc


@app.get("/api/c4/models")
def list_models() -> dict[str, Any]:
    available = available_catalog_entries()

    return {
        "default_model": next(
            (
                entry.key
                for entry in MODEL_CATALOG
                if entry.runtime_default
            ),
            None,
        ),
        "models": [
            {
                "key": entry.key,
                "label": entry.label,
                "artifact": entry.filename,
                "runtime_default": entry.runtime_default,
                "notes": entry.notes,
            }
            for entry in available
        ],
    }


@app.get("/api/c4/models/{model_key}")
def get_model_profile(model_key: str) -> dict[str, Any]:
    get_model_entry(model_key)

    try:
        explorer = C4ModelExplorer.from_catalog(model_key)
        profile = explorer.profile()
        schema = explorer.schema_table()

        return {
            "key": model_key,
            "profile": json_safe(profile),
            "features": json_safe(
                schema.to_dict(orient="records")
            ),
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Model artifact not found: {exc}",
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to inspect model artifact: {exc}",
        ) from exc


@app.post("/api/c4/models/{model_key}/validate-csv")
async def validate_csv(
    model_key: str,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    entry = get_model_entry(model_key)
    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Please upload a file with a .csv extension.",
        )

    try:
        content = await file.read(MAX_UPLOAD_SIZE + 1)

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV file is empty.",
            )

        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="CSV file exceeds the 10 MB upload limit.",
            )

        try:
            df = pd.read_csv(BytesIO(content))
        except (
            ValueError,
            UnicodeDecodeError,
            pd.errors.ParserError,
        ) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to read CSV: {exc}",
            ) from exc

    finally:
        await file.close()

    if len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail="The CSV does not contain any columns.",
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="The CSV does not contain any data rows.",
        )

    _, required_columns = get_model_schema(model_key)
    preprocessing_errors: list[str] = []

    if (
        "freshness_status_encoded" in required_columns
        and "freshness_status_encoded" not in df.columns
        and "freshness_status" in df.columns
    ):
        freshness_mapping = {
            "fresh": 0,
            "delayed": 1,
            "stale": 2,
        }

        raw_status = (
            df["freshness_status"]
            .astype("string")
            .str.strip()
            .str.lower()
        )

        encoded_status = raw_status.map(freshness_mapping)
        unknown_mask = raw_status.notna() & encoded_status.isna()

        if unknown_mask.any():
            unknown_values = (
                raw_status[unknown_mask]
                .drop_duplicates()
                .tolist()
            )

            preprocessing_errors.append(
                "Unknown freshness_status value(s): "
                + ", ".join(str(value) for value in unknown_values)
            )

        df["freshness_status_encoded"] = encoded_status

    uploaded_columns = [str(column) for column in df.columns]

    duplicate_column_names = (
        df.columns[df.columns.duplicated()]
        .astype(str)
        .tolist()
    )

    missing_columns = [
        column
        for column in required_columns
        if column not in uploaded_columns
    ]

    extra_columns = [
        column
        for column in uploaded_columns
        if column not in required_columns
    ]

    missing_values: dict[str, int] = {}
    non_numeric_values: dict[str, int] = {}
    non_finite_values: dict[str, int] = {}

    for column in required_columns:
        if column not in df.columns:
            continue

        series = df[column]
        missing_count = int(series.isna().sum())

        if missing_count:
            missing_values[column] = missing_count

        numeric = pd.to_numeric(series, errors="coerce")
        invalid_mask = series.notna() & numeric.isna()
        invalid_count = int(invalid_mask.sum())

        if invalid_count:
            non_numeric_values[column] = invalid_count

        numeric_values = numeric.dropna()

        if not numeric_values.empty:
            finite_mask = pd.Series(
                np.isfinite(numeric_values.to_numpy(dtype=float)),
                index=numeric_values.index,
            )

            non_finite_count = int((~finite_mask).sum())

            if non_finite_count:
                non_finite_values[column] = non_finite_count

    duplicate_rows = int(df.duplicated().sum())
    errors = list(preprocessing_errors)
    warnings: list[str] = []

    if duplicate_column_names:
        errors.append(
            "Duplicate column names were found in the CSV."
        )

    if missing_columns:
        errors.append(
            f"{len(missing_columns)} required feature column(s) are missing."
        )

    if missing_values:
        errors.append(
            "Missing values were found in required feature columns."
        )

    if non_numeric_values:
        errors.append(
            "Non-numeric values were found in required feature columns."
        )

    if non_finite_values:
        errors.append(
            "Infinite or non-finite numeric values were found."
        )

    if extra_columns:
        warnings.append(
            f"{len(extra_columns)} extra column(s) are not required by this model."
        )

    if duplicate_rows:
        warnings.append(
            f"{duplicate_rows} duplicate row(s) were detected."
        )

    present_feature_count = sum(
        column in uploaded_columns
        for column in required_columns
    )

    is_valid = not errors

    if is_valid and warnings:
        status = "valid_with_warnings"
    elif is_valid:
        status = "valid"
    else:
        status = "invalid"

    return {
        "filename": filename,
        "model_key": model_key,
        "model_label": entry.label,
        "status": status,
        "valid": is_valid,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "required_feature_count": len(required_columns),
        "present_feature_count": present_feature_count,
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "duplicate_column_names": duplicate_column_names,
        "missing_values": missing_values,
        "non_numeric_values": non_numeric_values,
        "non_finite_values": non_finite_values,
        "duplicate_rows": duplicate_rows,
        "errors": errors,
        "warnings": warnings,
        "message": (
            "CSV passed structural and basic data-quality validation."
            if is_valid
            else "CSV validation failed. Fix the reported errors and upload again."
        ),
    }


async def _read_training_csv(file: UploadFile) -> pd.DataFrame:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    try:
        content = await file.read(MAX_UPLOAD_SIZE + 1)

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV is empty.",
            )

        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="The CSV exceeds the 10 MB upload limit.",
            )

        try:
            return pd.read_csv(BytesIO(content))
        except (
            ValueError,
            pd.errors.ParserError,
            UnicodeDecodeError,
        ) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read the CSV: {exc}",
            ) from exc

    finally:
        await file.close()


@app.post("/api/c4/training/preview")
async def preview_training_dataset(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    uploaded_df = await _read_training_csv(file)

    try:
        prepared = prepare_uploaded_dataset(uploaded_df)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    label_counts = {
        str(label): int(count)
        for label, count in prepared["trust_label"].value_counts().items()
    }

    preview_columns = [
        column
        for column in [
            "device_id",
            "device_timestamp",
            "trust_label",
            *FEATURES,
        ]
        if column in prepared.columns
    ]

    preview = prepared[preview_columns].head(8).copy()

    if "device_timestamp" in preview.columns:
        preview["device_timestamp"] = (
            preview["device_timestamp"].astype(str)
        )

    return {
        "filename": file.filename,
        "rows": int(len(prepared)),
        "columns": int(len(uploaded_df.columns)),
        "unique_devices": int(prepared["device_id"].nunique()),
        "class_distribution": label_counts,
        "features": FEATURES,
        "preview": json_safe(
            preview.to_dict(orient="records")
        ),
        "message": (
            "Dataset preparation passed. The dataset is ready for training."
        ),
    }
@app.post("/api/c4/predict")
async def predict_uploaded_csv(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    uploaded_df = await _read_training_csv(file)

    try:
        predictions = predict_uploaded_dataset(uploaded_df)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"The existing C4 model could not be found: {exc}",
        ) from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc}",
        ) from exc

    return {
        "filename": file.filename,
        "rows": int(len(predictions)),
        "predictions": json_safe(
            predictions.to_dict(orient="records")
        ),
        "message": (
            "Predictions generated using the existing C4 model. "
            "No model training was performed."
        ),
    }


@app.post("/api/c4/predict-manual")
async def predict_manual_features(request: ManualPredictionRequest) -> dict[str, Any]:
    """Predict trust label from manually entered feature values.

    This endpoint is designed for viva demonstrations where you want to
    show the ML model running with custom input values.

    Args:
        request: Feature values for a single telemetry packet

    Returns:
        Predicted trust label and behavioral score
    """
    try:
        from apps.c4_frontend.ml_explorer import C4ModelExplorer, MODEL_CATALOG
        from pathlib import Path

        # Basic type and sanity checks to prevent crashes (not domain validation)
        # These checks ensure the model can run without crashing
        if not isinstance(request.tx_interval_s, (int, float)) or not np.isfinite(request.tx_interval_s):
            raise HTTPException(
                status_code=400,
                detail="TX Interval must be a finite number"
            )
        if not isinstance(request.rssi_dbm, (int, float)) or not np.isfinite(request.rssi_dbm):
            raise HTTPException(
                status_code=400,
                detail="RSSI must be a finite number"
            )
        if not isinstance(request.snr_db, (int, float)) or not np.isfinite(request.snr_db):
            raise HTTPException(
                status_code=400,
                detail="SNR must be a finite number"
            )
        if not isinstance(request.battery_pct, (int, float)) or not np.isfinite(request.battery_pct):
            raise HTTPException(
                status_code=400,
                detail="Battery % must be a finite number"
            )
        if not isinstance(request.battery_voltage_v, (int, float)) or not np.isfinite(request.battery_voltage_v):
            raise HTTPException(
                status_code=400,
                detail="Battery voltage must be a finite number"
            )
        if not isinstance(request.current_ma, (int, float)) or not np.isfinite(request.current_ma):
            raise HTTPException(
                status_code=400,
                detail="Current must be a finite number"
            )
        if not isinstance(request.retry_count, int) or request.retry_count < 0:
            raise HTTPException(
                status_code=400,
                detail="Retry count must be a non-negative integer"
            )
        if not isinstance(request.reboot_count_24h, int) or request.reboot_count_24h < 0:
            raise HTTPException(
                status_code=400,
                detail="Reboot count must be a non-negative integer"
            )
        if request.freshness_status not in ["fresh", "delayed", "stale"]:
            raise HTTPException(
                status_code=400,
                detail="Freshness status must be 'fresh', 'delayed', or 'stale'"
            )

        # Flag if inputs appear unrealistic (for experimental labeling only)
        # This does not reject the input, only adds a warning label
        is_unrealistic = (
            request.tx_interval_s <= 0 or
            request.battery_voltage_v <= 0 or
            request.current_ma < 0 or
            request.rssi_dbm > 0 or  # Positive RSSI is unusual for LoRa
            request.battery_pct < 0 or request.battery_pct > 100
        )

        # Get the default runtime model
        default_entry = next(
            (entry for entry in MODEL_CATALOG if entry.runtime_default),
            None
        )

        if default_entry is None:
            raise HTTPException(
                status_code=503,
                detail="No default runtime model is configured"
            )

        # Load the model
        repo_root = Path(__file__).resolve().parents[2]
        model_path = repo_root / "experiments" / "c4" / "models" / default_entry.filename

        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"Model file not found: {model_path}"
            )

        explorer = C4ModelExplorer.from_catalog(default_entry.key)

        # Prepare the feature row
        # numpy and pandas are already imported at module level

        # Map freshness status to encoded value
        freshness_mapping = {
            "fresh": 0,
            "delayed": 1,
            "stale": 2,
        }
        freshness_encoded = freshness_mapping[request.freshness_status]

        # Calculate derived features
        # Note: For manual demo without device history, we use reasonable defaults
        # In production runtime, these would be calculated from actual device history
        rx_delay_s = 5.0  # Simulated typical delay between observation and reception
        rssi_deviation_db = 0.0  # No history available, assume no deviation
        packet_size_bytes = 256  # Estimated typical telemetry packet size

        # Corrected training fills absent prior history with zero.
        # Do not invent history or variability from the current observation.
        rolling_interval_mean = 0.0
        rolling_interval_std = 0.0
        rolling_rssi_mean = 0.0
        rolling_rssi_std = 0.0
        rolling_retry_mean = 0.0

        # Build feature row matching the expected schema
        feature_row = {
            "tx_interval_s": request.tx_interval_s,
            "rx_delay_s": rx_delay_s,
            "freshness_status_encoded": freshness_encoded,
            "rssi_dbm": request.rssi_dbm,
            "rssi_deviation_db": rssi_deviation_db,
            "snr_db": request.snr_db,
            "retry_count": request.retry_count,
            "packet_size_bytes": packet_size_bytes,
            "battery_pct": request.battery_pct,
            "battery_voltage_v": request.battery_voltage_v,
            "current_ma": request.current_ma,
            "reboot_count_24h": request.reboot_count_24h,
            "sensor_fault_flag": 1 if request.sensor_fault_flag else 0,
            "rolling_interval_mean": rolling_interval_mean,
            "rolling_interval_std": rolling_interval_std,
            "rolling_rssi_mean": rolling_rssi_mean,
            "rolling_rssi_std": rolling_rssi_std,
            "rolling_retry_mean": rolling_retry_mean,
        }

        # Create DataFrame with correct column order
        from components.c4_trust.runtime_features import C4_MODEL_FEATURE_SCHEMA
        df = pd.DataFrame([feature_row], columns=C4_MODEL_FEATURE_SCHEMA)

        # Get prediction using the correct method
        scored = explorer.score_features(df)

        if scored is None or len(scored) == 0:
            raise HTTPException(
                status_code=500,
                detail="Model returned no prediction"
            )

        predicted_label = str(scored.iloc[0]["predicted_label"])

        # Ensure consistent capitalization for frontend comparison
        # The model returns label as encoded (e.g., "Trusted"), we keep it as-is
        # Frontend handles case-insensitive comparison

        # Get behavioral score from the model
        behavioral_score = float(scored.iloc[0]["anomaly_score"])
        input_health_warnings = []
        for condition, warning in (
            (request.tx_interval_s <= 0, "TX interval is zero or negative."),
            (request.battery_pct <= 0, "Battery percentage is zero or negative."),
            (request.battery_voltage_v <= 0, "Battery voltage is zero or negative."),
            (request.sensor_fault_flag, "Device reports a sensor fault."),
            (request.freshness_status == "stale", "Telemetry is stale."),
        ):
            if condition:
                input_health_warnings.append(warning)

        # Use the actual model prediction without override
        trust_label = predicted_label
        logger_message = f"ML model prediction: {trust_label} (anomaly score: {behavioral_score:.4f})"

        return {
            "predicted_label": trust_label,
            "behavioural_score": behavioral_score,
            "raw_prediction": predicted_label,
            "input_health_warnings": input_health_warnings,
            "feature_assumptions": {
                "rx_delay_s": "Assumed 5 seconds; timestamps are not supplied.",
                "packet_size_bytes": "Assumed 256 bytes; no serialized packet is supplied.",
                "rssi_deviation_db": "Assumed zero; device mean RSSI is unavailable.",
                "rolling_features": "No prior history: all five rolling features are zero, matching corrected training cold-start fill.",
            },
            "features": json_safe(feature_row),
            "scored_results": json_safe(scored.iloc[0].to_dict()),
            "debug_info": {
                "model_prediction": str(predicted_label),
                "anomaly_score": float(scored.iloc[0].get("anomaly_score", "N/A")),
                "ml_decision": str(scored.iloc[0].get("ml_decision", "N/A")),
                "p_trusted": float(scored.iloc[0].get("p_trusted", "N/A")) if "p_trusted" in scored.columns else "N/A",
                "demo_override": False,
                "is_experimental": is_unrealistic,
            },
            "message": logger_message
        }

    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        error_detail = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=f"Manual prediction failed: {error_detail}"
        ) from exc

def _training_progress(
    training_id: str,
    stage: str,
    message: str,
) -> None:
    with _TRAINING_LOCK:
        job = _TRAINING_JOBS.get(training_id)

        if job is not None:
            job["stage"] = stage
            job["message"] = message


def _training_response(
    training_id: str,
    filename: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    predictions = result["predictions"].head(20).copy()

    if "device_timestamp" in predictions.columns:
        predictions["device_timestamp"] = (
            predictions["device_timestamp"].astype(str)
        )

    return json_safe({
        "training_id": training_id,
        "filename": filename,
        "accuracy": result["accuracy"],
        "classes": result["classes"],
        "classification_report": result["report"],
        "confusion_matrix": result["confusion_matrix"],
        "train_rows": len(result["splits"]["train"]),
        "validation_rows": len(result["splits"]["validation"]),
        "test_rows": len(result["splits"]["test"]),
        "unique_devices": int(
            result["prepared"]["device_id"].nunique()
        ),
        "feature_importance": result[
            "feature_importance"
        ].to_dict(orient="records"),
        "sample_predictions": predictions.to_dict(orient="records"),
        "runtime_compatibility_verified": False,
        "message": (
            "Training completed. Review the test metrics before saving "
            "the candidate model."
        ),
    })


def _run_training_job(
    training_id: str,
    filename: str,
    uploaded_df: pd.DataFrame,
) -> None:
    try:
        result = train_uploaded_random_forest(
            uploaded_df,
            progress_callback=lambda stage, message: _training_progress(
                training_id,
                stage,
                message,
            ),
        )

        response = _training_response(
            training_id,
            filename,
            result,
        )

        with _TRAINING_LOCK:
            _TRAINING_SESSIONS[training_id] = result

            while len(_TRAINING_SESSIONS) > 5:
                oldest_id = next(iter(_TRAINING_SESSIONS))
                del _TRAINING_SESSIONS[oldest_id]

            job = _TRAINING_JOBS.get(training_id)

            if job is not None:
                job["result"] = response
                job["status"] = "completed"
                job["stage"] = "completed"
                job["message"] = "Training and evaluation completed."

    except Exception as exc:
        with _TRAINING_LOCK:
            job = _TRAINING_JOBS.get(training_id)

            if job is not None:
                job["status"] = "failed"
                job["stage"] = "failed"
                job["message"] = str(exc)


@app.post("/api/c4/training/train")
async def train_candidate_dataset(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    uploaded_df = await _read_training_csv(file)
    training_id = str(uuid.uuid4())
    filename = file.filename or "uploaded_dataset.csv"

    with _TRAINING_LOCK:
        _TRAINING_JOBS[training_id] = {
            "status": "running",
            "stage": "queued",
            "message": "Training job queued.",
            "result": None,
        }

    asyncio.create_task(
        asyncio.to_thread(
            _run_training_job,
            training_id,
            filename,
            uploaded_df,
        )
    )

    return {
        "training_id": training_id,
        "status": "running",
        "stage": "queued",
        "message": "Training started. Poll the status endpoint for progress.",
    }

@app.get("/api/c4/training/debug/jobs")
def debug_training_jobs() -> dict[str, Any]:
    with _TRAINING_LOCK:
        return {
            "job_ids": list(_TRAINING_JOBS.keys()),
            "session_ids": list(_TRAINING_SESSIONS.keys()),
        }
    
@app.get("/api/c4/training/{training_id}/status")
def get_training_status(training_id: str) -> dict[str, Any]:
    with _TRAINING_LOCK:
        job = _TRAINING_JOBS.get(training_id)

        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Training job not found. Start training again.",
            )

        response = {
            "training_id": training_id,
            "status": job["status"],
            "stage": job["stage"],
            "message": job["message"],
        }

        if job["status"] == "completed":
            response["result"] = job["result"]

        return json_safe(response)



@app.post("/api/c4/training/{training_id}/save")
def save_trained_candidate(training_id: str) -> dict[str, Any]:
    with _TRAINING_LOCK:
        result = _TRAINING_SESSIONS.get(training_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Training result not found. Train the model again "
                    "before saving."
                ),
            )

        existing_path = result.get("saved_candidate_path")

    repo_root = Path(__file__).resolve().parents[2]

    if existing_path:
        candidate_path = (repo_root / existing_path).resolve()
    else:
        try:
            candidate_path = save_candidate_model(result)
            existing_path = candidate_path.resolve().relative_to(
                repo_root
            ).as_posix()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Could not save the candidate model: {exc}",
            ) from exc

    try:
        verification = verify_candidate_runtime_compatibility(
            candidate_path
        )
    except Exception as exc:
        verification = {
            "runtime_compatibility_verified": False,
            "checks": {
                "candidate_artifact_loads": False,
                "runtime_artifact_loads": False,
                "feature_schema_matches": False,
                "model_type_matches": False,
                "class_labels_match": False,
                "prediction_output_valid": False,
                "probability_output_valid": False,
            },
            "errors": [f"{type(exc).__name__}: {exc}"],
            "message": "Candidate was saved, but verification failed.",
        }

    with _TRAINING_LOCK:
        result["saved_candidate_path"] = existing_path
        result["runtime_compatibility"] = verification

    return {
        "saved": True,
        "candidate_path": existing_path,
        **verification,
    }


@app.post("/api/c4/scenarios/run")
def run_c4_scenario(request: ScenarioRequest) -> dict[str, Any]:
    """Run a C4 security scenario and return assessment results.

    This endpoint enforces the security gate before ML:
    - Security checks run first (authentication, integrity, freshness, replay, certificates)
    - ML inference only runs if mandatory_security_pass = True
    - Failed packets skip ML and record the security failure reason

    Args:
        request: Request body containing scenario name (e.g., "valid_hmac", "tampered_hmac", "valid_ecdsa")

    Returns:
        Assessment results including security status, ML status, and routing outcome
    """
    scenario = request.scenario

    if scenario not in SUPPORTED_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported scenario: {scenario}. "
            f"Supported scenarios: {', '.join(sorted(SUPPORTED_SCENARIOS))}"
        )

    backend = None
    try:
        backend = C4DemoBackend()
        results = backend.run_simulation(scenario)

        if not results:
            raise HTTPException(
                status_code=500,
                detail="Scenario returned no results"
            )

        # Add security status and ML status to each result
        for result in results:
            mandatory_pass = result.get("mandatory_security_pass", False)
            ml_ran = result.get("ml_ran", False)

            # Determine security status
            if mandatory_pass:
                security_status = "PASS"
            else:
                security_status = "FAIL"

            # Determine ML status
            if ml_ran:
                ml_status = "COMPLETED"
            elif not mandatory_pass:
                ml_status = "SKIPPED - SECURITY FAILURE"
            else:
                ml_status = "UNAVAILABLE - MISSING FEATURES"

            # Add status fields
            result["security_status"] = security_status
            result["ml_status"] = ml_status

        return {
            "scenario": scenario,
            "results": json_safe(results),
            "count": len(results),
            "message": f"Scenario '{scenario}' completed successfully. "
            f"{len(results)} assessment(s) generated."
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Scenario execution failed: {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        if backend is not None:
            backend.close()


@app.get("/api/c4/scenarios")
def list_scenarios() -> dict[str, Any]:
    """List all available C4 security scenarios.

    Returns:
        Dictionary with scenario names and descriptions
    """
    scenario_descriptions = {
        "valid_hmac": "Valid telemetry with HMAC-SHA256 signature",
        "tampered_hmac": "Tampered packet with valid HMAC signature (FAIL)",
        "replay_hmac": "Replay attack with duplicate packet (FAIL)",
        "valid_ecdsa": "Valid telemetry with X.509 certificate and ECDSA signature",
        "tampered_ecdsa": "Tampered packet with valid ECDSA signature (FAIL)",
        "expired_x509": "Packet with expired X.509 certificate (FAIL)",
        "untrusted_ca_x509": "Packet signed by untrusted CA (FAIL)",
        "mismatched_identity_x509": "Certificate identity mismatch (FAIL)",
        "revoked_x509": "Packet with revoked certificate (FAIL)",
        "fallback_rejection": "Algorithm fallback rejection (FAIL)",
    }

    return {
        "scenarios": [
            {
                "key": scenario,
                "description": scenario_descriptions.get(scenario, ""),
            }
            for scenario in sorted(SUPPORTED_SCENARIOS)
        ]
    }


@app.get("/api/c4/health")
def health_check() -> dict[str, str]:
    """Health check endpoint to verify API is running."""
    return {"status": "ok", "service": "C4 Model Explorer API"}


@app.post("/api/c4/persist-trusted")
async def persist_trusted_packets(request: PersistTrustedRequest) -> dict[str, Any]:
    """Persist TRUSTED packets from ML prediction to Component 1 database.

    This endpoint receives ML prediction results, filters for TRUSTED packets,
    reconstructs the full telemetry packets, and persists them to the database
    for downstream Component 1 processing.

    Args:
        request: Contains predictions list and original filename

    Returns:
        Summary of persisted packets and any errors
    """
    try:
        import traceback

        settings = get_settings()
        engine = create_database_engine(settings)

        persisted_count = 0
        failed_count = 0
        errors: list[str] = []

        from sqlalchemy.orm import Session

        with Session(engine) as session:
            for idx, prediction in enumerate(request.predictions):
                try:
                    # Extract full packet JSON from prediction
                    full_packet_json = prediction.get("full_packet_json")
                    if not full_packet_json:
                        errors.append(f"Row {idx}: Missing full_packet_json for device {prediction.get('device_id')}")
                        failed_count += 1
                        continue

                    # Reconstruct TelemetryPacket from JSON
                    try:
                        packet_data = json.loads(full_packet_json) if isinstance(full_packet_json, str) else full_packet_json
                        packet = TelemetryPacket.model_validate(packet_data)
                    except Exception as validation_exc:
                        errors.append(f"Row {idx}: Failed to validate packet for device {prediction.get('device_id')}: {validation_exc}")
                        failed_count += 1
                        continue

                    # Persist to database
                    try:
                        result = persist_telemetry_packet(session, packet)
                        persisted_count += 1
                    except Exception as persist_exc:
                        errors.append(f"Row {idx}: Failed to persist packet {packet.packet_id}: {persist_exc}")
                        failed_count += 1
                        continue

                except Exception as exc:
                    errors.append(f"Row {idx}: Unexpected error processing prediction: {exc}\n{traceback.format_exc()}")
                    failed_count += 1

            # Commit all successful persist operations
            session.commit()

        engine.dispose()

        return {
            "status": "completed",
            "persisted_count": persisted_count,
            "failed_count": failed_count,
            "total_predictions": len(request.predictions),
            "errors": errors[:20],  # Limit to first 20 errors
            "message": f"Persisted {persisted_count} TRUSTED packets to database for Component 1 processing."
        }

    except Exception as exc:
        import traceback
        error_detail = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist trusted packets: {error_detail}"
        ) from exc


@app.get("/api/c4/quarantine")
def get_quarantine_files() -> dict[str, Any]:
    """Get all quarantine records from the quarantine/c4/ directory.

    Returns:
        Summary and detailed list of quarantine records
    """
    try:
        print(f"DEBUG: REPO_ROOT = {REPO_ROOT}")
        print(f"DEBUG: QUARANTINE_DIR = {QUARANTINE_DIR}")
        print(f"DEBUG: QUARANTINE_DIR.exists() = {QUARANTINE_DIR.exists()}")

        if not QUARANTINE_DIR.exists():
            return {
                "count": 0,
                "records": [],
                "statistics": {
                    "total": 0,
                    "released": 0,
                    "unreleased": 0,
                    "by_reason": {},
                },
                "message": f"Quarantine directory not found: {QUARANTINE_DIR}"
            }

        quarantine_files = list(QUARANTINE_DIR.glob("*.json"))
        print(f"DEBUG: Found {len(quarantine_files)} quarantine files")

        if not quarantine_files:
            return {
                "count": 0,
                "records": [],
                "statistics": {
                    "total": 0,
                    "released": 0,
                    "unreleased": 0,
                    "by_reason": {},
                },
                "message": "No quarantine files found"
            }

        records = []
        reason_counts: dict[str, int] = {}
        released_count = 0

        for file_path in sorted(quarantine_files):
            try:
                with file_path.open(encoding="utf-8") as f:
                    record = json.load(f)
                    records.append(record)

                    # Count by reason
                    reason = record.get("quarantine_reason", "UNKNOWN")
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1

                    # Count released
                    if record.get("released"):
                        released_count += 1

            except Exception as exc:
                # Skip files that can't be read
                print(f"DEBUG: Error reading {file_path.name}: {exc}")
                continue

        statistics = {
            "total": len(records),
            "released": released_count,
            "unreleased": len(records) - released_count,
            "by_reason": reason_counts,
        }

        print(f"DEBUG: Loaded {len(records)} records successfully")

        return {
            "count": len(records),
            "records": json_safe(records),
            "statistics": statistics,
            "message": f"Found {len(records)} quarantine record(s)"
        }

    except Exception as exc:
        print(f"DEBUG: Exception in get_quarantine_files: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read quarantine files: {exc}"
        ) from exc
