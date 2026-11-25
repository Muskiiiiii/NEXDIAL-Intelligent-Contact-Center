import json
import asyncio
from typing import List, Dict, Any
from fastapi import WebSocket
import logging

logger = logging.getLogger("nexdial.websocket")

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message_type: str, data: Any):
        """Broadcast message to all connected frontend clients."""
        payload = json.dumps({
            "type": message_type,
            "data": data,
        })
        async with self._lock:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.warning(f"Error sending to client, removing: {e}")
                    disconnected.append(connection)
            for conn in disconnected:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)

ws_manager = WebSocketManager()
