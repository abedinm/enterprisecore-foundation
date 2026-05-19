"""
Simple in-process WebSocket connection manager for live notifications.

Each authenticated client opens a WebSocket on /ws/notifications.
We track {user_id: set[WebSocket]} so a user with multiple tabs gets
notifications on every tab. When `push_to_user` is called from any
synchronous route handler, it fans out to all that user's open sockets.

Caveats:
- In-process only. For multi-worker / multi-server deployments, swap this
  out for Redis Pub/Sub or similar.
- We `asyncio.run_coroutine_threadsafe` because routes are sync but
  WebSocket sends are async. The main FastAPI event loop is captured on
  app startup.
"""

import asyncio
from typing import Any, Dict, Set, Optional
from fastapi import WebSocket


class WSManager:
    def __init__(self) -> None:
        self._conns: Dict[int, Set[WebSocket]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once during app startup to capture the running event loop."""
        self._loop = loop

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._conns.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        conns = self._conns.get(user_id)
        if conns and ws in conns:
            conns.discard(ws)
            if not conns:
                self._conns.pop(user_id, None)

    async def _send_to_user(self, user_id: int, payload: Any) -> None:
        conns = list(self._conns.get(user_id, set()))
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    def push_to_user(self, user_id: int, payload: Any) -> None:
        """Fire-and-forget from a sync context. Safe if no loop bound yet."""
        if self._loop is None or not self._conns.get(user_id):
            return
        asyncio.run_coroutine_threadsafe(self._send_to_user(user_id, payload), self._loop)


# Module-level singleton — every helper calls this same instance.
manager = WSManager()
