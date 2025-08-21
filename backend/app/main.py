from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from app.routes import users, orders, trades, auth, wallets
from app.core.cron_jobs import process_pending_orders_job
from app.websocket import router as ws_router
from app.db.session import engine
from app.db.data_model import Base
from app.core.logs import logger


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    Base.metadata.create_all(bind=engine)
    scheduler.add_job(process_pending_orders_job, "interval", seconds=60 * 5)
    scheduler.start()
    logger.info("🚀 Scheduler started with job: process_pending_orders_job (every 60s)")

    yield
    scheduler.shutdown()
    logger.info("🛑 Scheduler stopped.")


app = FastAPI(title="Real-Time Trading Platform", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(trades.router, prefix="/trades", tags=["Trades"])
app.include_router(wallets.router, prefix="/wallets", tags=["Wallets"])
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])


@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "Trading platform backend is running."}


# Health check endpoint
@app.get("/health")
def health():
    logger.debug("Health check called")
    return {"status": "ok"} 
