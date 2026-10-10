# 14_GEONEX_REPOSITORY_AND_IMPLEMENTATION_GUIDE.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** Repository, Development Environment and Implementation
Guide\
**Status:** Implementation Baseline v1\
**Depends on:** Documents 00--13\
**Audience:** Entire GeoNex development/research team\
**Purpose:** Convert the approved GeoNex architecture into a practical
shared repository that four members can implement independently while
preserving common contracts, reproducibility and integration.

------------------------------------------------------------------------

# 1. Why This Document Exists

Documents 00--13 define what GeoNex should do.

This document defines how the implementation should be organized.

It prevents:

``` text
four unrelated codebases
duplicate shared schemas
different naming conventions
hardcoded paths
component-specific database assumptions
notebook-only implementations
models that cannot be loaded by runtime
firmware packet incompatibility
merge conflicts caused by unclear ownership
```

------------------------------------------------------------------------

# 2. Implementation Philosophy

GeoNex should be:

``` text
MODULAR
+
CONTRACT-FIRST
+
LOCALLY DEPLOYABLE
+
REPRODUCIBLE
+
TESTABLE
+
RESEARCH-FRIENDLY
```

The prototype does not require unnecessary enterprise microservice
complexity.

------------------------------------------------------------------------

# 3. Recommended Architecture Style

Use a **modular monorepo**.

Benefits:

``` text
one shared contract source
one database migration history
one integration-test suite
clear component ownership
easy local development
reproducible project release
```

------------------------------------------------------------------------

# 4. Final Baseline Repository Structure

``` text
geonex/
├── apps/
│   ├── ingestion/
│   ├── decision_engine/
│   ├── api/
│   └── runtime_orchestrator/
│
├── components/
│   ├── c1_credibility/
│   ├── c2_diagnostics/
│   ├── c3_forecasting/
│   └── c4_trust/
│
├── firmware/
│   ├── type_a/
│   ├── type_b/
│   ├── backup_pipe/
│   ├── sensor_hub/
│   └── main_gateway/
│
├── shared/
│   ├── contracts/
│   ├── schemas/
│   ├── enums/
│   ├── telemetry/
│   ├── features/
│   ├── time/
│   ├── logging/
│   └── utils/
│
├── database/
│   ├── migrations/
│   ├── seeds/
│   ├── views/
│   └── queries/
│
├── data/
│   ├── manifests/
│   ├── synthetic/
│   ├── physical/
│   ├── external/
│   ├── processed/
│   └── splits/
│
├── models/
│   ├── registry/
│   ├── artifacts/
│   ├── preprocessors/
│   └── calibrators/
│
├── experiments/
│   ├── c1/
│   ├── c2/
│   ├── c3/
│   └── c4/
│
├── configs/
│   ├── common/
│   ├── development/
│   ├── test/
│   ├── demo/
│   └── components/
│
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── hardware/
│   ├── security/
│   └── end_to_end/
│
├── scripts/
│   ├── setup/
│   ├── data/
│   ├── train/
│   ├── evaluate/
│   ├── deploy/
│   └── maintenance/
│
├── docs/
│   ├── architecture/
│   ├── components/
│   ├── research/
│   ├── development/
│   ├── testing/
│   └── changes/
│
├── deployment/
│   ├── docker/
│   ├── manifests/
│   └── system/
│
├── notebooks/
│   ├── exploratory/
│   └── analysis/
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── CONTRIBUTING.md
```

------------------------------------------------------------------------

# 5. Structure Status

This structure is now the **recommended implementation baseline**.

Minor practical adjustments are allowed, but changing major shared
boundaries should follow the architecture-change procedure.

------------------------------------------------------------------------

# 6. `apps/`

`apps/` contains system-level runtime applications that are not owned by
a single research component.

``` text
apps/
├── ingestion/
├── decision_engine/
├── api/
└── runtime_orchestrator/
```

------------------------------------------------------------------------

# 7. Ingestion Application

Responsibilities:

``` text
receive gateway telemetry
validate transport/schema
persist raw packet
normalize observations
dispatch/queue downstream processing
```

It must not perform C1/C3 research logic internally.

------------------------------------------------------------------------

# 8. Decision Engine

Responsibilities:

``` text
consume C3 forecast
consume current severity/quality/health/trust
apply decision policy
select operating mode
create alerts
create device commands
```

It remains separate from C3.

------------------------------------------------------------------------

# 9. API Application

Potential responsibilities:

``` text
dashboard/backend access
system status
historical data
forecasts
alerts
administrative/test operations
```

Exact endpoints are deferred until implementation.

------------------------------------------------------------------------

# 10. Runtime Orchestrator

For the prototype, a lightweight orchestrator can coordinate:

``` text
C4
C1
C2 triggers
Golden Timeline updates
C3 forecasts
Decision Engine
```

This can initially be a Python process/service rather than a complex
message platform.

------------------------------------------------------------------------

# 11. `components/`

Each research contribution has an isolated package:

``` text
components/
├── c1_credibility/
├── c2_diagnostics/
├── c3_forecasting/
└── c4_trust/
```

------------------------------------------------------------------------

# 12. Standard Component Layout

Recommended:

``` text
component/
├── README.md
├── config/
├── data/
├── features/
├── models/
├── training/
├── evaluation/
├── service/
├── tests/
└── __init__.py
```

Component-specific needs may add subfolders.

------------------------------------------------------------------------

# 13. C1 Package

``` text
components/c1_credibility/
├── features/
│   ├── temporal.py
│   ├── neighbours.py
│   ├── rainfall.py
│   └── device_context.py
├── models/
├── training/
├── evaluation/
├── service/
└── tests/
```

C1 owns measurement-credibility logic only.

------------------------------------------------------------------------

# 14. C2 Package

``` text
components/c2_diagnostics/
├── expected_reports/
├── features/
├── diagnosis/
├── recovery/
├── models/
├── training/
├── evaluation/
├── service/
└── tests/
```

Separate:

``` text
silence detection
diagnosis
recovery orchestration
```

------------------------------------------------------------------------

# 15. C3 Package

``` text
components/c3_forecasting/
├── sequences/
├── features/
├── models/
├── training/
├── evaluation/
├── calibration/
├── service/
└── tests/
```

Keep sequence construction separate from neural-model code.

------------------------------------------------------------------------

