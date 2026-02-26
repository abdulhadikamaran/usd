"""
Database Module
===============
All SQLite interactions live here. No SQL leaks into other modules.
Uses aiosqlite for async compatibility with FastAPI.
Stores timestamps in Iraq time (UTC+3) per project requirements.
"""

import logging
from datetime import datetime, timezone, timedelta

import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)

# Iraq timezone: UTC+3
IRAQ_TZ = timezone(timedelta(hours=3))

# ── Schema ────────────────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS exchange_rates (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
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

_db: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Initialize the database: open connection, set pragmas, create schema."""
    global _db

    # Ensure data directory exists
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    _db = await aiosqlite.connect(str(settings.DB_PATH))
    _db.row_factory = aiosqlite.Row

    # Performance & reliability pragmas
    await _db.execute("PRAGMA journal_mode = WAL;")
    await _db.execute("PRAGMA busy_timeout = 5000;")
    await _db.execute("PRAGMA foreign_keys = ON;")

    # Create tables & indexes
    await _db.executescript(SCHEMA_SQL)
    await _db.commit()

    count = await get_rates_count()
    logger.info(f"Database initialized at {settings.DB_PATH} ({count} records)")


async def close_db() -> None:
    """Close the database connection gracefully."""
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("Database connection closed")


def _get_db() -> aiosqlite.Connection:
    """Get the active database connection. Raises if not initialized."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


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
    db = _get_db()
    
    timestamp = created_at if created_at else _now_iraq()
    
    try:
        cursor = await db.execute(
            """
            INSERT INTO exchange_rates (erbil_penzi, erbil_sur, erbil_average, source_message_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (penzi, sur, average, message_id, timestamp),
        )
        await db.commit()
        logger.info(
            f"Stored rate: penzi={penzi}, sur={sur}, avg={average}, msg_id={message_id}"
        )
        return cursor.lastrowid
    except aiosqlite.IntegrityError:
        # Duplicate message ID — already stored
        logger.debug(f"Duplicate message ID skipped: {message_id}")
        return None


# ── Queries ───────────────────────────────────────────────────────────

async def get_latest_rate() -> dict | None:
    """
    Get the most recently stored exchange rate.

    Returns a dict with keys: id, erbil_penzi, erbil_sur, erbil_average,
    source_message_id, created_at. Returns None if no data exists.
    """
    db = _get_db()
    cursor = await db.execute(
        "SELECT * FROM exchange_rates ORDER BY id DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def get_rate_24h_ago() -> dict | None:
    """
    Get the final exchange rate from yesterday (the market close price).
    Returns the most recent rate strictly before today's date.
    """
    db = _get_db()
    
    # Get the start of today in Iraq timezone
    today_str = datetime.now(IRAQ_TZ).strftime("%Y-%m-%d")
    
    # Try finding the latest rate that is older than today (i.e. yesterday's close)
    cursor = await db.execute(
        "SELECT * FROM exchange_rates WHERE substr(created_at, 1, 10) < ? ORDER BY created_at DESC LIMIT 1",
        (today_str,)
    )
    row = await cursor.fetchone()
    
    # If no rates from before today exist (e.g. newly created DB), grab the absolute oldest rate we have
    if not row:
        cursor2 = await db.execute("SELECT * FROM exchange_rates ORDER BY created_at ASC LIMIT 1")
        row = await cursor2.fetchone()
        await cursor2.close()
        
    await cursor.close()
    return dict(row) if row else None


async def get_last_stored_average() -> int | None:
    """
    Get the average price from the most recent record.
    Used for anomaly detection.
    """
    rate = await get_latest_rate()
    if rate is None:
        return None
    return rate["erbil_average"]


async def get_last_message_id() -> str | None:
    """
    Get the source_message_id of the most recent record.
    Used by the fetcher to avoid re-processing old messages.
    """
    db = _get_db()
    cursor = await db.execute(
        "SELECT source_message_id FROM exchange_rates ORDER BY id DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return row["source_message_id"]


async def get_rate_history(days: int = 7) -> list[dict]:
    """
    Get all exchange rate records from the last N days.
    Returns a list of dicts ordered by most recent first.
    """
    db = _get_db()
    # Calculate cutoff time in Iraq timezone
    cutoff = (datetime.now(IRAQ_TZ) - timedelta(days=days)).isoformat()
    
    if days <= 7:
        # Group by hour
        cursor = await db.execute(
            """
            SELECT 
                substr(created_at, 1, 13) || ':00:00+03:00' as last_updated,
                CAST(ROUND(AVG(erbil_penzi)) AS INTEGER) as penzi,
                CAST(ROUND(AVG(erbil_sur)) AS INTEGER) as sur,
                CAST(ROUND(AVG(erbil_average)) AS INTEGER) as average
            FROM exchange_rates
            WHERE created_at >= ?
            GROUP BY substr(created_at, 1, 13)
            ORDER BY created_at DESC
            """,
            (cutoff,)
        )
    else:
        # Group by day
        cursor = await db.execute(
            """
            SELECT 
                substr(created_at, 1, 10) || 'T12:00:00+03:00' as last_updated,
                CAST(ROUND(AVG(erbil_penzi)) AS INTEGER) as penzi,
                CAST(ROUND(AVG(erbil_sur)) AS INTEGER) as sur,
                CAST(ROUND(AVG(erbil_average)) AS INTEGER) as average
            FROM exchange_rates
            WHERE created_at >= ?
            GROUP BY substr(created_at, 1, 10)
            ORDER BY created_at DESC
            """,
            (cutoff,)
        )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_rates_count() -> int:
    """Get total number of stored exchange rate records."""
    db = _get_db()
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM exchange_rates")
    row = await cursor.fetchone()
    return row["cnt"] if row else 0
