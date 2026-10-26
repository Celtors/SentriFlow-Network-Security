# Contributing

- `main` is always demo-able. Work on short-lived branches: `feat/<module>-<topic>`.
- Merge by pull request with at least one reviewer.
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- CI must pass (ruff, mypy, pytest, eslint, build).
- Any change in `backend/src/sentriflow/inspection/` or `core/` needs tests.
- `core/` and `inspection/` must never import from `api/`, `proxy/` or `os_adapters/`.
- Use dummy PII only in tests and demos.
