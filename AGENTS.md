# Repository Guidelines

## Project Structure & Module Organization

- `src/nexor/` - primary package: configuration, infrastructure, logging, observability, health and utilities.
- `tests/` - pytest-based suite mirroring functionality; keep test modules within this folder.
- Documentation lives under `docs/` with MkDocs pages, and `mkdocs.yml` at the root configures site generation.
- Lockfiles include `uv.lock` for reproducible `uv` environments; `pyproject.toml` holds metadata and dependency groups.

## Build, Test, and Development Commands

- `uv install` – creates the virtual environment defined by `uv.lock`. Add `--env dev` to include dev deps before development work.
- `uv run pytest` – exercises the pytest suite with the fast failure/tb settings from `pyproject.toml`. Run from the repo root.
- `uv run uvicorn my_service:app --reload` – example runtime command referenced in docs; adapt module path for real services.
- `uv run mkdocs build` / `uv run mkdocs serve` – rebuilds or previews the MkDocs site after editing `docs/`.

## Coding Style & Naming Conventions

- Python code targets 120‑char lines and single quotes (`ruff` enforces this setting). Follow existing Pydantic/asyncio idioms.
- Modules expose explicit exports via `__all__`; keep public helpers listed to aid mkdocstrings.
- Naming: use `CamelCase` for settings/models, `snake_case` for functions/variables, and prefix constants in `ALL_CAPS`.
- Formatting: rely on `ruff` (configure in `pyproject.toml`) and keep logic comments concise.

## Testing Guidelines

- Tests use `pytest` with `pytest-asyncio`. Naming matches `test_*.py` files and `test_*` functions, placed under `tests/`.
- Run `uv run pytest` after edits and before commits; no additional coverage threshold is enforced but keep assertions meaningful.

## Commit & Pull Request Guidelines

- Commit messages follow Conventional Commits using `commitizen` (see `[tool.commitizen]` in `pyproject.toml`). Examples: `feat: add scoped session helper`, `fix: handle missing alembic_url`.
- Pull requests should explain the change, reference relevant issues or tickets, and note any manual testing steps (e.g., `uv run pytest` or MkDocs preview). Include documentation updates when introducing public API changes.

## Configuration & Secrets

- Environment values should obey `ServiceSettings.required_keys`. Avoid committing secrets; use `SecretStr` fields and local env overrides.
