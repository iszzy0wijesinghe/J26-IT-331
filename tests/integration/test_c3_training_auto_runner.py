"""Integration tests for C3 automatic training orchestration."""

from unittest.mock import patch

import pytest

from apps.c3_workbench.training_auto_runner import run


def test_automatic_training_lifecycle_success():
    """A queued job must train, register candidates, and complete."""

    job_id = "c3train_test001"
    dataset_id = "dataset_test001"

    queued_job = {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "status": "QUEUED",
    }

    registration_result = {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "registered_candidates": 18,
    }

    completion_result = {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "status": "COMPLETED",
    }

    with (
        patch(
            "apps.c3_workbench.training_auto_runner.get_training_job",
            return_value=queued_job,
        ) as mock_get_job,
        patch(
            "apps.c3_workbench.training_auto_runner.execute_training_job",
        ) as mock_train,
        patch(
            "apps.c3_workbench.training_auto_runner.register_model_candidates",
            return_value=registration_result,
        ) as mock_register,
        patch(
            "apps.c3_workbench.training_auto_runner.complete_training_job",
            return_value=completion_result,
        ) as mock_complete,
    ):
        result = run(job_id)

    mock_get_job.assert_called_once_with(job_id)

    mock_train.assert_called_once_with(
        job_id,
        max_epochs=30,
        patience=6,
        device="auto",
    )

    mock_register.assert_called_once_with(
        job_id,
        dataset_id,
    )

    mock_complete.assert_called_once_with(
        job_id,
        dataset_id,
    )

    assert result["registration"] == registration_result
    assert result["completion"] == completion_result


def test_automatic_training_rejects_nonqueued_job():
    """Training must not start for a job that is already running."""

    job_id = "c3train_test002"

    with (
        patch(
            "apps.c3_workbench.training_auto_runner.get_training_job",
            return_value={
                "job_id": job_id,
                "dataset_id": "dataset_test002",
                "status": "TRAINING",
            },
        ),
        patch(
            "apps.c3_workbench.training_auto_runner.execute_training_job",
        ) as mock_train,
    ):
        with pytest.raises(ValueError, match="Expected QUEUED"):
            run(job_id)

    mock_train.assert_not_called()


def test_automatic_training_rejects_unknown_job():
    """Unknown training jobs must not start."""

    job_id = "c3train_unknown"

    with patch(
        "apps.c3_workbench.training_auto_runner.get_training_job",
        return_value=None,
    ):
        with pytest.raises(ValueError, match="Unknown job"):
            run(job_id)


def test_automatic_training_registration_failure():
    """Registration failures must prevent training completion."""

    job_id = "c3train_test003"
    dataset_id = "dataset_test003"

    queued_job = {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "status": "QUEUED",
    }

    evaluating_job = {
        **queued_job,
        "status": "EVALUATING",
    }

    with (
        patch(
            "apps.c3_workbench.training_auto_runner.get_training_job",
            side_effect=[queued_job, evaluating_job],
        ),
        patch(
            "apps.c3_workbench.training_auto_runner.execute_training_job",
        ),
        patch(
            "apps.c3_workbench.training_auto_runner.register_model_candidates",
            side_effect=ValueError("Invalid model artifacts"),
        ),
        patch(
            "apps.c3_workbench.training_auto_runner.complete_training_job",
        ) as mock_complete,
        patch(
            "apps.c3_workbench.training_auto_runner.update_training_job",
        ) as mock_update,
    ):
        with pytest.raises(ValueError, match="Invalid model artifacts"):
            run(job_id)

    mock_complete.assert_not_called()

    mock_update.assert_called_once()

    assert mock_update.call_args.kwargs["status"] == "FAILED"
    assert mock_update.call_args.kwargs["stage"] == "AUTOMATION_FAILED"