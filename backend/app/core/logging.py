import logging

import structlog
from pythonjsonlogger import jsonlogger

LOG_FILE = "/var/log/fastapi/app.log"  # or local path "./logs/app.log"


def configure_logging():
    # Stream (console) handler
    stream_handler = logging.StreamHandler()
    stream_formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    stream_handler.setFormatter(stream_formatter)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(stream_formatter)

    # Set up root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(stream_handler)
    root.addHandler(file_handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
