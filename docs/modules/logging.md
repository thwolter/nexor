# `nexor.logging`

## Overview

Logging helpers configure both Loguru and the standard library logger to share defaults across FDE services.
They also wire optional OTLP forwarding that reuses the resource construction logic from `nexor.observability`.

| Function | Purpose |
| --- | --- |
| `configure_loguru_logging` | Sets up Loguru sinks, optionally bridges to stdlib, and enables OTLP forwarding when requested. |
| `configure_std_logging` | Applies `logging.basicConfig`, respects user-defined formatter/level, then optionally wires OTLP. |
| `LogExporterSettings` | Captures OTLP configuration (endpoint, headers, service namespace) and resource overrides. |

## Example

```python
from nexor.logging import configure_loguru_logging, LogExporterSettings

configure_loguru_logging(
    settings=settings,
    exporter_settings=LogExporterSettings(
        enabled=True,
        endpoint='https://otel-collector.example',
        headers='api-key=secret',
        service_name='my-service',
    ),
)
```

When OTLP is enabled, both OpenTelemetry SDK logging and `logger.add` share the same resource. The helper also ensures the log level is kept in sync via `_map_loguru_level`. For stdlib-only instrumentation, call `configure_std_logging` directly and share the `LogExporterSettings`.

## Backend initialization

Services that implement application-specific backends should call `configure_loguru_logging` early so every component inherits the same sinks, OTLP exporter, and resource metadata. The `LogExporterSettings` instance can be reused by other helpers, keeping exporter configuration centralized:

```python
from nexor.logging import configure_loguru_logging, LogExporterSettings
from loguru import logger


def bootstrap_backend(settings) -> None:
    exporter_settings = LogExporterSettings(
        enabled=True,
        endpoint='https://otel-collector.example',
        headers='api-key=secret',
        service_name=settings.service_name,
        resource_attributes={'service.namespace': 'backend'},
    )

    configure_loguru_logging(settings=settings, exporter_settings=exporter_settings)
    logger.info('Backend ready, logs routed to Loguru sinks and OTLP')
```

Any background worker or HTTP handler can now call `logger.bind(component='worker')` to tag its entries, and the same `exporter_settings` can be passed to `configure_std_logging` if standard library loggers need the identical OTLP pipeline.

## API Reference

::: nexor.logging
