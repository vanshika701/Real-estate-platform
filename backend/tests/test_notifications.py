from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from httpx import AsyncClient, Response
from rq import Queue, SimpleWorker
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_booking_notifier
from app.core.config import get_settings
from app.core.redis import get_sync_redis, redis_client
from app.main import app
from app.models import Listing, User, UserRole
from app.services import email as email_module
from app.services.agent_events import AgentEventPublisher
from app.services.email import EmailMessage, ResendEmailSender
from app.services.notifications import BookingNotifier
from app.workers.email_jobs import send_email
from tests.factories import auth_headers, future_slot_start, make_listing, make_slot, make_user


@dataclass
class World:
    agent: User
    buyer: User
    listing: Listing
    slot_start: datetime


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    agent = await make_user(db_session, UserRole.AGENT)
    buyer = await make_user(db_session, UserRole.BUYER)
    listing = await make_listing(db_session, agent, title="Sea-facing 3 BHK in Worli")
    start = datetime(2030, 3, 14, 4, 30, tzinfo=UTC)  # 10:00 IST
    await make_slot(db_session, listing, start)
    return World(agent, buyer, listing, start)


@pytest.fixture
def email_queue() -> Queue:
    return Queue(get_settings().email_queue_name, connection=get_sync_redis())


async def hold_and_book(client: AsyncClient, w: World, note: str | None = None) -> Response:
    await client.post(
        f"/api/v1/listings/{w.listing.id}/slots/hold",
        json={"slot_start": w.slot_start.isoformat()},
        headers=auth_headers(w.buyer),
    )
    return await client.post(
        "/api/v1/bookings",
        json={"listing_id": w.listing.id, "slot_start": w.slot_start.isoformat(), "note": note},
        headers=auth_headers(w.buyer),
    )


def queued_messages(queue: Queue) -> list[EmailMessage]:
    return [EmailMessage.model_validate(job.args[0]) for job in queue.jobs]


# --- enqueueing -----------------------------------------------------------------------------


async def test_booking_queues_buyer_and_agent_emails(
    client: AsyncClient, world: World, email_queue: Queue
) -> None:
    response = await hold_and_book(client, world, note="Is parking available?")
    assert response.status_code == 201

    to_buyer, to_agent = queued_messages(email_queue)

    assert to_buyer.to == world.buyer.email
    assert to_buyer.subject == "Visit requested: Sea-facing 3 BHK in Worli"
    assert "Thursday, 14 March 2030 at 10:00 AM IST" in to_buyer.text
    assert to_agent.to == world.agent.email
    assert to_agent.subject == "New visit request: Sea-facing 3 BHK in Worli"
    assert world.buyer.email in to_agent.text
    assert "Is parking available?" in to_agent.text


async def test_jobs_are_queued_with_retries(
    client: AsyncClient, world: World, email_queue: Queue
) -> None:
    await hold_and_book(client, world)

    assert {job.retries_left for job in email_queue.jobs} == {3}


async def test_html_body_escapes_user_input(
    client: AsyncClient, world: World, email_queue: Queue
) -> None:
    await hold_and_book(client, world, note="<script>alert(1)</script>")

    _, to_agent = queued_messages(email_queue)

    assert "<script>" not in to_agent.html
    assert "&lt;script&gt;" in to_agent.html


async def test_booking_succeeds_even_if_email_queue_is_down(
    client: AsyncClient, world: World
) -> None:
    class BrokenQueue:
        async def enqueue(self, message: EmailMessage) -> None:
            raise ConnectionError("redis is down")

    app.dependency_overrides[get_booking_notifier] = lambda: BookingNotifier(
        BrokenQueue(),  # type: ignore[arg-type]
        AgentEventPublisher(redis_client),
    )

    response = await hold_and_book(client, world)

    assert response.status_code == 201


# --- the worker -----------------------------------------------------------------------------


async def test_worker_runs_queued_jobs_through_the_email_sender(
    client: AsyncClient,
    world: World,
    email_queue: Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[EmailMessage] = []

    class RecordingSender:
        def send(self, message: EmailMessage) -> None:
            sent.append(message)

    monkeypatch.setattr(email_module, "get_email_sender", lambda: RecordingSender())
    monkeypatch.setattr("app.workers.email_jobs.get_email_sender", lambda: RecordingSender())
    await hold_and_book(client, world)

    # SimpleWorker runs jobs in-process (no fork), the same code path as the real worker.
    SimpleWorker([email_queue], connection=email_queue.connection).work(burst=True)

    assert sorted(m.to for m in sent) == sorted([world.buyer.email, world.agent.email])
    assert email_queue.count == 0


def test_console_sender_is_used_without_resend_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "resend_api_key", None)

    assert isinstance(email_module.get_email_sender(), email_module.ConsoleEmailSender)
    # And the job runs end to end without network access.
    send_email({"to": "a@b.com", "subject": "Hi", "text": "Hello", "html": "<p>Hello</p>"})


# --- Resend ---------------------------------------------------------------------------------


def _resend(handler: Any) -> ResendEmailSender:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ResendEmailSender("re_test_key", "PropVisit <noreply@propvisit.dev>", client)


MESSAGE = EmailMessage(to="riya@example.com", subject="Hi", text="Hello", html="<p>Hello</p>")


def test_resend_sender_posts_the_message() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "email_123"})

    _resend(handler).send(MESSAGE)

    (request,) = requests
    assert str(request.url) == "https://api.resend.com/emails"
    assert request.headers["Authorization"] == "Bearer re_test_key"
    body = httpx.Response(200, content=request.content).json()
    assert body["to"] == ["riya@example.com"]
    assert body["from"] == "PropVisit <noreply@propvisit.dev>"


def test_resend_failure_raises_so_rq_retries() -> None:
    sender = _resend(lambda request: httpx.Response(503, json={"message": "busy"}))

    with pytest.raises(httpx.HTTPStatusError):
        sender.send(MESSAGE)


async def test_future_slot_helper_is_used(db_session: AsyncSession) -> None:
    # Guard: the fixture above uses a fixed 2030 date; make sure it's still in the future.
    assert future_slot_start() < datetime(2030, 3, 14, tzinfo=UTC)
