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
    """
    Builds a resource object by utilizing provided service details and additional
    metadata. This function is a wrapper around `_build_resource` to streamline
    the creation of the resource object.

    Args:
        service_name (str): The name of the service for which the resource is
            being built.
        service_namespace (Optional[str]): An optional namespace for the service,
            typically representing the group or organization the service belongs to.
        deployment_environment (Optional[str]): An optional deployment environment
            name, such as "production", "staging", or "development".
        extra (Optional[Mapping[str, str]]): Optional additional metadata provided
            as key-value pairs for the resource.

    Returns:
        Resource: The constructed resource object.
    """
    return _build_resource(
        service_name=service_name,
        service_namespace=service_namespace,
        deployment_environment=deployment_environment,
        extra=extra,
    )


def parse_otlp_headers(raw_headers: str | None) -> Dict[str, str]:
    """
    Parses a string of headers into a dictionary format.

    This function takes a string of comma-separated key-value pairs representing
    headers and parses them into a dictionary. Each key-value pair should be
    separated by an equals sign (`=`). If the input is `None` or improperly
    formatted, an empty dictionary is returned.

    Args:
        raw_headers: A string of comma-separated key-value pairs representing
            headers, where each pair is in the format `key=value`. Can also be
            `None`.

    Returns:
        A dictionary where the keys are the header names and the values are the
        corresponding header values. If `raw_headers` is `None` or improperly
        formatted, returns an empty dictionary.
    """
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
    """
    Initializes observability resources required for monitoring and reporting.

    This function creates and configures the necessary resources to enable observability
    for a given service. It helps ensure that required providers for tracing and metrics
    are properly set up.

    Args:
        service_name: The name of the service to be monitored.
        service_namespace: The namespace of the service, used for categorization and
            grouping of related services. Defaults to None.
        deployment_environment: The environment in which the service is deployed, such
            as "production" or "staging". Defaults to None.
        extra: Additional metadata or key-value pairs to enrich the observability
            resource. Defaults to None.
    """
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
    """
    Initializes OpenTelemetry observability for a FastAPI application.

    This function configures OpenTelemetry instrumentation for the provided FastAPI
    instance. It initializes the service observability with the given service name,
    optional service namespace, deployment environment, and additional attributes.
    If the FastAPIInstrumentor is available, the function ensures that the app is
    instrumented by uninstrumenting any existing instrumentation first and then
    reapplying it.

    Args:
        app: The FastAPI application instance to be instrumented.
        service_name: The name of the service, utilized for observability.
        service_namespace: The namespace of the service, useful for logical grouping.
            Defaults to None.
        deployment_environment: The environment in which the service is deployed
            (e.g., production, staging). Defaults to None.
        extra: A mapping of additional attributes to supplement observability
            data. Defaults to None.
    """
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
    """
    Initializes OpenTelemetry worker for setting up observability features.

    This function provides an interface for initializing observability
    capabilities using OpenTelemetry by configuring telemetry data
    with specified service details and environmental context. It ensures
    that service-related metrics, traces, or logs can be collected
    appropriately.

    Args:
        service_name (str): The unique name of the service for which
            observability is being set up.
        service_namespace (Optional[str]): The namespace in which the
            service resides, typically used for organizing services in larger
            environments. Defaults to None.
        deployment_environment (Optional[str]): Specifies the environment
            where the deployment occurs (e.g., 'production', 'staging').
            Defaults to None.
        extra (Optional[Mapping[str, str]]): Additional metadata or parameters
            to be attached to the telemetry data. Defaults to None.
    """
    init_observability(
        service_name=service_name,
        service_namespace=service_namespace,
        deployment_environment=deployment_environment,
        extra=extra,
    )


def get_tracer(name: str):
    """
    Retrieves a tracer by its specified name. Tracers are used for capturing
    telemetry data such as spans, events, and context for distributed tracing.

    This function enables interaction with the tracing framework, allowing
    developers to track operation flows and measure performance characteristics
    of their systems.

    Args:
        name (str): The name of the tracer to retrieve.

    Returns:
        Tracer: An instance of the requested tracer.
    """
    return trace.get_tracer(name)
