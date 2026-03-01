import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path so 'app' imports work
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.telegram.fetcher import TelegramFetcher
from app.telegram.parser import MessageParser
from app.database import init_db, insert_rate, close_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("recovery")

async def run_recovery():
    logger.info("Starting historical recovery...")
    
    # Initialize DB
    await init_db()
    
    # Initialize Fetcher and Parser
    fetcher = TelegramFetcher()
    parser = MessageParser()
    
    await fetcher.connect()
    
    try:
        # Fetch last 1500 messages (about 30-40 days of data)
        logger.info("Fetching last 1500 messages from channel...")
        messages = await fetcher.fetch_initial_messages(count=1500)
        
        # Telethon returns newest first. Reverse to process oldest first.
        messages.reverse()
        
        recovered_count = 0
        skipped_count = 0
        
        for msg in messages:
            if not msg.text:
                continue

            # Parse message (disable anomaly checking for historical backfill)
            result = parser.parse_message(
                text=msg.text,
                message_id=str(msg.id),
                last_average=None  
            )
            
            if result:
                # Convert message date to Iraq time string (UTC+3)
                from datetime import timedelta
                iraq_date = (msg.date + timedelta(hours=3)).isoformat()
                
                # Attempt to insert (insert_rate handles UNIQUE constraint on source_message_id)
                row_id = await insert_rate(
                    penzi=result.penzi_price,
                    sur=result.sur_price,
                    average=result.average_price,
                    message_id=result.message_id,
                    created_at=iraq_date
                )
                
                if row_id is not None:
                    recovered_count += 1
                else:
                    skipped_count += 1
                    
        logger.info(f"Recovery complete! Successfully recovered {recovered_count} missed prices.")
        logger.info(f"{skipped_count} prices were already in the database and skipped.")
        
    finally:
        await fetcher.disconnect()
        await close_db()

if __name__ == "__main__":
    asyncio.run(run_recovery())
