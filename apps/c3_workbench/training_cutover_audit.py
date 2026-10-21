"""
GeoNex C3 — Training Database Cutover Audit.

Phase 1.4.12

Read-only verification of the separation between:

    Golden Database:
        Operational sensor observations.

    Training Database:
        Dataset metadata.
        Training approvals.
        Training jobs.
        Training events.
        Model versions.
        Active research model assignments.
        Model activation history.

IMPORTANT:
    This audit never:
        - Creates databases.
        - Modifies records.
        - Starts training.
        - Activates models.
        - Removes rollback tables.
        - Approves runtime cutover.

Historical Golden training tables are treated as
rollback snapshots, not the authoritative live store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_GOLDEN_DB = (
    PROJECT_ROOT
    / "data/workbench/c3/golden/c3_golden.sqlite3"
)

DEFAULT_TRAINING_DB = (
    PROJECT_ROOT
    / "data/training/c3_training.sqlite3"
)


TRAINING_TABLES = (
    "c3_datasets",
    "c3_training_jobs",
    "c3_training_events",
    "c3_model_versions",
    "c3_training_approvals",
    "c3_active_model_assignments",
    "c3_model_activation_history",
)


OPERATIONAL_TABLES = (
    "c3_golden_observations",
    "c3_forecast_runs",
    "c3_forecast_values",
    "c3_alert_events",
)


def open_readonly(
    path: Path,
) -> sqlite3.Connection:
    """
    Open an existing SQLite database without
    creating or modifying it.
    """

    resolved = path.resolve()

    if not resolved.is_file():
        raise FileNotFoundError(
            f"Database does not exist: {resolved}"
        )

    connection = sqlite3.connect(
        resolved.as_uri() + "?mode=ro",
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    return connection


def get_tables(
    connection: sqlite3.Connection,
) -> set[str]:
    """
    Retrieve database table names.
    """

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    return {
        row["name"]
        for row in rows
    }


def fingerprint_table(
    connection: sqlite3.Connection,
    table: str,
) -> dict:
    """
    Calculate a deterministic fingerprint
    using column names and row values.

    Row ordering does not affect the result.
    """

    columns = [
        row["name"]
        for row in connection.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    ]

    if not columns:
        return {
            "exists": False,
            "rows": None,
            "sha256": None,
        }

    rows = connection.execute(
        f'SELECT * FROM "{table}"'
    ).fetchall()

    encoded_rows = [
        json.dumps(
            list(row),
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        for row in rows
    ]

    encoded_rows.sort()

    digest = hashlib.sha256()

    digest.update(
        json.dumps(
            columns,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    for encoded in encoded_rows:

        digest.update(b"\n")

        digest.update(
            encoded.encode("utf-8")
        )

    return {
        "exists": True,
        "rows": len(rows),
        "sha256": digest.hexdigest(),
    }


def database_health(
    connection: sqlite3.Connection,
) -> dict:
    """
    Verify SQLite structural integrity and
    foreign-key consistency.
    """

    integrity = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    return {
        "integrity": integrity,
        "foreign_key_errors": len(
            foreign_key_errors
        ),
        "healthy": (
            integrity == "ok"
            and not foreign_key_errors
        ),
    }


def audit(
    source: Path = DEFAULT_GOLDEN_DB,
    target: Path = DEFAULT_TRAINING_DB,
) -> dict:
    """
    Audit Golden and Training Database separation.

    Returns a structured, read-only report.
    """

    source = source.resolve()
    target = target.resolve()

    if source == target:
        raise ValueError(
            "Golden and Training Databases "
            "must use different paths."
        )

    with open_readonly(source) as golden_connection:

        with open_readonly(target) as training_connection:

            golden_tables = get_tables(
                golden_connection
            )

            training_tables = get_tables(
                training_connection
            )

            # -----------------------------------------
            # 1. Training table inventory
            # -----------------------------------------

            golden_snapshots = {
                table: fingerprint_table(
                    golden_connection,
                    table,
                )
                for table in TRAINING_TABLES
            }

            training_records = {
                table: fingerprint_table(
                    training_connection,
                    table,
                )
                for table in TRAINING_TABLES
            }

            missing_training_tables = sorted(
                set(TRAINING_TABLES)
                - training_tables
            )

            # -----------------------------------------
            # 2. Historical snapshot comparison
            # -----------------------------------------

            drifted_tables = [
                table
                for table in TRAINING_TABLES
                if (
                    golden_snapshots[table]
                    != training_records[table]
                )
            ]

            # Differences after migration may be
            # legitimate training lifecycle updates.
            # Report them without silently failing.

            # -----------------------------------------
            # 3. Operational table separation
            # -----------------------------------------

            unexpected_operational_tables = sorted(
                training_tables.intersection(
                    OPERATIONAL_TABLES
                )
            )

            golden_observation_table_exists = (
                "c3_golden_observations"
                in golden_tables
            )

            golden_observation_count = None

            if golden_observation_table_exists:

                golden_observation_count = (
                    golden_connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM c3_golden_observations
                        """
                    ).fetchone()[0]
                )

            # -----------------------------------------
            # 4. Database integrity
            # -----------------------------------------

            golden_health = database_health(
                golden_connection
            )

            training_health = database_health(
                training_connection
            )

            # -----------------------------------------
            # 5. Read-only structural assessment
            # -----------------------------------------

            structural_checks_passed = all(
                (
                    not missing_training_tables,
                    not unexpected_operational_tables,
                    golden_observation_table_exists,
                    golden_health["healthy"],
                    training_health["healthy"],
                )
            )

            # Snapshot equality is reported
            # separately from structural readiness.

            snapshot_matches = (
                not drifted_tables
            )

            return {
                "golden_database": str(source),
                "training_database": str(target),

                "training_tables": (
                    training_records
                ),

                "golden_rollback_snapshots": (
                    golden_snapshots
                ),

                "missing_training_tables": (
                    missing_training_tables
                ),

                "drifted_tables": (
                    drifted_tables
                ),

                "snapshot_matches": (
                    snapshot_matches
                ),

                "unexpected_operational_tables": (
                    unexpected_operational_tables
                ),

                "golden_observation_table_exists": (
                    golden_observation_table_exists
                ),

                "golden_observation_count": (
                    golden_observation_count
                ),

                "golden_database_health": (
                    golden_health
                ),

                "training_database_health": (
                    training_health
                ),

                "structural_checks_passed": (
                    structural_checks_passed
                ),

                "runtime_cutover_approved": False,

                "reason": (
                    "Structural verification alone "
                    "does not establish complete "
                    "runtime database isolation. "
                    "Application dependency auditing "
                    "and integration testing remain."
                ),
            }


def main() -> None:

    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_GOLDEN_DB,
    )

    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TRAINING_DB,
    )

    args = parser.parse_args()

    result = audit(
        source=args.source,
        target=args.target,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    raise SystemExit(
        0
        if result["structural_checks_passed"]
        else 2
    )


if __name__ == "__main__":
    main()