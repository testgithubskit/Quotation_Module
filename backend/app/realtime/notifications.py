from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import WebSocket


class NotificationHub:
    """In-process fan-out of notification events to connected users."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def register(self, user_id: UUID, websocket: WebSocket) -> None:
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    def publish(self, user_ids: list[UUID]) -> None:
        """Schedule a push from sync request handlers onto the server event loop."""
        ids = list(dict.fromkeys(user_ids))
        loop = self._loop
        if not ids or loop is None or not loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(ids), loop)

    async def _broadcast(self, user_ids: list[UUID]) -> None:
        payload = json.dumps({"type": "notifications"})
        for user_id in user_ids:
            dead: list[WebSocket] = []
            for websocket in list(self._connections.get(user_id, ())):
                try:
                    await websocket.send_text(payload)
                except Exception:
                    dead.append(websocket)
            for websocket in dead:
                self.disconnect(user_id, websocket)


notification_hub = NotificationHub()
