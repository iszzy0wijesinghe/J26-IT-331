import sqlite3
from pathlib import Path

import importlib.util
MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "c3_workbench" / "training_cutover_audit.py"
spec = importlib.util.spec_from_file_location("training_cutover_audit", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
audit = module.audit

TABLES = ('c3_datasets', 'c3_training_jobs', 'c3_training_events', 'c3_model_versions')

def setup_db(path: Path):
    with sqlite3.connect(path) as conn:
        for table in TABLES:
            conn.execute(f'CREATE TABLE {table} (id TEXT PRIMARY KEY, value TEXT)')
            conn.execute(f'INSERT INTO {table} VALUES (?, ?)', ('one', 'value'))

def test_matching_snapshot(tmp_path):
    src, dst = tmp_path/'golden.sqlite3', tmp_path/'training.sqlite3'
    setup_db(src)
    setup_db(dst)
    result = audit(src, dst)
    assert result['snapshot_matches'] is True
    assert result['runtime_cutover_approved'] is False

def test_drift_is_detected(tmp_path):
    src, dst = tmp_path/'golden.sqlite3', tmp_path/'training.sqlite3'
    setup_db(src)
    setup_db(dst)
    with sqlite3.connect(src) as conn:
        conn.execute("UPDATE c3_training_jobs SET value='changed'")
    result = audit(src, dst)
    assert 'c3_training_jobs' in result['drifted_tables']
    assert result['snapshot_matches'] is False

def test_operational_tables_not_allowed(tmp_path):
    src, dst = tmp_path/'golden.sqlite3', tmp_path/'training.sqlite3'
    setup_db(src)
    setup_db(dst)
    with sqlite3.connect(dst) as conn:
        conn.execute('CREATE TABLE c3_golden_observations (id TEXT)')
    result = audit(src, dst)
    assert result['unexpected_operational_tables'] == ['c3_golden_observations']
    assert result['snapshot_matches'] is False
