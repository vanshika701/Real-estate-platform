"""Entry point for the background worker: python -m app.workers.run"""

from rq import Queue, Worker

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.redis import get_sync_redis


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.app_env == "production")
    connection = get_sync_redis()
    worker = Worker(
        [Queue(settings.email_queue_name, connection=connection)], connection=connection
    )
    # The scheduler is what re-runs failed jobs after their retry interval.
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
