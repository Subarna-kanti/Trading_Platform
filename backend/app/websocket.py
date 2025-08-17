# app/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

router = APIRouter()


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
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You said: {data}", websocket)
            await manager.broadcast(f"Broadcast: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("A user has disconnected.")


# --- Helper functions ---
async def broadcast_wallet_update(
    user_id: int, balance: float, reserved_balance: float
):
    await manager.broadcast(
        f"Wallet Update | User {user_id}: Balance={balance}, Reserved={reserved_balance}"
    )


async def broadcast_trade_update(trade_id: int, price: float, quantity: float):
    await manager.broadcast(
        f"Trade Executed | Trade ID {trade_id}, Price={price}, Quantity={quantity}"
    )
