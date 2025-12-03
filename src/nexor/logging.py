from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

from loguru import logger

from nexor.observability import build_resource, parse_otlp_headers

if TYPE_CHECKING:
    from opentelemetry.sdk.resources import Resource

_configured_loguru = False
_loguru_forward_added = False
_configured_stdlib = False


def _map_loguru_level(level_name: str) -> int:
    mapping = {
        'TRACE': logging.DEBUG,
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'SUCCESS': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return mapping.get(level_name.upper(), logging.INFO)


@dataclass(frozen=True)
class LogExporterSettings:
    enabled: bool = False
    endpoint: str | None = None
    headers: str | None = None
    service_name: str | None = None
    service_namespace: str | None = None
    deployment_environment: str | None = None
    resource_extra: Mapping[str, str] | None = None
    resource: 'Resource' | None = None


def _bridge_loguru_to_stdlib(level_name: str) -> None:
    global _loguru_forward_added
    if _loguru_forward_added:
        return

    level_map: Mapping[str, int] = {
        'TRACE': logging.DEBUG,
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'SUCCESS': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }

    def _forward_to_stdlog(message):
        record = message.record
        lvl = level_map.get(record['level'].name, logging.INFO)
        extra = record.get('extra', {})
        logging.getLogger(record['name']).log(lvl, record['message'], extra=extra)

    logger.add(
        _forward_to_stdlog,
        level=level_name,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )
    _loguru_forward_added = True


def _configure_otlp_loguru(settings: object, *, exporter_settings: LogExporterSettings) -> None:
    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    except Exception:  # pragma: no cover - optional dependency
        return

    resource = (
        exporter_settings.resource
        if exporter_settings.resource is not None
        else build_resource(
            service_name=exporter_settings.service_name or getattr(settings, 'app_name', 'service'),
            service_namespace=exporter_settings.service_namespace,
            deployment_environment=exporter_settings.deployment_environment,
            extra=exporter_settings.resource_extra,
        )
    )

    provider = LoggerProvider(resource=resource)  # type: ignore[arg-type]
    exporter = (
        OTLPLogExporter(
            endpoint=exporter_settings.endpoint,
            headers=parse_otlp_headers(exporter_settings.headers),
        )
        if exporter_settings.endpoint or exporter_settings.headers
        else OTLPLogExporter()
    )
    processor = BatchLogRecordProcessor(exporter)
    provider.add_log_record_processor(processor)
    set_logger_provider(provider)

    std_logging_handler = LoggingHandler(level=logging.NOTSET)
    root_logger = logging.getLogger()
    if not any(isinstance(handler, type(std_logging_handler)) for handler in root_logger.handlers):
        root_logger.addHandler(std_logging_handler)
    root_logger.setLevel(_map_loguru_level(getattr(settings, 'log_level', 'INFO')))

    _bridge_loguru_to_stdlib(getattr(settings, 'log_level', 'INFO'))


def configure_loguru_logging(
    *,
    settings: object,
    exporter_settings: LogExporterSettings | None = None,
) -> None:
    """Initialise Loguru logging with optional OTLP forwarding."""
    global _configured_loguru
    if _configured_loguru:
        return

    if getattr(settings, 'log_remove_default_sink', True):
        logger.remove()

    logger.add(
        sys.stderr,
        level=getattr(settings, 'log_level', 'INFO'),
        enqueue=getattr(settings, 'log_enqueue', True),
        backtrace=getattr(settings, 'log_backtrace', True),
        diagnose=getattr(settings, 'log_diagnose', False),
        serialize=not getattr(settings, 'log_console_plain', True),
        format='<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
        '<level>{level: <8}</level> | '
        '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
        '<level>{message}</level>',
    )

    if exporter_settings and exporter_settings.enabled:
        _configure_otlp_loguru(settings=settings, exporter_settings=exporter_settings)

    _configured_loguru = True


def _configure_otlp_stdlib(
    *, exporter_settings: LogExporterSettings, level: int, root_logger: logging.Logger, settings: object
) -> None:
    try:
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    except ImportError:  # pragma: no cover - optional dependency
        root_logger.warning('OpenTelemetry logging SDK modules not available; skipping OTLP log forwarding.')
        return

    try:
        resource = (
            exporter_settings.resource
            if exporter_settings.resource is not None
            else build_resource(
                service_name=exporter_settings.service_name or getattr(settings, 'app_name', 'service'),
                service_namespace=exporter_settings.service_namespace,
                deployment_environment=exporter_settings.deployment_environment,
                extra=exporter_settings.resource_extra,
            )
        )
    except RuntimeError:
        root_logger.warning('OpenTelemetry SDK not available; skipping OTLP log forwarding.')
        return

    exporter = (
        OTLPLogExporter(
            endpoint=exporter_settings.endpoint,
            headers=parse_otlp_headers(exporter_settings.headers),
        )
        if exporter_settings.endpoint or exporter_settings.headers
        else OTLPLogExporter()
    )
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    otel_handler = LoggingHandler(level=level, logger_provider=provider)
    otel_handler.setLevel(level)
    root_logger.addHandler(otel_handler)


def configure_std_logging(
    *,
    settings: object,
    formatter: str = '%(asctime)s %(levelname)s [%(name)s] %(message)s',
    exporter_settings: LogExporterSettings | None = None,
) -> None:
    """Initialise the standard library logger with optional OTLP forwarding."""
    global _configured_stdlib
    if _configured_stdlib:
        return

    root_logger = logging.getLogger()

    level_name = getattr(settings, 'log_level', 'INFO')
    level = getattr(logging, level_name.upper(), logging.INFO)

    if not root_logger.handlers:
        logging.basicConfig(level=level, format=formatter)
    root_logger.setLevel(level)

    if exporter_settings and exporter_settings.enabled:
        _configure_otlp_stdlib(
            exporter_settings=exporter_settings,
            level=level,
            root_logger=root_logger,
            settings=settings,
        )

    _configured_stdlib = True
