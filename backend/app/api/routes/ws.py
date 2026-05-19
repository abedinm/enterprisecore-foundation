"""
WebSocket endpoint for real-time notifications.

Clients connect with `?token=<access_token>` because WebSockets in browsers
can't easily set custom headers. The token is validated exactly like a
normal HTTP request — we don't trust the connection until the token decodes
and resolves to an active user.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import decode_token
from app.core.ws_manager import manager
from app.models.user import User


router = APIRouter()


@router.websocket("/notifications")
async def notifications_ws(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Authenticated WebSocket. Closes with 4401 on bad credentials."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4401)
        return
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        await websocket.close(code=4401)
        return

    user = db.get(User, user_id)
    if not user or not user.is_active:
        await websocket.close(code=4401)
        return

    await manager.connect(user_id, websocket)
    try:
        # Send a hello so the client can confirm the connection.
        await websocket.send_json({"kind": "hello", "user_id": user_id})
        while True:
            # We don't expect inbound traffic — just keep the connection open
            # and respond to client-side pings with a pong.
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception:
        manager.disconnect(user_id, websocket)
