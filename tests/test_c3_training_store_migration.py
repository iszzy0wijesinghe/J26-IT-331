import sqlite3
from pathlib import Path
import pytest
from apps.c3_workbench.training_store_migration import migrate


def test_preview_and_verified_copy(tmp_path: Path):
    src, dst = tmp_path/'golden.sqlite3', tmp_path/'training.sqlite3'
    with sqlite3.connect(src) as db:
        db.executescript('''
        CREATE TABLE c3_datasets(dataset_id TEXT PRIMARY KEY);
        CREATE TABLE c3_training_jobs(job_id TEXT PRIMARY KEY,dataset_id TEXT REFERENCES c3_datasets(dataset_id));
        CREATE TABLE c3_training_events(event_id INTEGER PRIMARY KEY,job_id TEXT REFERENCES c3_training_jobs(job_id));
        CREATE TABLE c3_model_versions(model_version_id TEXT PRIMARY KEY,job_id TEXT REFERENCES c3_training_jobs(job_id));
        INSERT INTO c3_datasets VALUES ('d1');
        INSERT INTO c3_training_jobs VALUES ('j1','d1');
        INSERT INTO c3_training_events VALUES (1,'j1');
        INSERT INTO c3_model_versions VALUES ('m1','j1');
        ''')
    assert migrate(src, dst)['mode'] == 'preview'
    assert not dst.exists()
    assert migrate(src, dst, apply=True)['verified'] is True
    with sqlite3.connect(dst) as db:
        assert db.execute('SELECT COUNT(*) FROM c3_model_versions').fetchone()[0] == 1
    with pytest.raises(FileExistsError):
        migrate(src, dst, apply=True)
