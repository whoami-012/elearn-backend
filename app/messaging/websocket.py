import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self, max_connections_per_user: int = 5) -> None:
        self.max_connections_per_user = max_connections_per_user
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._subscriptions: dict[WebSocket, set[UUID]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UUID, websocket: WebSocket) -> bool:
        async with self._lock:
            if len(self._connections[user_id]) >= self.max_connections_per_user:
                return False
            await websocket.accept()
            self._connections[user_id].add(websocket)
            return True

    async def subscribe(self, websocket: WebSocket, conversation_id: UUID) -> None:
        self._subscriptions[websocket].add(conversation_id)

    async def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                self._connections.pop(user_id, None)
            self._subscriptions.pop(websocket, None)

    async def send_to_users(self, user_ids: set[UUID], conversation_id: UUID, event: dict) -> None:
        stale: list[tuple[UUID, WebSocket]] = []
        for user_id in user_ids:
            for socket in tuple(self._connections.get(user_id, ())):
                if conversation_id not in self._subscriptions.get(socket, set()):
                    continue
                try:
                    await socket.send_json(event)
                except Exception:
                    stale.append((user_id, socket))
        for user_id, socket in stale:
            await self.disconnect(user_id, socket)


# This manager is the single-process adapter. Its interface is intentionally
# isolated so a Redis Pub/Sub broadcaster can fan events into send_to_users.
connection_manager = ConnectionManager()
