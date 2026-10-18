# GeoNex Research Workbench — Shared Frontend Foundation

## Scope

This is the initial **frontend foundation**, not the finished C3 dashboard. C1, C2 and C4 are intentionally placeholder pages. The C3 page connects to the existing standalone C3 API's `/health` and `/models` endpoints. **No cross-component AI integration is performed.**

## Setup on macOS / Windows / Linux

Requirements: Node.js 20.19+ or 22.12+; npm; Git. For the C3 status panel, start the existing Python FastAPI service separately.

From the GeoNex repository root:

```bash
cd apps/web
npm install
npm run dev
```

Open http://127.0.0.1:5173/ .

For C3 API connectivity, in a **separate terminal** from the repository root:

```bash
conda activate geonex
python -m apps.c3_workbench
```

Vite proxies `/api/c3/*` to `http://127.0.0.1:8033/*` **in development only**. This avoids browser CORS issues and keeps the backend's existing routes unchanged. The C3 API must be running for the C3 status panel to show models.

Validation:

```bash
cd apps/web
npm run typecheck
npm run build
```

## Component ownership

- C1 owner: `apps/web/src/features/c1/`
- C2 owner: `apps/web/src/features/c2/`
- C3 owner: `apps/web/src/features/c3/`
- C4 owner: `apps/web/src/features/c4/`

Shared (coordinate changes with the team): `apps/web/src/app/`, `layouts/`, `components/ui/`, `services/`, `styles/`, `types/`, `vite.config.ts`, `package.json`.

Each owner can replace their `pages/*Page.tsx` placeholder and add files in their own `components/`, `hooks/` and `api/` folders. Route prefixes are `/c1`, `/c2`, `/c3`, `/c4`. If you need new nested routes, coordinate updates in `src/app/App.tsx`.

Backend contracts for C1/C2/C4 have **not** been assumed. Their owners should agree API contracts before adding network calls. The C3 frontend currently only reads `/health` and `/models`; it does not expose training, upload, replay or live inference UI yet.

## Branching and committing

**Do not copy the ZIP over an existing `apps/web` directory without reviewing changes.** This package was prepared against the uploaded repository snapshot which had no `apps/web` folder.

Suggested process:

```bash
git status --short
git switch -c feature/shared-web-foundation
# copy apps/web and docs/GEONEX_WEB_TEAM_SETUP.md into repo
cd apps/web && npm install && npm run typecheck && npm run build && cd ../..
git add apps/web docs/GEONEX_WEB_TEAM_SETUP.md
git diff --cached --stat
git commit -m "feat(web): initialize shared GeoNex research workbench"
```

Push and open a pull request into your team's agreed integration branch. Teammates should branch from the merged foundation rather than copying files between branches. **Never commit `.env`, model checkpoints, or private datasets.**

## Current C3 demonstration evidence

Nine M4 API/direct-checkpoint comparisons passed for one validation record per horizon (15/30/60 min), three ablations each. These confirm integration consistency for the sampled records, **not** generalization, operational landslide risk accuracy or held-out test performance. The UI intentionally labels future features as planned.

## Next increment

C3 prediction explorer with validated schema and real API results; dataset upload and safe storage; training jobs and log streaming; golden-timeline replay with causal timestamp ordering; scientific charts and reproducibility metadata. For production deployment, configure API routing/authentication and resource limits explicitly; Vite dev proxy is not a production gateway.