# 16. C4 Package

``` text
components/c4_trust/
├── security/
├── features/
├── behavioural/
├── models/
├── training/
├── evaluation/
├── service/
└── tests/
```

Mandatory deterministic security logic should not be hidden inside
behavioral-model code.

------------------------------------------------------------------------

# 17. Component README

Every component README should state:

``` text
research problem
component boundary
inputs
outputs
dataset versions
baseline models
candidate model
training command
evaluation command
runtime interface
known limitations
owner
```

------------------------------------------------------------------------

# 18. Component Ownership

Baseline ownership:

``` text
C1 — R. M. Kanishka Harshana
C2 — Karunathilaka A. L.
C3 — W. A. I. Y. Wijesinghe
C4 — Geshani H. D. S.
```

Shared infrastructure remains team-owned.

------------------------------------------------------------------------

# 19. Ownership Does Not Mean Isolation

Each member may modify their component freely within the shared
contract.

They must not independently redefine:

``` text
IDs
timestamps
mode names
Golden Timeline
shared enums
database semantics
cross-component contracts
```

------------------------------------------------------------------------

# 20. `shared/`

This directory contains code that has one authoritative implementation
for the whole system.

``` text
shared/
├── contracts/
├── schemas/
├── enums/
├── telemetry/
├── features/
├── time/
├── logging/
└── utils/
```

------------------------------------------------------------------------

# 21. Shared-Code Rule

Code belongs in `shared/` only if multiple modules genuinely need the
same semantics.

Do not turn `shared/` into an unstructured dumping ground.

------------------------------------------------------------------------

# 22. `shared/contracts/`

Contains typed software-facing domain objects.

Examples:

``` text
TelemetryPacket
SensorObservation
C1Assessment
C2Diagnosis
C4TrustAssessment
GoldenObservation
C3Forecast
Decision
DeviceCommand
CommandAck
```

------------------------------------------------------------------------

# 23. Contract Implementation

For Python, a strong candidate is:

``` text
Pydantic
```

or equivalent typed validation.

The architecture is not dependent on one library, but runtime validation
is strongly recommended.

------------------------------------------------------------------------

# 24. Example Contract Style

Conceptually:

``` python
class SensorObservation(...):
    schema_version: str
    observation_id: str
    packet_id: str
    zone_id: str
    device_id: str
    sensor_instance_id: str
    observed_at: datetime
    received_at: datetime
    value: float | None
    unit: str | None
```

Exact code is implemented after schema review.

------------------------------------------------------------------------

# 25. `shared/schemas/`

Contains machine-readable schemas for:

``` text
JSON/event payloads
dataset manifests
deployment manifests
experiment manifests
```

where applicable.

------------------------------------------------------------------------

# 26. `shared/enums/`

Authoritative enums:

``` text
OperatingMode
SourceOrigin
RecoveryProvenance
ProcessingStatus
C1CredibilityLabel
C4TrustLabel
C2FailureType
C2Action
CommandStatus
AlertSeverity
```

------------------------------------------------------------------------

# 27. Enum Rule

Do not duplicate:

``` python
class OperatingMode(...)
```

inside C1, C2, C3 and firmware-facing applications.

Use the shared definition or generated compatible representation.

------------------------------------------------------------------------

# 28. `shared/telemetry/`

Potential shared logic:

``` text
packet parsing
measurement normalization
unit mapping
sequence helpers
common telemetry validation
```

Security-specific C4 logic remains in C4.

------------------------------------------------------------------------

# 29. `shared/features/`

Only truly common feature utilities belong here.

Examples:

``` text
rolling-window helpers
as-of joins
missingness masks
observation-age calculation
```

Component-specific scientific features stay inside components.

------------------------------------------------------------------------

# 30. `shared/time/`

Centralize:

``` text
UTC conversion
as-of checks
window boundaries
timestamp validation
clock-quality helpers
```

Time semantics are too important to reimplement differently in each
component.

------------------------------------------------------------------------

# 31. `shared/logging/`

Provide consistent structured logging with:

``` text
timestamp
level
service/component
correlation_id
zone_id
device_id
model_version
message
```

where applicable.

------------------------------------------------------------------------

# 32. Database Layer

``` text
database/
├── migrations/
├── seeds/
├── views/
└── queries/
```

The operational database baseline remains PostgreSQL + TimescaleDB.

------------------------------------------------------------------------

# 33. Migration Ownership

Database schema changes must occur through migrations.

Do not manually alter the shared development database and leave no
migration.

------------------------------------------------------------------------

# 34. Migration Naming

Conceptual:

``` text
0001_create_core_tables
0002_add_c4_assessments
0003_add_c1_assessments
...
```

Use the selected migration framework's convention.

------------------------------------------------------------------------

# 35. Seed Data

Seeds may include:

``` text
zones
device types
sensor definitions
test devices
initial policies
```

Never seed production/private secrets.

------------------------------------------------------------------------

# 36. Database Views

Views can expose:

``` text
Golden Timeline
latest device state
latest operating mode
recent forecast
```

when they simplify consistent queries.

------------------------------------------------------------------------

# 37. Repository/Data Access Layer

Applications/components should use defined repository/query functions
rather than scattering SQL everywhere.

Conceptual:

``` text
TelemetryRepository
AssessmentRepository
GoldenTimelineRepository
ForecastRepository
DecisionRepository
```

------------------------------------------------------------------------

# 38. Raw Data Access

Raw records remain accessible for:

``` text
audit
research
reprocessing
```

but normal downstream runtime should use approved repositories/views.

------------------------------------------------------------------------

# 39. `data/`

``` text
data/
├── manifests/
├── synthetic/
├── physical/
├── external/
├── processed/
└── splits/
```

This area is for research datasets/artifacts, not the live operational
database.

------------------------------------------------------------------------

# 40. Large Data Rule

Large datasets should not automatically be committed to Git.

Git should contain:

``` text
manifests
small samples
scripts
schemas
```

while large artifacts use controlled project storage.

------------------------------------------------------------------------

# 41. Sample Dataset

Each component may include a very small non-sensitive sample for:

``` text
unit tests
schema demonstration
pipeline smoke test
```

It must not be confused with final research data.

------------------------------------------------------------------------

# 42. `models/`

``` text
models/
├── registry/
├── artifacts/
├── preprocessors/
└── calibrators/
```

