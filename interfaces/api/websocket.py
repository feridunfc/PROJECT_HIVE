"""
WebSocket support for real-time task updates.
"""
import json
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from core.queue import task_queue
from core.telemetry.metrics import metrics


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        """Disconnect WebSocket."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """Send message to specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(client_id)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected_clients.append(client_id)

        for client_id in disconnected_clients:
            self.disconnect(client_id)


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, task_id: str = None):
    """
    WebSocket endpoint for real-time task updates.

    Args:
        websocket: WebSocket connection
        task_id: Optional specific task ID to monitor
    """
    client_id = f"client_{id(websocket)}"

    await manager.connect(websocket, client_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "task_id": task_id
        })

        if task_id:
            # Monitor specific task
            last_status = None
            while True:
                task = task_queue.get_task(task_id)
                if task:
                    current_status = task.status.value
                    if current_status != last_status:
                        await websocket.send_json({
                            "type": "task_update",
                            "task_id": task_id,
                            "status": current_status,
                            "progress": "running" if task.status.value == "running" else "done",
                            "timestamp": task.completed_at.isoformat() if task.completed_at else None
                        })
                        last_status = current_status

                # Check if task is completed or failed
                if task and task.status.value in ["completed", "failed", "cancelled"]:
                    await websocket.send_json({
                        "type": "task_completed",
                        "task_id": task_id,
                        "status": task.status.value,
                        "result": task.result,
                        "error": task.error
                    })
                    break

                # Sleep to prevent busy waiting
                import asyncio
                await asyncio.sleep(1)

        else:
            # General updates
            while True:
                # Send queue stats periodically
                stats = task_queue.get_stats()
                await websocket.send_json({
                    "type": "queue_stats",
                    "stats": stats,
                    "timestamp": datetime.now().isoformat()
                })

                import asyncio
                await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)