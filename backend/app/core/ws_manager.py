# app/core/ws_manager.py
from fastapi import WebSocket
from typing import Dict, List
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.global_connections: List[WebSocket] = []
        asyncio.create_task(self._ping_clients())

    async def connect(self, websocket: WebSocket, user_id: int = None):
        await websocket.accept()
        if user_id:
            self.active_connections.setdefault(user_id, []).append(websocket)
        self.global_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int = None):
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws != websocket
            ]
        self.global_connections = [
            ws for ws in self.global_connections if ws != websocket
        ]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception:
            pass

    async def send_user_message(self, user_id: int, message: str):
        for ws in self.active_connections.get(user_id, []):
            try:
                await ws.send_text(message)
            except Exception:
                pass

    async def broadcast(self, message: str):
        for ws in self.global_connections:
            try:
                await ws.send_text(message)
            except Exception:
                pass

    async def _ping_clients(self):
        while True:
            await asyncio.sleep(25)
            for ws in self.global_connections:
                try:
                    await ws.send_text("ping")
                except Exception:
                    pass

manager = ConnectionManager()