This implements Document 13 lifecycle requirements.

------------------------------------------------------------------------

# 43. Model Registry Metadata

Use machine-readable files or a lightweight registry database.

Example conceptual record:

``` yaml
model_version: C3_MODEL_012
status: CHAMPION
dataset_version: C3_DS_004
feature_schema_version: C3FS_003
artifact: ...
```

------------------------------------------------------------------------

# 44. Model Artifact Rule

Never use filenames like:

``` text
model_final.pkl
best_new_final2.pt
```

Use immutable version IDs.

------------------------------------------------------------------------

# 45. `experiments/`

Each component stores formal experiment configurations/results.

``` text
experiments/c3/
├── configs/
├── results/
└── manifests/
```

Large generated artifacts can be stored externally and referenced.

------------------------------------------------------------------------

# 46. Notebook Boundary

`notebooks/` is for:

``` text
exploration
visualization
analysis
```

not authoritative runtime code.

If a notebook develops important feature logic, move it into the
component/shared package.

------------------------------------------------------------------------

# 47. `configs/`

Configuration is separated from code.

``` text
configs/
├── common/
├── development/
├── test/
├── demo/
└── components/
```

------------------------------------------------------------------------

# 48. Common Configuration

May contain:

``` text
database host/port placeholders
logging
timezone policy
schema versions
general runtime options
```

Secrets are injected separately.

------------------------------------------------------------------------

# 49. Environment-Specific Configuration

Use separate configuration for:

``` text
development
test
demo
```

This prevents synthetic/test records from accidentally mixing with
official demo operation.

------------------------------------------------------------------------

# 50. Component Configuration

Examples:

``` text
C1 context-window settings
C2 silence-policy references
C3 history/horizon/model references
C4 behavioral threshold references
```

Research-critical configuration should be versioned.

------------------------------------------------------------------------

# 51. Environment Variables

Secrets/runtime-specific values use environment variables.

Example `.env.example`:

``` text
GEONEX_DB_HOST=
GEONEX_DB_PORT=
GEONEX_DB_NAME=
GEONEX_DB_USER=
GEONEX_DB_PASSWORD=
```

Never commit the actual `.env`.

------------------------------------------------------------------------

# 52. Configuration Precedence

Define one deterministic precedence.

Recommended concept:

``` text
defaults
→ environment config
→ environment variables/secrets
→ explicit CLI override for approved development tasks
```

Log effective non-secret configuration.

------------------------------------------------------------------------

# 53. `tests/`

``` text
tests/
├── unit/
├── contract/
├── integration/
├── hardware/
├── security/
└── end_to_end/
```

Component-local unit tests may also live inside component packages.

------------------------------------------------------------------------

# 54. Unit Tests

Test small deterministic behavior.

Examples:

``` text
C3 Δt calculation
C2 expected-report deadline
C1 feature calculation
C4 replay-state helper
```

------------------------------------------------------------------------

# 55. Contract Tests

Test Document 11 schemas.

Examples:

``` text
known enum accepted
invalid enum rejected
required timestamp missing rejected
model version preserved
```

------------------------------------------------------------------------

# 56. Integration Tests

Test module boundaries with actual/shared contracts.

Example:

``` text
C4 → C1 → Golden Timeline
```

------------------------------------------------------------------------

# 57. Hardware Tests

Hardware tests should be explicitly marked because they require:

``` text
ESP32
serial/LoRa
physical sensors
test rig
```

They should not run automatically on a developer laptop without
hardware.

------------------------------------------------------------------------

# 58. Security Tests

Include:

``` text
replay
tamper
unknown identity
authorized recovery replay
```

according to implemented C4 security design.

------------------------------------------------------------------------

# 59. End-to-End Tests

Implement Document 12 scenarios as reproducible tests/scripts where
possible.

------------------------------------------------------------------------

# 60. Pytest Markers

Candidate markers:

``` text
unit
integration
hardware
security
slow
e2e
```

This allows targeted execution.

------------------------------------------------------------------------

# 61. `scripts/`

Scripts provide stable entry points for repetitive tasks.

``` text
scripts/
├── setup/
├── data/
├── train/
├── evaluate/
├── deploy/
└── maintenance/
```

------------------------------------------------------------------------

# 62. Setup Scripts

Potential:

``` text
initialize database
create development directories
validate environment
seed test metadata
```

------------------------------------------------------------------------

# 63. Data Scripts

Potential:

``` text
build C1 dataset
build C2 dataset
build C3 sequences
build C4 dataset
validate manifest
```

------------------------------------------------------------------------

# 64. Training Scripts

Each component should expose a consistent command concept.

Example:

``` text
python -m components.c3_forecasting.training.train --config ...
```

Exact CLI is implemented later.

------------------------------------------------------------------------

# 65. Evaluation Scripts

Separate training from evaluation.

Example concept:

``` text
python -m components.c3_forecasting.evaluation.evaluate \
  --model-version ... \
  --dataset-version ...
```

------------------------------------------------------------------------

# 66. Deployment Scripts

Potential:

``` text
register candidate
promote model
activate deployment manifest
rollback model
```

Promotion must remain controlled.

------------------------------------------------------------------------

# 67. Maintenance Scripts

Potential:

``` text
database backup
artifact hash verification
registry consistency check
evidence export
```

------------------------------------------------------------------------

# 68. `docs/`

Organize the existing specification set.

Recommended:

``` text
docs/development/
  00_GEONEX_SYSTEM_DEVELOPMENT_PLAN.md

docs/architecture/
  01_GEONEX_END_TO_END_ARCHITECTURE.md
  02_GEONEX_DATA_DATABASE_ARCHITECTURE.md
  03_GEONEX_DATASET_ARCHITECTURE.md
  04_GEONEX_MODE_SAMPLING_AND_TIMING_SPECIFICATION.md
  11_GEONEX_INTEGRATION_CONTRACT.md

docs/components/
  05_C1_DEVELOPMENT_GUIDE.md
  06_C2_DEVELOPMENT_GUIDE.md
  07_C3_DEVELOPMENT_GUIDE.md
  08_C4_DEVELOPMENT_GUIDE.md

docs/research/
  09_GEONEX_MODEL_SELECTION_AND_JUSTIFICATION.md
  10_GEONEX_RESEARCH_THEORY_AND_CONCEPTS.md
  13_GEONEX_MLOPS_AND_REPRODUCIBILITY_PLAN.md

docs/testing/
  12_GEONEX_TESTING_AND_VALIDATION_PLAN.md
```

