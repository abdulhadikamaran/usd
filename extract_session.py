import asyncio
import sys
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.config import settings

async def extract():
    print("Generating a BRAND NEW String Session...")
    
    # 1. Start a fresh, empty StringSession
    client = TelegramClient(
        StringSession(), 
        settings.TELEGRAM_API_ID, 
        settings.TELEGRAM_API_HASH
    )
    
    # 2. Start the client (this will ask for phone number & SMS code in the terminal)
    await client.start()
    
    # 3. Print the resulting string session
    print("\n\n" + "="*50)
    print("SUCCESS! HERE IS YOUR BRAND NEW SESSION STRING:")
    print("="*50)
    print(client.session.save())
    print("="*50 + "\n")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(extract())
