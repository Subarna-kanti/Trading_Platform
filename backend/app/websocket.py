# app/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

router = APIRouter()


# --- Connection Manager for broadcasting ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message only to this client (echo)."""
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """Send message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


# --- WebSocket endpoint ---
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive incoming client messages
            data = await websocket.receive_text()
            # Echo back to sender
            await manager.send_personal_message(f"You said: {data}", websocket)
            # Broadcast to all clients
            await manager.broadcast(f"Broadcast: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("A user has disconnected.")


# --- Helper functions for broadcasting updates ---
async def broadcast_wallet_update(user_id: int, balance: float):
    """Notify all clients about a wallet balance update."""
    await manager.broadcast(f"Wallet Update | User {user_id}: Balance = {balance}")


async def broadcast_trade_update(trade_id: int, price: float, quantity: float):
    """Notify all clients about a new trade execution."""
    await manager.broadcast(
        f"Trade Executed | Trade ID {trade_id}, Price: {price}, Quantity: {quantity}"
    )
