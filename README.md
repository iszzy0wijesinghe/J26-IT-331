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

### Python Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
pytest
```

### Web Frontend (React + TypeScript)

The web application is located in `apps/web/` and provides a React-based interface for all GeoNex components including C4.

```bash
cd apps/web
npm install
npm run dev
```

The development server will start at `http://127.0.0.1:5173/`

To build for production:

```bash
cd apps/web
npm run build
```

The built files will be in `apps/web/dist/`

### C4 Web Features

The C4 component in the web application includes:

- **How C4 Works**: Documentation of the C4 trust gate architecture and runtime path
- **Command Center**: Security operations summary with metrics for processed packets, trust labels, and routing outcomes
- **Telemetry Explorer**: Detailed inspection of simulated packets with filtering by device, trust label, and scenario
- **Threat Investigation**: Analysis of rejected, suspicious, or quarantined packets with reason code frequency analysis
- **Authentication & Device Trust**: Overview of mandatory cryptographic controls (HMAC, ECDSA, X.509 certificates)
- **ML Model Explorer**: Inspection of behavioral ML models, feature importance, holdout evaluation, and SHAP explanations
- **Device Registry & Policy**: Device lifecycle management, topology information, and security policy documentation
- **Data Storage & Diagnostics**: System diagnostics including model availability, database connectivity, and storage inventory
- **Model & Policy**: Security policy reference with routing outcomes and control definitions

All C4 features are now integrated into the React web application following the same structure as other components (C1, C2, C3).

## Shared invariants

Do not redefine operating modes, timestamp semantics, IDs, provenance, Golden Timeline semantics, or cross-component contracts inside individual components. Proposed architecture changes must be coordinated and documented.