------------------------------------------------------------------------

# 69. Architecture Change Records

Use:

``` text
docs/changes/
```

for approved deviations from shared architecture.

Do not rewrite history silently.

------------------------------------------------------------------------

# 70. Firmware Repository Structure

``` text
firmware/
├── common/
├── type_a/
├── type_b/
├── backup_pipe/
├── sensor_hub/
└── main_gateway/
```

A `common/` folder may be added for shared embedded code if useful.

------------------------------------------------------------------------

# 71. Firmware Common Code

Potential shared embedded modules:

``` text
packet schema
device identity
timestamp/session
command handling
LoRa framing
logging
```

Hardware-specific sensor drivers remain with appropriate
targets/libraries.

------------------------------------------------------------------------

# 72. Firmware Build Tool

Use the toolchain most practical for the ESP32 implementation, such as:

``` text
PlatformIO
or
Arduino/ESP-IDF workflow
```

The exact choice should be standardized across the team where possible.

------------------------------------------------------------------------

# 73. Firmware Version

Every firmware build used for formal tests should expose/store:

``` text
firmware_version
```

in device status/telemetry where practical.

------------------------------------------------------------------------

# 74. Device Configuration

Do not hardcode all deployment identity into source.

Prefer configurable:

``` text
device_id
zone_id
device role
radio parameters
policy defaults
```

with secure handling of secrets.

------------------------------------------------------------------------

# 75. Device Secrets

Never commit:

``` text
private keys
shared secrets
credentials
```

to the repository.

Provision separately.

------------------------------------------------------------------------

# 76. Gateway Boundary

Main Gateway firmware handles:

``` text
LoRa/device communication
packet forwarding
commands
ACK forwarding
gateway-local control
```

It does not become the primary database/ML server.

------------------------------------------------------------------------

# 77. Main Computing System

The Lenovo ThinkCentre-class system runs the main software stack:

``` text
database
ingestion
component inference
Decision Engine
API/dashboard backend as needed
```

Actual process placement can be adjusted after performance tests.

------------------------------------------------------------------------

# 78. Python Package Baseline

For main-computer software, Python is recommended because:

``` text
ML ecosystem
data processing
research tooling
rapid integration
```

Other languages can be used for justified modules, but shared interfaces
remain language-neutral.

------------------------------------------------------------------------

# 79. Python Version

Freeze one supported Python version before implementation.

Do not let members independently use incompatible major/minor versions
for final environments.

------------------------------------------------------------------------

# 80. `pyproject.toml`

Use it to define:

``` text
project metadata
dependencies
development dependencies
test configuration
lint/format configuration where supported
```

A lock strategy should also be selected.

------------------------------------------------------------------------

# 81. Virtual Environment

Each developer uses an isolated environment.

Conceptually:

``` text
python -m venv .venv
```

or the selected dependency manager.

Do not install project dependencies globally as the official workflow.

------------------------------------------------------------------------

# 82. Dependency Groups

Separate where practical:

``` text
runtime
ml
development
test
optional hardware
```

to avoid unnecessary deployment dependencies.

------------------------------------------------------------------------

# 83. Heavy ML Libraries

Do not require PyTorch/TensorFlow for services that only run:

``` text
ingestion
database
Decision Engine
```

unless technically necessary.

------------------------------------------------------------------------

# 84. Code Style

Baseline:

``` text
PEP 8-compatible Python
type hints for shared/runtime code
clear docstrings for public APIs
small focused functions
meaningful names
```

------------------------------------------------------------------------

# 85. Formatter/Linter

Recommended candidates:

``` text
Ruff
Black
```

or an equivalent standardized combination.

Select one team configuration and commit it.

------------------------------------------------------------------------

# 86. Type Checking

Static typing tools such as:

``` text
mypy
pyright
```

are optional but useful for shared contracts/runtime code.

------------------------------------------------------------------------

# 87. Import Rule

Prefer package imports.

Avoid fragile:

``` python
sys.path.append("../../..")
```

in final code.

------------------------------------------------------------------------

# 88. Absolute Paths

Do not hardcode personal paths such as:

``` text
D:\Projects\...
C:\Users\...
/Users/name/...
```

Use project-relative/configured paths.

------------------------------------------------------------------------

# 89. Path Handling

Use:

``` python
pathlib.Path
```

or equivalent portable path utilities.

------------------------------------------------------------------------

# 90. Logging vs Print

Runtime services use structured logging.

`print()` is acceptable for small CLI outputs/debugging, but not as the
primary operational logging system.

------------------------------------------------------------------------

# 91. Exception Handling

Do not use broad silent patterns such as:

``` python
try:
    ...
except:
    pass
```

Failures affecting data/model integrity must be visible.

------------------------------------------------------------------------

# 92. Scientific Constants

Research thresholds/windows should not be scattered as magic numbers.

Put them in:

``` text
versioned config
named constants
policy definitions
```

with explanation.

------------------------------------------------------------------------

# 93. DataFrame Column Names

Canonical ML columns should follow stable `snake_case`.

Dataset builders should validate expected columns before training.

------------------------------------------------------------------------

# 94. Unit Naming

Include units in schema metadata rather than relying only on column
names.

If useful, explicit names such as:

``` text
delta_t_seconds
tilt_rate_deg_h
```

can reduce ambiguity.

------------------------------------------------------------------------

# 95. Model Interface

Every component model wrapper should expose a stable abstraction.

Conceptual:

``` python
class ComponentModel:
    def load(...): ...
    def validate_input(...): ...
    def predict(...): ...
    def metadata(...): ...
```

Framework-specific details remain internal.

------------------------------------------------------------------------

# 96. Service Interface

Each component service handles:

``` text
contract validation
feature retrieval/build
model inference
postprocessing
output contract
error status
logging
```

------------------------------------------------------------------------

# 97. Training Code Is Separate

Do not place:

``` text
model.fit(...)
```

inside runtime service startup or prediction handlers.

------------------------------------------------------------------------

# 98. Feature Code Reuse

Runtime and training should call the same tested feature logic where
feasible.

This minimizes training-serving skew.

------------------------------------------------------------------------

# 99. Database Session Management

