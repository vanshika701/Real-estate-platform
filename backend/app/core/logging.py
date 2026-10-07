import logging
import sys

import structlog


def configure_logging(level: str, json_logs: bool) -> None:
    """Route both structlog and stdlib logging (uvicorn, sqlalchemy) through one formatter.

    JSON in production so logs are machine-parseable; pretty console output in development.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Uvicorn installs its own handlers; drop them so its logs propagate to our formatter.
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers = []
    uvicorn_logger.propagate = True

    # Our request middleware logs each request, so uvicorn's access log would be a duplicate.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
