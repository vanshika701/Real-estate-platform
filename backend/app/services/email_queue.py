import asyncio

from redis import Redis as SyncRedis
from rq import Queue, Retry

from app.services.email import EmailMessage
from app.workers.email_jobs import send_email

# Back off between attempts so a brief provider outage doesn't burn all retries at once.
EMAIL_RETRY = Retry(max=3, interval=[10, 60, 300])


class EmailQueue:
    """Hands emails to the RQ worker so the request never waits on the email provider."""

    def __init__(self, connection: SyncRedis, queue_name: str) -> None:
        self.queue = Queue(queue_name, connection=connection)

    async def enqueue(self, message: EmailMessage) -> None:
        # RQ is synchronous; a thread keeps its Redis round trip off the event loop.
        await asyncio.to_thread(
            self.queue.enqueue, send_email, message.model_dump(), retry=EMAIL_RETRY
        )
