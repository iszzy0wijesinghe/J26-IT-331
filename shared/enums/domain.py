from enum import StrEnum

# ---------------------------------------------------------------------------
# Frozen shared integration enums
# ---------------------------------------------------------------------------


class OperatingMode(StrEnum):
    """GeoNex operating modes.

    These names are frozen by Integration Contract v1.
    """

    DEEP_SLEEP = "DEEP_SLEEP"
    IDLE = "IDLE"
    RISK = "RISK"
    WARNING = "WARNING"
    EMERGENCY = "EMERGENCY"


class SourceOrigin(StrEnum):
    """Origin of evidence/data, not recovery provenance."""

    PHYSICAL_DEMO = "PHYSICAL_DEMO"
    SYNTHETIC = "SYNTHETIC"
    EXTERNAL = "EXTERNAL"
    SIMULATED = "SIMULATED"


class RecoveryProvenance(StrEnum):
    """How a downstream environmental value became available."""

    DIRECT = "DIRECT"
    LATE_ORIGINAL = "LATE_ORIGINAL"
    BACKUP = "BACKUP"
    FUSED = "FUSED"
    DERIVED = "DERIVED"


class ProcessingStatus(StrEnum):
    """Execution/processing state, separate from scientific output."""

    OK = "OK"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    PROCESSING_ERROR = "PROCESSING_ERROR"


class C1CredibilityLabel(StrEnum):
    """Shared C1 measurement-credibility classes."""

    CLEAN = "CLEAN"
    ANOMALY = "ANOMALY"
    VALID_EVENT = "VALID_EVENT"


class C4TrustLabel(StrEnum):
    """Shared C4 source/transmission trust classes."""

    TRUSTED = "TRUSTED"
    SUSPICIOUS = "SUSPICIOUS"
    UNTRUSTED = "UNTRUSTED"


# ---------------------------------------------------------------------------
# Baseline integration enums
#
# These are useful shared runtime values from Document 11, but their
# implementation may evolve through a versioned architecture change.
# ---------------------------------------------------------------------------


class C2FailureType(StrEnum):
    """High-level C2 runtime failure taxonomy."""

    NORMAL = "NORMAL"
    COMMUNICATION_FAILURE = "COMMUNICATION_FAILURE"
    HARDWARE_FAILURE = "HARDWARE_FAILURE"
    POSSIBLE_ZONE_DAMAGE = "POSSIBLE_ZONE_DAMAGE"
    UNKNOWN = "UNKNOWN"


class C2Action(StrEnum):
    """Baseline C2 recovery/escalation actions."""

    REQUEST_SD_REPLAY = "REQUEST_SD_REPLAY"
    ACTIVATE_BACKUP_SENSOR = "ACTIVATE_BACKUP_SENSOR"
    USE_NEIGHBOR_FUSION = "USE_NEIGHBOR_FUSION"
    SWITCH_BACKUP_HUB = "SWITCH_BACKUP_HUB"
    ESCALATE = "ESCALATE"
    NO_ACTION = "NO_ACTION"


class C1ContextStatus(StrEnum):
    """Availability/quality of context used by C1."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    STALE_CONTEXT = "STALE_CONTEXT"


class C4RoutingOutcome(StrEnum):
    """Routing outcome after C4 assessment."""

    ACCEPT = "ACCEPT"
    QUARANTINE = "QUARANTINE"
    REJECT = "REJECT"


class SilenceState(StrEnum):
    """Baseline state names for expected-report/silence handling."""

    ON_TIME = "ON_TIME"
    LATE = "LATE"
    SUSPECTED_SILENCE = "SUSPECTED_SILENCE"
    CONFIRMED_SILENCE = "CONFIRMED_SILENCE"
    DIAGNOSING = "DIAGNOSING"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class RecoveryStatus(StrEnum):
    """Execution status of a C2 recovery action."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class CommandStatus(StrEnum):
    """Device command acknowledgement state."""

    RECEIVED = "RECEIVED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class CommandType(StrEnum):
    """Candidate shared command types from Integration Contract v1."""

    APPLY_MODE = "APPLY_MODE"
    APPLY_SAMPLING_POLICY = "APPLY_SAMPLING_POLICY"
    REQUEST_STATUS = "REQUEST_STATUS"
    REQUEST_SD_REPLAY = "REQUEST_SD_REPLAY"
    ACTIVATE_BACKUP = "ACTIVATE_BACKUP"
    DEACTIVATE_BACKUP = "DEACTIVATE_BACKUP"
    TRIGGER_ALERT_DEVICE = "TRIGGER_ALERT_DEVICE"


class DataQualityStatus(StrEnum):
    """Explicit qualitative summary of downstream input quality."""

    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    INSUFFICIENT = "INSUFFICIENT"


class AssessmentContext(StrEnum):
    """Distinguishes historical runtime output from research reprocessing."""

    RUNTIME = "RUNTIME"
    RETROSPECTIVE = "RETROSPECTIVE"

class DecisionType(StrEnum):
    """High-level Decision Engine action category."""

    MODE_CHANGE = "MODE_CHANGE"
    MAINTAIN_MODE = "MAINTAIN_MODE"


class AlertSeverity(StrEnum):
    """Alert severity is intentionally separate from OperatingMode."""

    INFO = "INFO"
    WATCH = "WATCH"
    WARNING = "WARNING"
    EMERGENCY = "EMERGENCY"


class AlertStatus(StrEnum):
    """Lifecycle state of an operational alert."""

    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"


class DeviceLifecycleState(StrEnum):
    """Device lifecycle states for C4 device registry."""

    PROVISIONED = "PROVISIONED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    RETIRED = "RETIRED"