# AGENTS.md

## Repository orientation
Native Python Pulumi custom provider for Microsoft Power Platform.
Provider logic lives in `provider/`, a hand-crafted Python SDK in `sdk/python/`,
and generated SDKs for other languages in `sdk/{nodejs,go,dotnet}/`.
See `README.md` and `CONTRIBUTING.md` for architecture and development details.

## Non-negotiable rules

### Before every handoff
1. **Tests pass**: `python -m pytest tests/ -v`
2. **Linter clean**: `ruff check provider/ tests/`
3. **If `schema.json` was modified**, regenerate non-Python SDKs and stage
   the output as part of the same commit as the schema change:
   ```bash
   pulumi package gen-sdk . --language nodejs --out sdk
   pulumi package gen-sdk . --language go     --out sdk
   pulumi package gen-sdk . --language dotnet --out sdk
   ```
   > `sdk/python/` is maintained manually — do not regenerate it.

### Branching
- **Never push to `main`** — work on the PR branch or a dedicated feature branch.
- Commit in logical units; group schema changes + regenerated SDKs in one commit.

### Code invariants
- All provider code is `async/await`. No synchronous blocking I/O.
- Optional SDK constructor parameters: `Optional[str] = None`, never `str = None`.
- Shared helpers come from `utils.py` — never redeclare `pv_str` or
  `retry_with_backoff` locally.
- Immutable resource properties must use `PropertyDiffKind.UPDATE_REPLACE`
  in `diff()`, not `UPDATE`.

### What not to do
- Do not commit secrets, real tenant IDs, or real environment IDs.
- Do not add dev dependencies without updating `pyproject.toml`
  `[project.optional-dependencies] dev`.
