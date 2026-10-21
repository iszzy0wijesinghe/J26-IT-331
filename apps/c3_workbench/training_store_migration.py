"""
GeoNex C3 - Training Store Migration

Safely copies existing training and model-management tables
from the Golden Database to the dedicated Training Database.

This script does not modify the Golden Database.

Usage:
    python -m apps.c3_workbench.training_store_migration
"""

from __future__ import annotations

import hashlib
import sqlite3

from pathlib import Path

from apps.c3_workbench.training_database import (
    get_training_db_path,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

GOLDEN_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "workbench"
    / "c3"
    / "golden"
    / "c3_golden.sqlite3"
)


TABLES_TO_MIGRATE = (
    # Dataset metadata required by training foreign keys
    "c3_datasets",

    # Training execution
    "c3_training_jobs",
    "c3_training_events",

    # Model registry
    "c3_model_versions",

    # Training governance
    "c3_training_approvals",

    # Model activation
    "c3_active_model_assignments",
    "c3_model_activation_history",
)


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
    schema: str = "main",
) -> bool:

    row = connection.execute(
        f"""
        SELECT name
        FROM {quote_identifier(schema)}.sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
    schema: str = "main",
) -> list[str]:

    rows = connection.execute(
        f"""
        PRAGMA {quote_identifier(schema)}.table_info(
            {quote_identifier(table_name)}
        )
        """
    ).fetchall()

    return [row[1] for row in rows]


def count_rows(
    connection: sqlite3.Connection,
    table_name: str,
    schema: str = "main",
) -> int:

    result = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {quote_identifier(schema)}.{quote_identifier(table_name)}
        """
    ).fetchone()

    return int(result[0])


def calculate_table_digest(
    connection: sqlite3.Connection,
    table_name: str,
    schema: str = "main",
) -> str:
    """
    Calculate a deterministic content digest.

    SQLite storage order is not guaranteed, so rows are
    serialized and sorted before hashing.
    """

    columns = get_table_columns(
        connection,
        table_name,
        schema,
    )

    if not columns:
        raise RuntimeError(
            f"No columns found for {schema}.{table_name}"
        )

    column_sql = ", ".join(
        quote_identifier(column)
        for column in columns
    )

    cursor = connection.execute(
        f"""
        SELECT {column_sql}
        FROM {quote_identifier(schema)}.{quote_identifier(table_name)}
        """
    )

    serialized_rows = []

    for row in cursor.fetchall():

        values = []

        for value in row:

            if value is None:
                values.append("NULL")

            elif isinstance(value, bytes):
                values.append(
                    "BLOB:" + value.hex()
                )

            else:
                values.append(
                    f"{type(value).__name__}:{value!r}"
                )

        serialized_rows.append(
            "\x1f".join(values)
        )

    serialized_rows.sort()

    digest = hashlib.sha256()

    for serialized_row in serialized_rows:
        digest.update(
            serialized_row.encode("utf-8")
        )
        digest.update(b"\n")

    return digest.hexdigest()


def get_source_table_sql(
    connection: sqlite3.Connection,
    table_name: str,
) -> str:

    row = connection.execute(
        """
        SELECT sql
        FROM source_db.sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    if row is None or not row[0]:
        raise RuntimeError(
            f"Source table schema missing: {table_name}"
        )

    return row[0]


def get_source_index_sql(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    rows = connection.execute(
        """
        SELECT sql
        FROM source_db.sqlite_master
        WHERE type = 'index'
          AND tbl_name = ?
          AND sql IS NOT NULL
        ORDER BY name
        """,
        (table_name,),
    ).fetchall()

    return [row[0] for row in rows]


def migrate_training_store() -> dict:

    source_path = GOLDEN_DB_PATH.resolve()
    destination_path = get_training_db_path().resolve()

    if not source_path.exists():
        raise FileNotFoundError(
            f"Golden Database not found: {source_path}"
        )

    if source_path == destination_path:
        raise RuntimeError(
            "Training and Golden Database paths must differ."
        )

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        str(destination_path),
        timeout=30,
        uri=True,
    )
    source_uri = (
        f"file:{source_path.as_posix()}?mode=ro"
    )

    migration_results = {}

    attached = False

    try:
        connection.execute(
            "PRAGMA busy_timeout = 30000"
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            "ATTACH DATABASE ? AS source_db",
            (source_uri,),
        )

        attached = True

        for table_name in TABLES_TO_MIGRATE:

            if not table_exists(
                connection,
                table_name,
                "source_db",
            ):
                raise RuntimeError(
                    f"Missing source table: {table_name}"
                )

            if table_exists(
                connection,
                table_name,
                "main",
            ):
                raise RuntimeError(
                    f"Destination table already exists: {table_name}. "
                    "Migration stopped to prevent overwriting."
                )

        connection.execute("BEGIN IMMEDIATE")

        for table_name in TABLES_TO_MIGRATE:

            create_sql = get_source_table_sql(
                connection,
                table_name,
            )

            connection.execute(create_sql)

            columns = get_table_columns(
                connection,
                table_name,
                "source_db",
            )

            column_sql = ", ".join(
                quote_identifier(column)
                for column in columns
            )

            connection.execute(
                f"""
                INSERT INTO {quote_identifier(table_name)}
                    ({column_sql})
                SELECT {column_sql}
                FROM source_db.{quote_identifier(table_name)}
                """
            )

            for index_sql in get_source_index_sql(
                connection,
                table_name,
            ):
                connection.execute(index_sql)

            source_count = count_rows(
                connection,
                table_name,
                "source_db",
            )

            destination_count = count_rows(
                connection,
                table_name,
                "main",
            )

            if source_count != destination_count:
                raise RuntimeError(
                    f"Count mismatch in {table_name}: "
                    f"{source_count} != {destination_count}"
                )

            source_digest = calculate_table_digest(
                connection,
                table_name,
                "source_db",
            )

            destination_digest = calculate_table_digest(
                connection,
                table_name,
                "main",
            )

            if source_digest != destination_digest:
                raise RuntimeError(
                    f"Data verification failed: {table_name}"
                )

            migration_results[table_name] = {
                "source_rows": source_count,
                "destination_rows": destination_count,
                "sha256": destination_digest,
            }

        connection.commit()

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"Destination integrity check failed: {integrity}"
            )

        return {
            "status": "SUCCESS",
            "source_database": str(source_path),
            "training_database": str(destination_path),
            "tables": migration_results,
        }

    except Exception:

        connection.rollback()
        raise

    finally:

        if attached:
            try:
                connection.execute(
                    "DETACH DATABASE source_db"
                )
            except sqlite3.Error:
                pass

        connection.close()


if __name__ == "__main__":

    import json

    result = migrate_training_store()

    print(
        json.dumps(
            result,
            indent=2,
        )
    )