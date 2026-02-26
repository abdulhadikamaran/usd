"""
Database Module
===============
All PostgreSQL interactions live here. No SQL leaks into other modules.
Uses asyncpg for async compatibility with FastAPI.
Stores timestamps in Iraq time (UTC+3) per project requirements.
"""

import logging
from datetime import datetime, timezone, timedelta

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

# Iraq timezone: UTC+3
IRAQ_TZ = timezone(timedelta(hours=3))

# ── Schema ────────────────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS exchange_rates (
    id                SERIAL PRIMARY KEY,
    erbil_penzi       INTEGER  NOT NULL,
    erbil_sur         INTEGER  NOT NULL,
    erbil_average     INTEGER  NOT NULL,
    source_message_id TEXT     NOT NULL UNIQUE,
    created_at        TEXT     NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_exchange_rates_created_at
    ON exchange_rates(created_at DESC);
"""

# ── Database Connection Manager ───────────────────────────────────────

_pool: asyncpg.Pool | None = None


async def init_db() -> None:
    """Initialize the database: create connection pool, create schema."""
    global _pool

    if not settings.DATABASE_URL:
        logger.warning("DATABASE_URL is not set in .env! Database connection will fail.")
        return

    try:
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=1,
            max_size=10,
        )

        # Create tables & indexes
        async with _pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)

        count = await get_rates_count()
        logger.info(f"PostgreSQL Database initialized ({count} records)")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")


async def close_db() -> None:
    """Close the database connection pool gracefully."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection closed")


def _get_pool() -> asyncpg.Pool:
    """Get the active database connection pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Database connection pool not initialized. Make sure DATABASE_URL is set.")
    return _pool


# ── Helper: Current Iraq Time ─────────────────────────────────────────

def _now_iraq() -> str:
    """Return current Iraq time (UTC+3) as ISO 8601 string."""
    return datetime.now(IRAQ_TZ).isoformat()


# ── Insert ────────────────────────────────────────────────────────────

async def insert_rate(
    penzi: int,
    sur: int,
    average: int,
    message_id: str,
    created_at: str | None = None,
) -> int | None:
    """
    Insert a new exchange rate record.

    Returns the row ID if successful, None if the message was already stored
    (duplicate source_message_id).
    """
    try:
        pool = _get_pool()
    except RuntimeError:
        return None

    timestamp = created_at if created_at else _now_iraq()
    
    try:
        async with pool.acquire() as conn:
            row_id = await conn.fetchval(
                """
                INSERT INTO exchange_rates (erbil_penzi, erbil_sur, erbil_average, source_message_id, created_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                penzi, sur, average, message_id, timestamp
            )
        logger.info(f"Stored rate: penzi={penzi}, sur={sur}, avg={average}, msg_id={message_id}")
        return row_id
    except asyncpg.exceptions.UniqueViolationError:
        # Duplicate message ID — already stored
        logger.debug(f"Duplicate message ID skipped: {message_id}")
        return None


# ── Queries ───────────────────────────────────────────────────────────

async def get_latest_rate() -> dict | None:
    try:
        pool = _get_pool()
    except RuntimeError:
        return None

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM exchange_rates ORDER BY id DESC LIMIT 1"
        )
    return dict(row) if row else None


async def get_rate_24h_ago() -> dict | None:
    try:
        pool = _get_pool()
    except RuntimeError:
        return None

    today_str = datetime.now(IRAQ_TZ).strftime("%Y-%m-%d")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM exchange_rates WHERE substr(created_at, 1, 10) < $1 ORDER BY created_at DESC LIMIT 1",
            today_str
        )
        if not row:
            row = await conn.fetchrow("SELECT * FROM exchange_rates ORDER BY created_at ASC LIMIT 1")
            
    return dict(row) if row else None


async def get_last_stored_average() -> int | None:
    rate = await get_latest_rate()
    if rate is None:
        return None
    return rate["erbil_average"]


async def get_last_message_id() -> str | None:
    try:
        pool = _get_pool()
    except RuntimeError:
        return None

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT source_message_id FROM exchange_rates ORDER BY id DESC LIMIT 1"
        )
    return row["source_message_id"] if row else None


async def get_rate_history(days: int = 7) -> list[dict]:
    try:
        pool = _get_pool()
    except RuntimeError:
        return []

    cutoff = (datetime.now(IRAQ_TZ) - timedelta(days=days)).isoformat()
    
    async with pool.acquire() as conn:
        if days <= 7:
            rows = await conn.fetch(
                """
                SELECT 
                    substr(created_at, 1, 13) || ':00:00+03:00' as last_updated,
                    CAST(ROUND(AVG(erbil_penzi)) AS INTEGER) as penzi,
                    CAST(ROUND(AVG(erbil_sur)) AS INTEGER) as sur,
                    CAST(ROUND(AVG(erbil_average)) AS INTEGER) as average
                FROM exchange_rates
                WHERE created_at >= $1
                GROUP BY substr(created_at, 1, 13)
                ORDER BY substr(created_at, 1, 13) DESC
                """,
                cutoff
            )
        else:
            rows = await conn.fetch(
                """
                SELECT 
                    substr(created_at, 1, 10) || 'T12:00:00+03:00' as last_updated,
                    CAST(ROUND(AVG(erbil_penzi)) AS INTEGER) as penzi,
                    CAST(ROUND(AVG(erbil_sur)) AS INTEGER) as sur,
                    CAST(ROUND(AVG(erbil_average)) AS INTEGER) as average
                FROM exchange_rates
                WHERE created_at >= $1
                GROUP BY substr(created_at, 1, 10)
                ORDER BY substr(created_at, 1, 10) DESC
                """,
                cutoff
            )
    return [dict(row) for row in rows]


async def get_rates_count() -> int:
    try:
        pool = _get_pool()
    except RuntimeError:
        return 0

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM exchange_rates")
    return row["cnt"] if row else 0
