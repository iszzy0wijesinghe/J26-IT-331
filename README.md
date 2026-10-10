# GeoNex

GeoNex is a research prototype for a smart landslide early-warning system using IoT, Edge AI and risk analytics.

## Research components

- **C1:** Rainfall Regime-Aware Sensor Credibility Classification
- **C2:** Silent-Pattern Diagnostic Classification via Backup Pipe Verification
- **C3:** Mode-Conditioned Variable-Rate Multi-Sensor Temporal Forecasting
- **C4:** Trusted Telemetry Provenance and Device Attestation

The Decision Engine is separate from C3 and owns operational mode/action decisions.

## Current development status

Repository bootstrap started. Shared contracts and enums are the first implementation layer. Detailed authoritative specifications are under `docs/`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
pytest
```

## Shared invariants

Do not redefine operating modes, timestamp semantics, IDs, provenance, Golden Timeline semantics, or cross-component contracts inside individual components. Proposed architecture changes must be coordinated and documented.
