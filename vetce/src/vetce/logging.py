import logging
import structlog
from vetce.config import settings

def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=settings.log_level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),  # swap to JSONRenderer in prod
        ],
    )

log = structlog.get_logger()