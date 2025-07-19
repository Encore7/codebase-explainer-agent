# backend/app/ultils/telemetry.py

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider

from backend.app.core.config import settings


def setup_otel(service_name: str):
    resource = Resource(attributes={"service.name": service_name})

    # Tracing
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    span_exporter = OTLPSpanExporter(endpoint=settings.OTLP_TRACES_URL, timeout=5)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))

    # Metrics
    metric_exporter = OTLPMetricExporter(endpoint=settings.OTLP_METRICS_URL, timeout=5)
    metric_reader = PeriodicExportingMetricReader(metric_exporter)

    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    set_meter_provider(meter_provider)

    # Logging
    log_exporter = OTLPLogExporter(endpoint=settings.OTLP_LOGS_URL, timeout=5)
    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(log_provider)

    # Auto-instrument stdlib logging
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Optional: Auto-instrument external libs
    RequestsInstrumentor().instrument()
