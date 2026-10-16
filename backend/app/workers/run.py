"""Entry point for the background worker: python -m app.workers.run"""

from rq import Queue, Worker
from rq.defaults import DEFAULT_LOGGING_DATE_FORMAT, DEFAULT_LOGGING_FORMAT
from rq.scheduler import RQScheduler

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.redis import get_sync_redis


class PacedWorker(Worker):
    """An RQ worker whose scheduler polls Redis at a configurable interval.

    RQ hardcodes the scheduler's 1-second poll inside `_start_scheduler`, so this override
    mirrors that method (rq is pinned in requirements.txt) and only adds `interval`.
    """

    def _start_scheduler(
        self,
        burst: bool = False,
        logging_level: str | None = "INFO",
        date_format: str = DEFAULT_LOGGING_DATE_FORMAT,
        log_format: str = DEFAULT_LOGGING_FORMAT,
    ) -> None:
        self.scheduler = RQScheduler(
            self.queues,
            connection=self.connection,
            interval=get_settings().rq_scheduler_interval_seconds,
            logging_level=logging_level if logging_level is not None else self.log.level,
            date_format=date_format,
            log_format=log_format,
            serializer=self.serializer,
        )
        self.scheduler.acquire_locks()
        if not self.scheduler.acquired_locks:
            return  # another worker's scheduler holds the lock
        if burst:
            try:
                self.scheduler.register_birth()
                self.scheduler.enqueue_scheduled_jobs()
            finally:
                self.scheduler.release_locks()
                self.scheduler.register_death()
        else:
            self.scheduler.start()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.app_env == "production")
    connection = get_sync_redis()
    worker = PacedWorker(
        [Queue(settings.email_queue_name, connection=connection)], connection=connection
    )
    # The scheduler is what re-runs failed jobs after their retry interval.
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
