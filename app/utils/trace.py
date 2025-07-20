from opentelemetry.trace import get_current_span


def _trace_attrs() -> dict[str, str]:
    span = get_current_span()
    ctx = span.get_span_context()
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
    }
