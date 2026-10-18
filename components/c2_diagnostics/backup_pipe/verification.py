"""Deterministic verification of primary and backup sensor telemetry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BackupVerificationResult:
    """Result of checking backup telemetry against primary telemetry."""

    verified: bool
    reason: str
    deviation: float | None = None


def verify_backup_telemetry(
    *,
    backup_reachable: bool,
    primary_values: dict[str, float] | None,
    backup_values: dict[str, float] | None,
    tolerance: float = 0.5,
) -> BackupVerificationResult:
    """Check whether backup telemetry is available and consistent.

    This is a deterministic check, not a machine-learning prediction.
    The tolerance must be selected according to sensor units and calibration.
    """

    if tolerance < 0:
        raise ValueError("tolerance cannot be negative")

    if not backup_reachable:
        return BackupVerificationResult(
            verified=False,
            reason="backup_unreachable",
        )

    if not primary_values or not backup_values:
        return BackupVerificationResult(
            verified=False,
            reason="telemetry_missing",
        )

    if primary_values.keys() != backup_values.keys():
        return BackupVerificationResult(
            verified=False,
            reason="sensor_fields_mismatch",
        )

    deviations = []

    for field in primary_values:
        primary = primary_values[field]
        backup = backup_values[field]

        if not isinstance(primary, (int, float)):
            raise TypeError(f"Primary value for {field} must be numeric")

        if not isinstance(backup, (int, float)):
            raise TypeError(f"Backup value for {field} must be numeric")

        deviations.append(abs(float(primary) - float(backup)))

    maximum_deviation = max(deviations, default=0.0)

    if maximum_deviation > tolerance:
        return BackupVerificationResult(
            verified=False,
            reason="telemetry_deviation_exceeded",
            deviation=maximum_deviation,
        )

    return BackupVerificationResult(
        verified=True,
        reason="telemetry_consistent",
        deviation=maximum_deviation,
    )