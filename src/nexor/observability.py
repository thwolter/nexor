from __future__ import annotations

import os
import socket
from typing import Dict, Mapping, Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

try:  # pragma: no cover - optional instrumentation dependency
    from opentelemetry.instrumentation.fastapi import (
        FastAPIInstrumentor,  # type: ignore
    )
except Exception:
    FastAPIInstrumentor = None  # type: ignore

_PROVIDER_INITIALISED = False
_METRICS_INITIALISED = False


def _build_resource(
    *,
    service_name: str,
    service_namespace: Optional[str] = None,
    deployment_environment: Optional[str] = None,
    extra: Optional[Mapping[str, str]] = None,
) -> Resource:
    attrs: Dict[str, str] = {
        'service.name': service_name,
        'service.namespace': service_namespace or os.getenv('SERVICE_NAMESPACE', 'finrag'),
        'deployment.environment': deployment_environment or os.getenv('DEPLOYMENT_ENV', 'development'),
        'service.instance.id': os.getenv('SERVICE_INSTANCE_ID', f'{socket.gethostname()}:{os.getpid()}'),
    }
    if extra:
        attrs.update(extra)
    return Resource.create(attrs)


def build_resource(
    *,
    service_name: str,
    service_namespace: Optional[str] = None,
    deployment_environment: Optional[str] = None,
    extra: Optional[Mapping[str, str]] = None,
) -> Resource:
    """Create an OpenTelemetry Resource for tracing and logging."""
    return _build_resource(
        service_name=service_name,
        service_namespace=service_namespace,
        deployment_environment=deployment_environment,
        extra=extra,
    )


def parse_otlp_headers(raw_headers: str | None) -> Dict[str, str]:
    if not raw_headers:
        return {}
    headers: Dict[str, str] = {}
    for pair in raw_headers.split(','):
        item = pair.strip()
        if not item or '=' not in item:
            continue
        key, value = item.split('=', 1)
        headers[key.strip()] = value.strip()
    return headers


def _ensure_provider(resource: Resource) -> TracerProvider:
    global _PROVIDER_INITIALISED
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider) or not _PROVIDER_INITIALISED:
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        _PROVIDER_INITIALISED = True
    return provider


def _ensure_metrics_provider(resource: Resource) -> MeterProvider:
    global _METRICS_INITIALISED
    provider = metrics.get_meter_provider()
    if not isinstance(provider, MeterProvider) or not _METRICS_INITIALISED:
        reader = PeriodicExportingMetricReader(OTLPMetricExporter())
        provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(provider)
        _METRICS_INITIALISED = True
    return provider


def init_observability(
    *,
    service_name: str,
    service_namespace: Optional[str] = None,
    deployment_environment: Optional[str] = None,
    extra: Optional[Mapping[str, str]] = None,
) -> None:
    """Initialise OpenTelemetry providers for tracing and metrics."""
    resource = build_resource(
        service_name=service_name,
        service_namespace=service_namespace,
        deployment_environment=deployment_environment,
        extra=extra,
    )
    _ensure_provider(resource)
    _ensure_metrics_provider(resource)


def init_otel_fastapi(
    app,
    *,
    service_name: str,
    service_namespace: Optional[str] = None,
    deployment_environment: Optional[str] = None,
    extra: Optional[Mapping[str, str]] = None,
) -> None:
    """Initialise FastAPI instrumentation with OpenTelemetry exporters."""
    init_observability(
        service_name=service_name,
        service_namespace=service_namespace,
        deployment_environment=deployment_environment,
        extra=extra,
    )

    if FastAPIInstrumentor is not None:
        try:
            if hasattr(FastAPIInstrumentor, 'uninstrument_app'):
                FastAPIInstrumentor.uninstrument_app(app)  # type: ignore[attr-defined]
        except Exception:
            pass
        if hasattr(FastAPIInstrumentor, 'instrument_app'):
            FastAPIInstrumentor.instrument_app(app)  # type: ignore[attr-defined]


def init_otel_worker(
    *,
    service_name: str,
    service_namespace: Optional[str] = None,
    deployment_environment: Optional[str] = None,
    extra: Optional[Mapping[str, str]] = None,
) -> None:
    """Initialise OpenTelemetry on worker processes."""
    init_observability(
        service_name=service_name,
        service_namespace=service_namespace,
        deployment_environment=deployment_environment,
        extra=extra,
    )


def get_tracer(name: str):
    return trace.get_tracer(name)