Centralize connection/session handling.

Do not open unmanaged database connections throughout component code.

------------------------------------------------------------------------

# 100. Transaction Boundaries

Persist raw telemetry before downstream ML processing.

A C3 error must not roll back a successfully received raw packet.

------------------------------------------------------------------------

# 101. Repository Interfaces

Conceptual:

``` python
class GoldenTimelineRepository:
    def get_as_of(...): ...
```

This lets C3 request runtime-equivalent history without knowing table
internals.

------------------------------------------------------------------------

# 102. As-Of Query

C3's repository must enforce:

``` text
available_at <= forecast_origin
```

This rule should be tested centrally.

------------------------------------------------------------------------

# 103. Golden Timeline Builder

Implement as a dedicated integration/data module rather than inside C3.

C3 consumes it; C3 does not own truth-selection policy.

------------------------------------------------------------------------

# 104. Expected-Report Scheduler

Implement as a C2-owned or shared runtime module with explicit contract.

It consumes:

``` text
last accepted report
applied mode/policy
grace rules
```

------------------------------------------------------------------------

# 105. Decision Policy Module

Decision Engine policy should be independently testable.

Conceptual:

``` python
decision = policy.evaluate(context)
```

Do not bury policy inside API routes.

------------------------------------------------------------------------

# 106. Device Command Service

Separate:

``` text
decision creation
```

from:

``` text
command delivery/retry/ACK tracking
```

------------------------------------------------------------------------

# 107. Runtime Orchestration Baseline

Initial practical sequence:

``` text
receive packet
→ persist
→ C4
→ normalize/eligible observations
→ C1
→ Golden Timeline
→ trigger/update C3 as policy requires
→ Decision Engine
→ command/alert
```

C2 scheduler runs independently for expected-report failures.

------------------------------------------------------------------------

# 108. Queue Strategy

Start simple.

Possible:

``` text
in-process/local task queue
database-backed work queue
lightweight message broker
```

Choose only if needed by measured concurrency/reliability.

Do not introduce Kafka-class complexity without justification.

------------------------------------------------------------------------

# 109. Synchronous vs Asynchronous

Synchronous calls are acceptable for early integration if
latency/reliability are sufficient.

Move to asynchronous processing where:

``` text
radio arrival must not block
model processing is slow
retries are required
independent C2 timers run
```

------------------------------------------------------------------------

# 110. API Framework

A lightweight Python API framework such as FastAPI is a reasonable
candidate.

It is not architecturally mandatory.

------------------------------------------------------------------------

# 111. Database ORM

An ORM/query toolkit may be used for maintainability.

Raw SQL remains appropriate for:

``` text
Timescale/time-series queries
performance-sensitive views
complex as-of operations
```

Keep semantics tested either way.

------------------------------------------------------------------------

# 112. Migration Framework

Select one migration framework compatible with the database stack.

For Python/SQLAlchemy ecosystems, Alembic is a reasonable candidate.

Tool choice is secondary to maintaining migration history.

------------------------------------------------------------------------

# 113. Docker Baseline

Docker Compose is recommended as a development/demo candidate for:

``` text
PostgreSQL/TimescaleDB
main software services
optional experiment tracker
```

Hardware interfaces may require host/device configuration.

------------------------------------------------------------------------

# 114. Docker Is Not Mandatory for Firmware

ESP32 firmware remains built/flashed using the embedded toolchain.

------------------------------------------------------------------------

# 115. Development Services

Conceptual Compose stack:

``` text
database
ingestion
runtime/orchestrator
api
optional MLflow
```

Components can initially run inside one runtime process if simpler.

------------------------------------------------------------------------

# 116. Service Decomposition Rule

Do not split every component into a network microservice merely because
directories are modular.

A module boundary can exist inside one process.

------------------------------------------------------------------------

# 117. Local Setup Flow

Target developer workflow:

``` text
clone repository
→ create environment
→ install dependencies
→ copy .env.example to local .env
→ start database
→ run migrations
→ seed development metadata
→ run tests
→ start software stack
```

------------------------------------------------------------------------

# 118. Setup Validation

Provide a script that checks:

``` text
Python version
required environment variables
database connection
schema version
model/artifact availability
```

------------------------------------------------------------------------

# 119. First-Run Model Behavior

If no approved model exists:

``` text
service readiness = false
```

or use an explicitly configured mock/development model.

Do not silently create a random model.

------------------------------------------------------------------------

# 120. Mock Mode

Development may support:

``` text
GEONEX_MOCK_C1
GEONEX_MOCK_C2
GEONEX_MOCK_C3
GEONEX_MOCK_C4
```

conceptually.

Mock outputs must be clearly tagged and disabled for formal
research/demo unless intentionally used.

------------------------------------------------------------------------

# 121. Simulator

A telemetry simulator is strongly recommended.

It can emit:

``` text
normal packets
genuine environmental changes
sensor anomalies
silence
replay
mode transitions
```

using shared packet contracts.

------------------------------------------------------------------------

# 122. Simulator Boundary

Simulator output must be marked:

``` text
source_origin = SIMULATED
```

and isolated from physical evidence.

------------------------------------------------------------------------

# 123. Synthetic Data Generator

Research synthetic generators are different from runtime simulator
tooling.

Both must be versioned.

------------------------------------------------------------------------

# 124. CLI Commands

Aim for consistent developer commands.

Conceptual:

``` text
geonex db migrate
geonex test
geonex run
geonex train c3 --config ...
geonex evaluate c3 --experiment ...
```

A custom CLI is optional; scripts can provide equivalent functionality.

------------------------------------------------------------------------

# 125. Makefile/Task Runner

A simple task runner can standardize commands:

``` text
setup
test
lint
db-up
db-migrate
run
```

Tool choice is flexible.

------------------------------------------------------------------------

# 126. Git Branch Strategy

Recommended lightweight workflow:

``` text
main
feature/<component-or-task>
fix/<issue>
docs/<topic>
```

Avoid long-lived isolated member branches that diverge for months.

------------------------------------------------------------------------

# 127. `main` Branch

`main` should remain:

``` text
integratable
tested
reviewed
```

Formal demo releases are tagged.

------------------------------------------------------------------------

# 128. Component Feature Branch

Examples:

``` text
feature/c1-neighbour-features
feature/c2-silence-scheduler
feature/c3-sequence-builder
feature/c4-replay-check
```

