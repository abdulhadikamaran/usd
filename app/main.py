"""
Application Entry Point
========================
Creates the FastAPI app, wires up database lifecycle,
starts the background scheduler, registers routes,
serves the frontend static files, and configures middleware.

Run with:
    uvicorn app.main:app --reload
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app import database as db
from app.api.routes import router
from app.scheduler.jobs import start_scheduler

# ── Paths ─────────────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting Erbil USD/IQD Rate API...")
    await db.init_db()

    scheduler_task = asyncio.create_task(start_scheduler())
    logger.info("Background scheduler started")
    logger.info("API is ready to serve requests")

    yield

    logger.info("Shutting down...")
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    await db.close_db()
    logger.info("Shutdown complete")


# ── App Creation ──────────────────────────────────────────────────────

app = FastAPI(
    title="Erbil USD/IQD Market Rate API",
    description=(
        "Provides the average USD to IQD market exchange rate for Erbil city, "
        "automatically extracted from a public Telegram channel."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

# ── CORS Middleware ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── API Routes ────────────────────────────────────────────────────────
app.include_router(router)

# ── Static Files ──────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Root → Frontend ──────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """Serve the PWA frontend."""
    return FileResponse(str(STATIC_DIR / "index.html"))
