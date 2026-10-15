"""SQLAlchemy persistence models for GeoNex telemetry."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class TelemetryPacketRecord(Base):
    """Persisted normalized telemetry packet.

    Original packet fields are preserved without overwriting
    them with downstream assessment results.
    """

    __tablename__ = "telemetry_packets"

    packet_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )

    schema_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    device_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    zone_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    boot_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    sequence_no: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    message_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    measurements: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    device_health: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    transport: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    security: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    source_origin: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    test_run_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    observations: Mapped[list["SensorObservationRecord"]] = relationship(
        back_populates="packet",
    )

    __table_args__ = (
        CheckConstraint(
            "sequence_no IS NULL OR sequence_no >= 0",
            name="sequence_no_nonnegative",
        ),
        Index(
            "ix_telemetry_packets_zone_observed_at",
            "zone_id",
            "observed_at",
        ),
        Index(
            "ix_telemetry_packets_device_received_at",
            "device_id",
            "received_at",
        ),
    )


class SensorObservationRecord(Base):
    """Persisted individual sensor observation."""

    __tablename__ = "sensor_observations"

    observation_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )

    packet_id: Mapped[str] = mapped_column(
        ForeignKey("telemetry_packets.packet_id"),
        nullable=False,
    )

    schema_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    zone_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    device_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    sensor_instance_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    raw_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    unit: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    calibration_version: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    source_origin: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    test_run_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    packet: Mapped["TelemetryPacketRecord"] = relationship(
        back_populates="observations",
    )

    __table_args__ = (
        CheckConstraint(
            "raw_value IS NOT NULL OR value IS NOT NULL",
            name="measurement_value_required",
        ),
        Index(
            "ix_sensor_observations_zone_observed_at",
            "zone_id",
            "observed_at",
        ),
        Index(
            "ix_sensor_observations_sensor_observed_at",
            "sensor_instance_id",
            "observed_at",
        ),
    )
