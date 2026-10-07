from fastapi import APIRouter, WebSocket

from app.core.redis import redis_client
from app.services.agent_events import authenticate_agent, stream_agent_events

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/agent")
async def agent_events(websocket: WebSocket, token: str | None = None) -> None:
    """Live booking events for the authenticated agent.

    The access token goes in the query string because browsers can't set headers on a
    WebSocket handshake. Events: booking.created, booking.cancelled (plus periodic pings).
    """
    # Accept first so the client receives our close code; closing before accept is reported
    # to the browser as a generic handshake failure.
    await websocket.accept()
    agent, close_code = await authenticate_agent(token)
    if agent is None:
        await websocket.close(code=close_code)
        return
    await stream_agent_events(websocket, redis_client, agent.id)
