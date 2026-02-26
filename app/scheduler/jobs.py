"""
Scheduler / Background Jobs
=============================
Orchestrates the automated fetch → parse → store cycle.
Runs as an async background task within the FastAPI lifespan.

Flow:
    1. Connect to Telegram
    2. If DB is empty → backfill last 50 messages
    3. Every 5 minutes → fetch new messages → parse → store
    4. Update in-memory cache after each successful store
"""

import asyncio
import logging

from app.config import settings
from app import database as db
from app.database import IRAQ_TZ
from app.telegram.fetcher import TelegramFetcher
from app.telegram.parser import MessageParser
from app.ws_manager import manager
from app.models import RateResponse

logger = logging.getLogger(__name__)


# ── In-Memory Cache ───────────────────────────────────────────────────
# Stores the latest rate dict for instant API reads (no DB query needed)

_cached_rate: dict | None = None


def get_cached_rate() -> dict | None:
    """Get the cached latest rate. Returns None if cache is empty."""
    return _cached_rate


async def refresh_cache() -> None:
    """Load the latest rate from DB into memory cache."""
    global _cached_rate
    rate = await db.get_latest_rate()
    if rate:
        _cached_rate = dict(rate)
        logger.debug(f"Cache refreshed: avg={rate['erbil_average']:,}")


# ── Fetch Cycle ───────────────────────────────────────────────────────

async def run_fetch_cycle(
    fetcher: TelegramFetcher,
    parser: MessageParser,
) -> int:
    """
    Single fetch → parse → store cycle.

    1. Get the last stored message ID from DB
    2. Fetch new messages from Telegram since that ID
    3. Parse each message for Erbil rates
    4. Store valid rates (dedup handled by DB layer)
    5. Refresh the in-memory cache

    Returns:
        Number of new rates stored this cycle.
    """
    stored_count = 0

    try:
        # Get last processed message ID
        latest_rate = await db.get_latest_rate()
        last_msg_id = None
        if latest_rate:
            try:
                last_msg_id = int(latest_rate["source_message_id"])
            except (ValueError, TypeError):
                # Non-numeric message ID (e.g., "seed_001") — treat as no history
                last_msg_id = None

        # Fetch new messages
        messages = await fetcher.fetch_new_messages(
            last_message_id=last_msg_id,
            limit=20,
        )

        if not messages:
            logger.debug("No new messages found")
            return 0

        # Get last average for anomaly detection
        last_avg = await db.get_last_stored_average()
        last_avg = last_avg if last_avg > 0 else None

        # Parse and store (process oldest first for correct ordering)
        for msg in reversed(messages):
            result = parser.parse_message(
                text=msg.text,
                message_id=str(msg.id),
                last_average=last_avg,
            )

            if result is None:
                continue

            row_id = await db.insert_rate(
                penzi=result.penzi_price,
                sur=result.sur_price,
                average=result.average_price,
                message_id=result.message_id,
                created_at=msg.date.astimezone(IRAQ_TZ).isoformat(),
            )

            if row_id is not None:
                stored_count += 1
                last_avg = result.average_price  # Update for next anomaly check
                logger.info(
                    f"Stored rate: penzi={result.penzi_price:,}, "
                    f"sur={result.sur_price:,}, avg={result.average_price:,} "
                    f"(msg_id={msg.id})"
                )

        # Refresh cache if we stored anything
        if stored_count > 0:
            await refresh_cache()
            if _cached_rate:
                rate_24h = await db.get_rate_24h_ago()
                daily_change = _cached_rate["erbil_average"] - rate_24h["erbil_average"] if rate_24h else None
                resp = RateResponse(
                    city="Erbil",
                    penzi=_cached_rate["erbil_penzi"],
                    sur=_cached_rate["erbil_sur"],
                    average=_cached_rate["erbil_average"],
                    daily_change=daily_change,
                    last_updated=_cached_rate["created_at"],
                )
                asyncio.create_task(manager.broadcast(resp.model_dump()))

        return stored_count

    except Exception as e:
        logger.error(f"Fetch cycle failed: {e}", exc_info=True)
        return 0


# ── Initial Backfill ──────────────────────────────────────────────────

async def run_backfill(
    fetcher: TelegramFetcher,
    parser: MessageParser,
) -> int:
    """
    Fetch the last N messages from the channel to populate an empty DB.
    Only runs once on first start when database has no records.

    Returns:
        Number of rates stored during backfill.
    """
    stored_count = 0

    try:
        messages = await fetcher.fetch_initial_messages()

        if not messages:
            logger.warning("Backfill: no messages found in channel")
            return 0

        logger.info(f"Backfill: processing {len(messages)} messages...")

        last_avg = None

        # Process oldest first
        for msg in reversed(messages):
            result = parser.parse_message(
                text=msg.text,
                message_id=str(msg.id),
                last_average=last_avg,
            )

            if result is None:
                continue

            row_id = await db.insert_rate(
                penzi=result.penzi_price,
                sur=result.sur_price,
                average=result.average_price,
                message_id=result.message_id,
                created_at=msg.date.astimezone(IRAQ_TZ).isoformat(),
            )

            if row_id is not None:
                stored_count += 1
                last_avg = result.average_price

        # Refresh cache
        if stored_count > 0:
            await refresh_cache()

        logger.info(f"Backfill complete: stored {stored_count} rates")
        return stored_count

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        return 0


# ── Scheduler Loop ────────────────────────────────────────────────────

async def start_scheduler() -> None:
    """
    Main scheduler loop. Runs forever as a background task.

    1. Connects to Telegram
    2. Checks if DB needs backfill
    3. Enters infinite fetch loop (every 5 minutes)
    """
    fetcher = TelegramFetcher()
    parser = MessageParser()

    try:
        # Connect to Telegram
        logger.info("Scheduler: connecting to Telegram...")
        await fetcher.connect()
        logger.info("Scheduler: connected to Telegram")

        # Check if backfill needed
        count = await db.get_rates_count()
        if count == 0:
            logger.info("Scheduler: empty database — running initial backfill...")
            backfill_count = await run_backfill(fetcher, parser)
            logger.info(f"Scheduler: backfill stored {backfill_count} rates")
        else:
            logger.info(f"Scheduler: database has {count} existing records")
            await refresh_cache()  # Load existing latest into cache

        # Main loop
        interval = settings.FETCH_INTERVAL_SECONDS
        logger.info(f"Scheduler: starting fetch loop (every {interval}s)")

        while True:
            await asyncio.sleep(interval)

            logger.debug("Scheduler: running fetch cycle...")
            stored = await run_fetch_cycle(fetcher, parser)

            if stored > 0:
                logger.info(f"Scheduler: stored {stored} new rate(s)")
            else:
                logger.debug("Scheduler: no new rates this cycle")

    except asyncio.CancelledError:
        logger.info("Scheduler: shutting down...")
    except Exception as e:
        logger.error(f"Scheduler: fatal error: {e}", exc_info=True)
    finally:
        await fetcher.disconnect()
        logger.info("Scheduler: stopped")