------------------------------------------------------------------------

# 129. Pull Request Rule

Changes to shared areas require review by at least another relevant team
member.

Especially:

``` text
shared/
database/
integration contracts
Decision Engine
firmware packet schema
```

------------------------------------------------------------------------

# 130. Component-Local Changes

Component owner can move quickly inside:

``` text
components/cX_.../
```

provided shared interfaces remain unchanged and tests pass.

------------------------------------------------------------------------

# 131. Merge Conflict Prevention

Before major shared work:

``` text
communicate ownership
keep branches short
pull/rebase/merge regularly
avoid four people editing same shared file unnecessarily
```

------------------------------------------------------------------------

# 132. Commit Style

Use meaningful commits.

Examples:

``` text
feat(c3): add time-aware sequence masks
fix(c2): preserve observed_at during SD replay
test(c4): add unauthorized replay case
docs(shared): clarify available_at semantics
```

Exact conventional-commit enforcement is optional.

------------------------------------------------------------------------

# 133. Do Not Commit Generated Noise

Avoid committing:

``` text
__pycache__
IDE state
temporary CSV exports
local logs
large checkpoints
.env
```

unless intentionally required.

------------------------------------------------------------------------

# 134. Code Review Checklist

Review:

``` text
contract compatibility
tests
timestamp semantics
provenance
error handling
hardcoded values
leakage risk
security/secrets
documentation
```

not only syntax.

------------------------------------------------------------------------

# 135. Shared-Contract Change Review

Any PR changing:

``` text
shared contracts
enum meaning
timestamp meaning
Golden Timeline
mode names
```

must reference an approved architecture change record.

------------------------------------------------------------------------

# 136. Database Change Review

Check:

``` text
migration exists
backward impact
indexes
constraints
data migration
test updates
```

------------------------------------------------------------------------

# 137. ML Change Review

Check:

``` text
dataset version
split
feature allowlist
leakage tests
baseline fairness
model artifact version
```

------------------------------------------------------------------------

# 138. Firmware Change Review

Check:

``` text
packet compatibility
power impact
sampling behavior
sequence/session behavior
command handling
```

------------------------------------------------------------------------

# 139. Definition of Done --- Code Task

A task is done when:

``` text
implementation complete
tests added/passing
shared contract respected
configuration documented
errors handled
no secrets/hardcoded local paths
relevant docs updated
```

------------------------------------------------------------------------

# 140. Definition of Done --- ML Experiment

An experiment is done when:

``` text
experiment ID assigned
config saved
dataset/split known
code version known
metrics saved
artifact saved
interpretation recorded
```

------------------------------------------------------------------------

# 141. Definition of Done --- Component

Component implementation baseline is done when:

``` text
runtime service works
training pipeline works
evaluation pipeline works
model versioning works
component tests pass
integration contract passes
failure behavior exists
research baselines/ablations executable
```

------------------------------------------------------------------------

# 142. Definition of Done --- Firmware Target

A firmware target is done when:

``` text
correct sensors initialized
identity configured
timestamps/sequence work
telemetry contract works
mode policy works
commands work
local failure handling works
hardware tests pass
```

------------------------------------------------------------------------

# 143. Development Sequence

Recommended implementation order:

``` text
PHASE 1 — repository + shared contracts
PHASE 2 — database + ingestion
PHASE 3 — simulator + raw telemetry
PHASE 4 — C4 deterministic trust path
PHASE 5 — C1 credibility path
PHASE 6 — Golden Timeline
PHASE 7 — C2 scheduler/diagnosis/recovery
PHASE 8 — C3 feature/forecast path
PHASE 9 — Decision Engine
PHASE 10 — command/ACK
PHASE 11 — firmware integration
PHASE 12 — full testing/research experiments
```

Parallel component model research can proceed using contract-conforming
mocks.

------------------------------------------------------------------------

# 144. Phase 1 --- Repository Bootstrap

Create:

``` text
directory structure
Python project
shared enums/contracts
test framework
config loader
logging
Git ignore
basic CI if available
```

------------------------------------------------------------------------

# 145. Phase 2 --- Database

Implement migrations for the approved Document 02 entities.

Do not start by building every optional table.

Prioritize runtime path:

``` text
zones
devices
sensor metadata
telemetry_packets
sensor_observations
C4/C1
Golden Timeline
modes
forecasts
decisions
commands
```

then add C2/research/MLOps entities as required.

------------------------------------------------------------------------

# 146. Phase 3 --- Simulator

Before all hardware is ready, generate contract-valid packets.

This allows integration work to continue independently.

------------------------------------------------------------------------

# 147. Phase 4 --- C4 Minimum Path

First implement:

``` text
device registration/identity plumbing
basic freshness/sequence handling
security result contract
```

using only actually approved security mechanisms.

Behavioral ML follows the C4 development guide.

------------------------------------------------------------------------

# 148. Phase 5 --- C1 Minimum Path

Implement:

``` text
observation retrieval
context builder
simple baseline
assessment contract
```

before advanced model tuning.

------------------------------------------------------------------------

# 149. Phase 6 --- Golden Timeline

Implement:

``` text
selection policy
provenance
available_at
as-of query
```

and automated leakage tests.

This is a critical integration milestone.

------------------------------------------------------------------------

# 150. Phase 7 --- C2

Implement:

``` text
expected-report scheduler
silence event
baseline diagnosis
backup verification
recovery provenance
```

then ML candidate.

------------------------------------------------------------------------

# 151. Phase 8 --- C3

Implement in this order:

``` text
dataset audit
target specification
split
feature/sequence builder
simple baseline
boosted-tree baseline
standard recurrent baseline
time-aware candidate
calibration
runtime service
```

Do not begin with a complex GRU before the data pipeline is trustworthy.

------------------------------------------------------------------------

# 152. Phase 9 --- Decision Engine

Start with deterministic versioned policy.

Test:

``` text
escalation
de-escalation
hysteresis
component unavailable
data quality degradation
```

------------------------------------------------------------------------

# 153. Phase 10 --- Commands

Implement:

``` text
command record
gateway delivery
ACK
retry
expiry
idempotency
```

before relying on mode changes in end-to-end tests.

------------------------------------------------------------------------

# 154. Phase 11 --- Hardware Integration

