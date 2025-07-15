from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracer(app):
    resource = Resource(attributes={"service.name": "fastapi-backend"})

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    otlp_exporter = OTLPSpanExporter(endpoint="http://tempo:4318/v1/traces")
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)

    FastAPIInstrumentor.instrument_app(app)
