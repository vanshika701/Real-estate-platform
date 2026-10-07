"""Sending email: Resend when an API key is configured, the console otherwise.

These run inside the RQ worker, which is synchronous, so the senders are synchronous too.
"""

from typing import Protocol

import httpx
import structlog
from pydantic import BaseModel, EmailStr

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

RESEND_URL = "https://api.resend.com/emails"


class EmailMessage(BaseModel):
    to: EmailStr
    subject: str
    text: str
    html: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailSender:
    """Development fallback: the email is logged instead of sent."""

    def send(self, message: EmailMessage) -> None:
        logger.info("email_logged", to=message.to, subject=message.subject, body=message.text)


class ResendEmailSender:
    def __init__(self, api_key: str, sender: str, client: httpx.Client | None = None) -> None:
        self.api_key = api_key
        self.sender = sender
        self.client = client or httpx.Client(timeout=10)

    def send(self, message: EmailMessage) -> None:
        response = self.client.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "from": self.sender,
                "to": [message.to],
                "subject": message.subject,
                "text": message.text,
                "html": message.html,
            },
        )
        # Raising lets RQ retry: Resend rate limits and 5xx errors are usually transient.
        response.raise_for_status()
        logger.info("email_sent", to=message.to, subject=message.subject)


def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.resend_api_key:
        return ResendEmailSender(settings.resend_api_key, settings.email_from)
    return ConsoleEmailSender()
