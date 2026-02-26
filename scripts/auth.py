"""
Telegram Session Authentication Script
=======================================
Run this ONCE to authenticate with Telegram and create a .session file.
Telegram will send an OTP code to your phone — type it when prompted.

Usage:
    python scripts/auth.py

After successful auth, a .session file is created in the project root.
The main app reuses this session silently — no more OTP needed.
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon import TelegramClient
from app.config import settings


async def main():
    print("=" * 50)
    print("  Telegram Session Authentication")
    print("=" * 50)

    # Validate config
    errors = settings.validate()
    if errors:
        print(f"\n  ERROR: Missing configuration:")
        for e in errors:
            print(f"    - {e}")
        print(f"\n  Please check your .env file at: {settings.DB_PATH.parent.parent / '.env'}")
        return

    print(f"\n  API ID:   {settings.TELEGRAM_API_ID}")
    print(f"  Phone:    {settings.TELEGRAM_PHONE}")
    print(f"  Session:  {settings.SESSION_NAME}.session")
    print(f"  Channel:  {settings.TELEGRAM_CHANNEL}")

    # Create client
    client = TelegramClient(
        str(Path(__file__).resolve().parent.parent / settings.SESSION_NAME),
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH,
    )

    print(f"\n  Connecting to Telegram...")
    await client.start(phone=settings.TELEGRAM_PHONE)

    # Verify connection
    me = await client.get_me()
    print(f"\n  Authenticated as: {me.first_name} (@{me.username})")

    # Test channel access
    print(f"\n  Testing access to {settings.TELEGRAM_CHANNEL}...")
    try:
        channel = await client.get_entity(settings.TELEGRAM_CHANNEL)
        print(f"  Channel found: {channel.title}")

        # Fetch 1 message to verify read access
        messages = await client.get_messages(channel, limit=1)
        if messages:
            print(f"  Latest message date: {messages[0].date}")
            print(f"  Read access confirmed!")
        else:
            print(f"  Channel is empty or no messages found.")
    except Exception as e:
        print(f"  WARNING: Could not access channel: {e}")
        print(f"  The session is still valid — check the channel username.")

    await client.disconnect()

    print(f"\n  Session file saved: {settings.SESSION_NAME}.session")
    print(f"\n  You're all set! The main app will use this session automatically.")
    print("=" * 50)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
