# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import users, orders, trades
from backend.app.websocket import router as ws_router

app = FastAPI(title="Real-Time Trading Platform", version="1.0")

# CORS configuration (if frontend runs separately)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(trades.router, prefix="/trades", tags=["Trades"])
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])

@app.get("/")
def root():
    return {"message": "Trading platform backend is running."}
