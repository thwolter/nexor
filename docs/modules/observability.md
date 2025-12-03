# `nexor.observability`

## Overview

Observability helpers centralise the OpenTelemetry configuration that FDE services otherwise repeat.
They build a `Resource` with service metadata, initialise tracing and metrics providers, and optionally instrument FastAPI or worker processes.

| Helper | Description |
| --- | --- |
| `build_resource` | Constructs a `Resource` using `service.name`, `deployment.environment`, and optional extras. |
| `parse_otlp_headers` | Parses comma-separated `key=value` pairs into a header dictionary for OTLP exporters. |
| `init_observability` | Bootstraps `TracerProvider` and `MeterProvider` with OTLP span/metric processors. |
| `init_otel_fastapi` | Adds FastAPI instrumentation via `FastAPIInstrumentor` after ensuring providers exist. |
| `init_otel_worker` | Initialises global providers for background worker processes. |
| `get_tracer` | Convenience wrapper for `trace.get_tracer`. |

## Example

```python
from nexor.observability import init_observability, init_otel_fastapi

resource_kwargs = {
    'service_name': 'my-service',
    'deployment_environment': 'production',
}
init_observability(**resource_kwargs)
init_otel_fastapi(app, **resource_kwargs)
```

If `FastAPIInstrumentor` is unavailable, `init_otel_fastapi` falls back gracefully, but the shared providers are still initialised. Pass `extra` to add service-specific resource attributes.

## API Reference

::: nexor.observability
