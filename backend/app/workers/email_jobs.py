"""RQ job functions. They run in the worker process, not the API.

Jobs receive the fully rendered email rather than a booking ID: the worker never touches the
database, and the email describes the booking as it was when it was made.
"""

from typing import Any

from app.services.email import EmailMessage, get_email_sender


def send_email(message: dict[str, Any]) -> None:
    get_email_sender().send(EmailMessage.model_validate(message))
