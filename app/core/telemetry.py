import logging
import sys
from typing import Annotated, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings

# Declare resource once for all providers
resource = Resource(attributes={"service.name": settings.PROJECT_NAME})

# Base stdout logging (fallback for local dev/debug)
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - Line %(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# LOGGING
try:
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=f"{settings.OTLP_ENDPOINT}/v1/logs",
                headers={"Authorization": f"Basic {settings.OTLP_TOKEN}"},
            )
        )
    )
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
except Exception as e:
    raise SystemExit(f"[OTel Logging Init Failure] {e}")

# TRACING
try:
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{settings.OTLP_ENDPOINT}/v1/traces",
                headers={"Authorization": f"Basic {settings.OTLP_TOKEN}"},
            )
        )
    )
    trace.set_tracer_provider(tracer_provider)
except Exception as e:
    raise SystemExit(f"[OTel Tracing Init Failure] {e}")

# METRICS
try:
    metric_exporter = OTLPMetricExporter(
        endpoint=f"{settings.OTLP_ENDPOINT}/v1/metrics",
        headers={"Authorization": f"Basic {settings.OTLP_TOKEN}"},
    )
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    set_meter_provider(meter_provider)
except Exception as e:
    raise SystemExit(f"[OTel Metrics Init Failure] {e}")

# Instrument External Libraries
LoggingInstrumentor().instrument(set_logging_format=True)
RequestsInstrumentor().instrument()


# Logger Getter Function
def get_logger(
    module_name: Optional[str] = None,
) -> Annotated[logging.Logger, "Logger instance for the specified module"]:
    if not module_name:
        module_name = __name__
    logger = logging.getLogger(module_name)
    if handler and not any(isinstance(h, LoggingHandler) for h in logger.handlers):
        logger.addHandler(handler)
    return logger


# FastAPI Instrumentation Wrapper
def instrument_fastapi(app):
    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception as e:
        raise SystemExit(f"[FastAPI Instrumentation Failure] {e}")
