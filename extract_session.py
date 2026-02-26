import asyncio
import sys
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.config import settings

async def extract():
    print("Extracting String Session from local .session file...")
    
    # 1. Connect using the existing SQLite session file
    client = TelegramClient(
        settings.SESSION_NAME, 
        settings.TELEGRAM_API_ID, 
        settings.TELEGRAM_API_HASH
    )
    
    await client.connect()
    
    if await client.is_user_authorized():
        # 2. Convert to StringSession
        string_session = StringSession.save(client.session)
        print("\n=== SUCCESS ===")
        print(f"STRING_SESSION={string_session}")
        print("===============\n")
    else:
        print("Error: The local session file is not authorized.")
        
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(extract())
