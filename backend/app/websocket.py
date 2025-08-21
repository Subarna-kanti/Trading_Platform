import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List
from jose import jwt, JWTError
from app.core.config import settings
from app.core.broadcasts import get_order_book_snapshot, get_trade_snapshot
from app.db.session import get_db
from app.db.data_model import User

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.global_connections: List[WebSocket] = []

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

    async def ping_clients(self):
        """Send ping to all clients every 25 seconds."""
        while True:
            await asyncio.sleep(25)
            for ws in self.global_connections:
                try:
                    await ws.send_text("ping")
                except Exception:
                    pass


manager = ConnectionManager()
asyncio.create_task(manager.ping_clients())


async def verify_token_ws(token: str):
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("username")
        if not username:
            return None
    except JWTError:
        return None

    db = next(get_db())
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    return username


@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user_id = await verify_token_ws(token)
    if user_id is None:
        await websocket.close(code=1008)  # Policy Violation
        return

    await manager.connect(websocket, user_id)
    await manager.send_personal_message(f"Connected as user: {user_id}", websocket)

    # Broadcast the current order book to this new client
    db = next(get_db())
    order_book = get_order_book_snapshot(db)
    await manager.send_personal_message(
        f"Order Book Update: {json.dumps(order_book)}", websocket
    )

    trade_book = get_trade_snapshot(db)
    await manager.send_personal_message(
        f"Trade Book Update: {json.dumps(trade_book)}", websocket
    )

    try:
        while True:
            try:
                data = await websocket.receive_text()
                if data == "pong":
                    continue  # keep-alive response
                await manager.send_personal_message(f"You said: {data}", websocket)
            except WebSocketDisconnect:
                break
            except Exception:
                await asyncio.sleep(0.1)
    finally:
        manager.disconnect(websocket, user_id)
        await manager.broadcast(f"User {user_id} disconnected.")
