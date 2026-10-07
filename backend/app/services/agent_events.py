"""Real-time events for agents, delivered over WebSocket via Redis pub/sub.

Publishing goes through Redis rather than an in-memory registry of sockets, so an event
reaches the agent no matter which backend instance (or worker) produced it and which
instance holds the agent's socket.
"""

import asyncio
import contextlib
import json
import time
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.core.security import TokenType, decode_token
from app.models import User, UserRole
from app.repositories.users import UserRepository

logger = structlog.get_logger(__name__)

# Idle sockets get a ping this often, so proxies with idle timeouts don't drop them.
PING_INTERVAL_SECONDS = 25.0

# Close codes in the 4000-4999 range are for applications; these mirror HTTP 401/403.
CLOSE_UNAUTHORIZED = 4401
CLOSE_FORBIDDEN = 4403


def agent_channel(agent_id: int) -> str:
    return f"agent_events:{agent_id}"


class AgentEventPublisher:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish(self, agent_id: int, event_type: str, data: dict[str, Any]) -> None:
        await self.redis.publish(
            agent_channel(agent_id), json.dumps({"type": event_type, **data}, default=str)
        )


async def authenticate_agent(token: str | None) -> tuple[User | None, int]:
    """Return (agent, 0) on success, or (None, close_code)."""
    if not token:
        return None, CLOSE_UNAUTHORIZED
    try:
        payload = decode_token(token, TokenType.ACCESS)
    except AppError:
        return None, CLOSE_UNAUTHORIZED

    # A short-lived session just for this lookup. A request-scoped dependency would hold a
    # pooled DB connection for as long as the socket stays open, which could be hours.
    async with SessionLocal() as session:
        user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        return None, CLOSE_UNAUTHORIZED
    if user.role is not UserRole.AGENT:
        return None, CLOSE_FORBIDDEN
    return user, 0


async def stream_agent_events(websocket: WebSocket, redis: Redis, agent_id: int) -> None:
    """Forward this agent's events to the socket until the client disconnects."""
    pubsub = redis.pubsub()
    await pubsub.subscribe(agent_channel(agent_id))

    async def forward_events() -> None:
        last_sent = time.monotonic()
        while True:
            # None means "nothing yet", or a subscribe confirmation that was skipped; so the
            # ping is driven by elapsed time, not by get_message returning None.
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message is not None:
                await websocket.send_text(message["data"])
                last_sent = time.monotonic()
            elif time.monotonic() - last_sent >= PING_INTERVAL_SECONDS:
                await websocket.send_json({"type": "ping"})
                last_sent = time.monotonic()

    async def wait_for_disconnect() -> None:
        # Agents don't send anything; reading is just how we notice the socket closing.
        with contextlib.suppress(WebSocketDisconnect):
            while True:
                await websocket.receive_text()

    tasks = [asyncio.create_task(forward_events()), asyncio.create_task(wait_for_disconnect())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            exc = None if task.cancelled() else task.exception()
            if exc is not None and not isinstance(exc, WebSocketDisconnect):
                logger.warning("agent_socket_error", agent_id=agent_id, error=str(exc))
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await pubsub.unsubscribe()
        await pubsub.aclose()
