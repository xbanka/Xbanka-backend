import asyncio
import logging
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class GlobalConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


class RoomConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, Set[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        self.active_connections[room_id].discard(websocket)
        #  clean up empty room
        if not self.active_connections[room_id]:
            del self.active_connections[room_id]

    async def broadcast(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_json(message)


class NotificationConnectionManager:
    """Per-ERP-user websocket connections, keyed by user id, so notification
    events can be pushed to one recipient without touching RoomConnectionManager."""

    def __init__(self):
        self.active_connections: dict[str, Set[WebSocket]] = {}
        self.loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Record the running event loop, so sync request handlers (which run
        in FastAPI's threadpool) can schedule broadcasts onto it."""
        self.loop = loop

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        connections = self.active_connections.get(user_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        for connection in list(self.active_connections.get(user_id, ())):
            try:
                await connection.send_json(message)
            except Exception:
                logger.info("Dropping dead notification socket for user %s", user_id, exc_info=True)
                self.disconnect(user_id, connection)

    def send_to_user_threadsafe(self, user_id: str, message: dict) -> None:
        """Schedule a push from sync code running off the event loop thread
        (e.g. a plain `def` FastAPI route handler in the threadpool)."""
        if self.loop is None or user_id not in self.active_connections:
            return
        
        asyncio.run_coroutine_threadsafe(
            self.send_to_user(user_id, message), 
            self.loop
        )


global_manager = GlobalConnectionManager()
room_manager = RoomConnectionManager()
notification_manager = NotificationConnectionManager()
