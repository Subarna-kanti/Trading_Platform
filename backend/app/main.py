from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from contextlib import asynccontextmanager
from app.routes import users, orders, trades
from app.websocket import router as ws_router
from app.db.session import engine
from app.db.data_model import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    Base.metadata.create_all(bind=engine)
    yield
    # (Optional) Shutdown logic here

app = FastAPI(
    title="Real-Time Trading Platform",
    version="1.0",
    lifespan=lifespan
)

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

# Health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}