Replace simulator inputs progressively:

``` text
gateway
one device
one sensor class
full pipe
hub
backup
second zone
```

Do not connect everything simultaneously before basic paths are proven.

------------------------------------------------------------------------

# 155. Phase 12 --- Research Validation

Execute Document 12:

``` text
baselines
ablations
stress tests
fault injection
security tests
adaptive sampling
latency
power
end-to-end
```

------------------------------------------------------------------------

# 156. Member Parallel Work

While shared infrastructure is built:

``` text
C1 member → dataset audit/features/baselines
C2 member → fault taxonomy/silence logic/recovery experiments
C3 member → dataset audit/sequences/baselines
C4 member → threat model/security design/behavioral baselines
```

using frozen contracts.

------------------------------------------------------------------------

# 157. Integration Cadence

Do not wait until the end.

Recommended team practice:

``` text
regular integration into main
contract tests on every shared change
end-to-end smoke test after major milestone
```

------------------------------------------------------------------------

# 158. Component Mock Deadline

Mocks are temporary.

Each mock should have an issue/milestone for replacement by real
component output before final integrated evaluation.

------------------------------------------------------------------------

# 159. Data Migration from Existing C3 Work

Existing development files should be copied into a clearly historical
area first.

Example:

``` text
data/synthetic/legacy/c3/
```

Then audit them against Document 03/07/13 before creating formal dataset
versions.

------------------------------------------------------------------------

# 160. Never Destroy Existing Research Work

Migration means:

``` text
preserve original
document source
create new audited version
```

not edit the only copy.

------------------------------------------------------------------------

# 161. Existing Prototype Evidence

Physical test photographs, notes and measurements should be organized
under evidence/test records, not mixed into training-data directories
unless converted through a documented dataset process.

------------------------------------------------------------------------

# 162. Research Paper Work

Paper-specific scripts/results should reference the same formal
experiment registry.

Avoid creating an isolated paper-only copy of the model that cannot be
reproduced from the repository.

------------------------------------------------------------------------

# 163. Documentation Updates

When implementation proves an assumption wrong:

``` text
update architecture through change process
```

Do not force code to obey an invalid assumption merely because an old
document said it.

------------------------------------------------------------------------

# 164. README Role

The root `README.md` should become the first page for any developer.

It should explain:

``` text
what GeoNex is
architecture summary
repository map
quick start
development commands
documentation map
component ownership
```

------------------------------------------------------------------------

# 165. CONTRIBUTING Role

`CONTRIBUTING.md` should define:

``` text
branching
commits
PR review
tests
shared-contract rules
database migrations
ML experiment rules
documentation changes
```

------------------------------------------------------------------------

# 166. Security Rule

No development convenience may bypass mandatory security in a way that
can accidentally become the demo/field configuration.

Development bypasses must be:

``` text
explicit
environment-gated
logged
disabled by default outside development
```

------------------------------------------------------------------------

# 167. Research Rule

No convenient feature may be added to training merely because it
improves accuracy.

Every feature must satisfy:

``` text
available at runtime?
scientifically meaningful?
not target-derived?
not post-outcome?
```

------------------------------------------------------------------------

# 168. Time Rule

Any code handling temporal data must explicitly know whether a timestamp
means:

``` text
observed
received
available
processed
forecast origin
```

Never use a generic `timestamp` variable across critical logic without
context.

------------------------------------------------------------------------

# 169. Provenance Rule

Any value that is:

``` text
recovered
estimated
derived
synthetic
external
```

must retain that provenance.

------------------------------------------------------------------------

# 170. Failure Rule

Component unavailability is data.

It must be represented explicitly and handled by system policy.

------------------------------------------------------------------------

# 171. Model Rule

Runtime code loads a registered model version.

It does not search a directory for "latest file" and assume that is the
correct model.

------------------------------------------------------------------------

# 172. Database Rule

The operational database is not a scratch notebook store.

Experimental intermediate tables must be clearly separated or use
research schemas/artifacts.

------------------------------------------------------------------------

# 173. Test Rule

A feature that changes shared behavior is incomplete without tests.

------------------------------------------------------------------------

# 174. Demo Rule

The demo should run from a tagged/manifested system release.

Do not demo from four developers' unmerged local branches.

------------------------------------------------------------------------

# 175. Suggested Release Tags

Conceptual:

``` text
v0.1-integration
v0.2-hardware
v0.3-research
v1.0-demo
```

Actual version scheme can be finalized later.

------------------------------------------------------------------------

# 176. Release Checklist

Before tagging:

``` text
tests pass
migrations current
model manifest valid
firmware versions recorded
no secrets
docs updated
known limitations recorded
```

------------------------------------------------------------------------

# 177. Backup Before Demo

Back up:

``` text
database
champion models
configs
deployment manifest
firmware binaries/source
critical evidence
```

------------------------------------------------------------------------

# 178. Recovery Drill

Before the final demonstration, rehearse recovery from:

``` text
database/service restart
model load failure
gateway reconnect
```

as appropriate.

------------------------------------------------------------------------

# 179. AI Assistant Rule for All Member Workspaces

Every member's coding AI should receive:

> **Implement only within the approved GeoNex repository and shared
> integration contracts. Do not rename shared IDs, redefine timestamp
> meanings, alter operating modes, bypass provenance, move Decision
> Engine logic into C3, merge C1/C4 responsibilities, or change
> cross-component schemas without an approved architecture change. Treat
> candidate algorithms, thresholds and security mechanisms as
> unfinalized unless the corresponding GeoNex document explicitly
> freezes them. Add tests for shared behavior and preserve
> reproducibility metadata for ML experiments.**

------------------------------------------------------------------------

# 180. C1 Developer AI Rule

Additionally:

> **C1 classifies measurement credibility. It does not authenticate the
> source, erase raw measurements, or reject genuine extreme events
> merely because they are unusual.**

------------------------------------------------------------------------

# 181. C2 Developer AI Rule

Additionally:

> **C2 is triggered by missing/late expected telemetry, diagnoses the
> reason, and manages provenance-aware recovery. Do not reduce C2 to
> imputation or one fixed timeout.**

------------------------------------------------------------------------

# 182. C3 Developer AI Rule

Additionally:

> **C3 forecasts future risk from runtime-eligible variable-rate
> temporal history. Preserve Δt, missingness, mode and provenance. Do
> not use target-derived risk fields or make C3 directly control
> operating modes.**

