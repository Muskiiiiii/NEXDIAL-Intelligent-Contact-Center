from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from app.core.websocket_manager import ws_manager

logger = logging.getLogger("nexdial.ws")
router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "data": {"status": "CONNECTED", "protocol": "NEXDIAL_TELEMETRY_V1"}
        })
        while True:
            # Keep alive and receive any client-side commands or pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
        await ws_manager.disconnect(websocket)
