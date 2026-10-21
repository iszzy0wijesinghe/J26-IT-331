"""Read-only audit of Golden Database foreign-key dependencies."""

from __future__ import annotations

import json
import sqlite3

from pathlib import Path

from apps.c3_workbench.golden_db import DATABASE_PATH


TRAINING_OWNED_TABLES = {
    "c3_datasets",
    "c3_training_jobs",
    "c3_training_events",
    "c3_model_versions",
    "c3_training_approvals",
    "c3_active_model_assignments",
    "c3_model_activation_history",
}


def inspect_golden_schema() -> dict:
    database_path = Path(DATABASE_PATH).resolve()

    if not database_path.is_file():
        raise FileNotFoundError(
            f"Golden Database not found: {database_path}"
        )

    connection = sqlite3.connect(
        f"{database_path.as_uri()}?mode=ro",
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    try:
        tables = [
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]

        dependencies = []

        for table in tables:
            escaped_table = table.replace('"', '""')

            foreign_keys = connection.execute(
                f'PRAGMA foreign_key_list("{escaped_table}")'
            ).fetchall()

            for foreign_key in foreign_keys:
                referenced_table = foreign_key["table"]

                if referenced_table in TRAINING_OWNED_TABLES:
                    dependencies.append(
                        {
                            "operational_table": table,
                            "referenced_training_table": referenced_table,
                            "from_column": foreign_key["from"],
                            "to_column": foreign_key["to"],
                            "foreign_key_id": foreign_key["id"],
                        }
                    )

        row_counts = {}

        for table in tables:
            escaped_table = table.replace('"', '""')

            row_counts[table] = connection.execute(
                f'SELECT COUNT(*) FROM "{escaped_table}"'
            ).fetchone()[0]

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        return {
            "database": str(database_path),
            "integrity": integrity,
            "foreign_key_errors": len(foreign_key_errors),
            "table_counts": row_counts,
            "training_table_dependencies": dependencies,
            "migration_required": bool(dependencies),
            "database_modified": False,
        }

    finally:
        connection.close()


def main() -> None:
    report = inspect_golden_schema()

    print(json.dumps(report, indent=2))

    if report["integrity"] != "ok":
        raise SystemExit(
            "FAILED: Golden Database integrity check"
        )

    if report["foreign_key_errors"]:
        raise SystemExit(
            "FAILED: Existing foreign-key violations detected"
        )

    print("\nGolden schema inspection: PASSED")
    print("No database modifications performed.")


if __name__ == "__main__":
    main()