------------------------------------------------------------------------

# 183. C4 Developer AI Rule

Additionally:

> **C4 protects telemetry trust. Mandatory deterministic security cannot
> be replaced or overridden by behavioral ML. Do not claim
> cryptographic/attestation mechanisms that have not actually been
> implemented and tested.**

------------------------------------------------------------------------

# 184. Implementation Anti-Patterns

Avoid:

``` text
one giant main.py
one giant notebook
one CSV as the live database
copy-pasted schemas
hardcoded personal paths
models named final.pkl
random-row temporal splits
silent exception handling
training inside runtime
manual database edits
component-specific mode enums
raw-value overwriting
automatic self-labeling
```

------------------------------------------------------------------------

# 185. Good Implementation Pattern

Prefer:

``` text
small typed modules
shared contracts
versioned configuration
database migrations
explicit repositories
reproducible dataset builders
component model wrappers
contract tests
integration tests
registered artifacts
```

------------------------------------------------------------------------

# 186. First Repository Milestone

The first coding milestone should produce:

``` text
repository skeleton
Python environment
shared enums
shared contracts
config loader
structured logging
database connection
initial migrations
pytest setup
simulator skeleton
```

No advanced AI model is required for this milestone.

------------------------------------------------------------------------

# 187. Second Repository Milestone

Produce:

``` text
simulated telemetry
raw packet persistence
normalized observations
C4 mock/minimum gate
C1 mock/minimum assessment
Golden Timeline
```

with traceable IDs.

------------------------------------------------------------------------

# 188. Third Repository Milestone

Produce:

``` text
C2 expected-report scheduler
silence event
recovery path
C3 baseline forecast
Decision Engine baseline
```

------------------------------------------------------------------------

# 189. Fourth Repository Milestone

Produce:

``` text
gateway/device command path
ACK
mode-conditioned sampling
hardware telemetry
```

------------------------------------------------------------------------

# 190. Fifth Repository Milestone

Replace mocks with validated component models progressively and run full
Document 12 experiments.

------------------------------------------------------------------------

# 191. Definition of Repository Success

The repository succeeds when a new team member can:

``` text
clone it
read README
set up environment
start database
run migrations
run tests
start system
simulate telemetry
trace one packet end-to-end
train/evaluate a component
identify deployed models
```

without hidden knowledge from one developer's computer.

------------------------------------------------------------------------

# 192. What Is Frozen by Document 14

1.  GeoNex uses a modular monorepo baseline.
2.  System applications, research components, firmware, shared
    contracts, database, data, models, experiments, configs, tests and
    docs are separated.
3.  C1--C4 each have independent component packages.
4.  Shared contracts/enums have one authoritative implementation.
5.  Database changes use migrations.
6.  Live operational data is separated from offline research datasets.
7.  Large generated data/model artifacts are not blindly committed to
    Git.
8.  Runtime and training code are separated.
9.  Feature logic is reused between training/runtime where practical.
10. C3 accesses runtime history through an as-of-aware Golden Timeline
    interface.
11. Decision Engine remains outside C3.
12. C2 silence scheduling is explicit.
13. Firmware and main-computer software are separate project areas.
14. Device secrets are never committed.
15. Python is the recommended main-computer implementation language.
16. Configuration is externalized from code.
17. Development/test/demo environments are separated.
18. Unit, contract, integration, hardware, security and E2E tests are
    distinct.
19. Notebooks are exploratory/analytical, not authoritative runtime
    implementations.
20. Component model wrappers hide ML-framework details.
21. Repository code uses portable paths and avoids developer-specific
    absolute paths.
22. Git work is integrated regularly rather than four long-lived
    isolated branches.
23. Shared changes require coordinated review.
24. Simulator data is clearly marked and isolated.
25. Existing historical research data is preserved during migration.
26. Formal demo runs use a tagged/manifested release.
27. Component AI assistants must obey the same shared architecture.
28. Implementation proceeds infrastructure-first rather than beginning
    with complex models.
29. Mocks are allowed for parallel development but must conform to
    shared contracts.
30. The repository must be reproducible by another team member without
    hidden local state.

------------------------------------------------------------------------

# 193. Decisions Still Deferred

This guide intentionally does not freeze:

``` text
FastAPI as mandatory framework
SQLAlchemy as mandatory ORM
Alembic as mandatory migration tool
PlatformIO vs ESP-IDF/Arduino
Ruff/Black exact combination
mypy/pyright adoption
Docker for every service
message broker technology
exact Python minor version
exact dependency manager
exact CI provider
exact release numbering
exact CLI/task runner
exact API endpoints
```

These can be selected during repository bootstrap without changing
GeoNex research architecture.

------------------------------------------------------------------------

# 194. Immediate Action Plan

The next practical steps are:

``` text
1. Create the geonex repository root.
2. Add the folder skeleton from this document.
3. Move Documents 00–14 into docs/.
4. Create pyproject.toml.
5. Create .gitignore and .env.example.
6. Implement shared enums.
7. Implement shared contracts from Document 11.
8. Set up pytest.
9. Start database migrations from Document 02.
10. Create telemetry simulator.
11. Run the first contract-valid packet into the database.
12. Build component services progressively.
```

------------------------------------------------------------------------

# 195. Next Files

After this implementation guide, create:

``` text
README.md
CONTRIBUTING.md
```

These should be concise operational entry points and must reference the
authoritative detailed documents rather than duplicate all 00--14
content.

After those files, repository bootstrap and actual implementation can
begin.

------------------------------------------------------------------------

# Document 14 Status

**`14_GEONEX_REPOSITORY_AND_IMPLEMENTATION_GUIDE.md` --- IMPLEMENTATION
BASELINE v1 READY**

The governing implementation rule is:

``` text
ONE REPOSITORY
     ↓
ONE SHARED CONTRACT LANGUAGE
     ↓
FOUR INDEPENDENT RESEARCH COMPONENTS
     ↓
VERSIONED DATA + MODELS + POLICIES
     ↓
CONTINUOUS INTEGRATION
     ↓
REPRODUCIBLE END-TO-END GEONEX SYSTEM
```

The goal is not merely to make four models run.

The goal is to make four independently researched components behave as
**one traceable, testable and reproducible landslide early-warning
system**.
