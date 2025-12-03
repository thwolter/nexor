# Nexor documentation

Nexor centralises shared configuration, logging and database helpers that the FDE services rely on.
This reference provides both the rationale for adopting the library and direct links into every module's API reference,
with the **mkdocstrings** handler providing live signatures and parameter descriptions.

## Purpose and scope

- **Shared configuration**: `ServiceSettings` and the supporting validation helpers keep environment-driven settings consistent from service to service.
- **Database lifecycle**: `nexor.infrastructure.db` exposes cached engines, scoped sessions and connection helpers so each application uses the same asyncpg/SQLAlchemy lifecycle.
- **Cross-cutting observability**: Logging and OpenTelemetry initialisation helpers reduce duplication while ensuring consistent resource attributes and exporters.
- **Health and utilities**: Lightweight health endpoints plus URL, fingerprint and CORS helpers further smooth integration into FDE services.

## Modules at a glance

| Module | Description |
| --- | --- |
| [api](modules/api.md) | TODO: document the API surface delivered by this module when more context is available. |
| [config](modules/config.md) | Application configuration helpers built on `ValidatedSettings`. |
| [health](modules/health.md) | FastAPI health-check routes tied to the shared database utilities. |
| [infrastructure](modules/infrastructure.md) | Async SQLAlchemy engine/session factories and asyncpg helpers. |
| [logging](modules/logging.md) | Loguru and stdlib logging initialisation with optional OTLP forwarding. |
| [observability](modules/observability.md) | OpenTelemetry resource, tracing and metrics bootstrap helpers. |
| [utils](modules/utils.md) | Reusable validation, fingerprinting and URL-normalisation helpers. |

## Navigating the reference

1. Start with [Installation](installation.md) to prep the virtual environment.
2. Follow [Quickstart](quickstart.md) for an end-to-end `ServiceSettings`/database usage snippet.
3. Dive into each module page for detailed API docs rendered by `mkdocstrings`.

## Keeping the docs current

Update the `::: nexor.<module>` sections whenever the exported handlers or settings change so mkdocstrings can regenerate signatures automatically.
