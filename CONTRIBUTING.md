# Contributing to GeoNex

GeoNex is developed concurrently by four research-component owners plus shared integration work.

## Branches

Use short-lived branches such as:

- `feature/c1-...`
- `feature/c2-...`
- `feature/c3-...`
- `feature/c4-...`
- `feature/shared-...`
- `fix/...`
- `docs/...`

Keep `main` integratable.

## Shared changes

Changes to `shared/`, `database/`, cross-component contracts, operating modes, timestamp semantics, Golden Timeline semantics, or firmware packet schemas require coordinated review.

## Before merge

Run tests, preserve contract compatibility, add tests for shared behavior, do not commit secrets or developer-specific absolute paths, and record ML dataset/split/model versions for formal experiments.
