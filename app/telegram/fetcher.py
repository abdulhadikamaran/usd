"""
Telegram Fetcher
=================
Manages the Telethon client connection and raw message fetching
from the @dolaraka12 channel.

This module only fetches — it does NOT parse or validate.
Parsing is handled by parser.py.
"""

import logging
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import Message

from app.config import settings

logger = logging.getLogger(__name__)

# Project root for session file location
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


from telethon.sessions import StringSession

class TelegramFetcher:
    """
    Wraps the Telethon client for fetching messages from the rate channel.

    Usage:
        fetcher = TelegramFetcher()
        await fetcher.connect()
        messages = await fetcher.fetch_new_messages(last_message_id=12345)
        await fetcher.disconnect()
    """

    def __init__(self):
        self._client: TelegramClient | None = None
        self._channel = None  # Resolved channel entity

    async def connect(self) -> None:
        """
        Connect to Telegram using the saved session string.
        Must have run scripts/auth.py first to create the session string.
        """
        self._client = TelegramClient(
            StringSession(settings.TELEGRAM_SESSION_STRING),
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
        )

        await self._client.connect()

        if not await self._client.is_user_authorized():
            raise RuntimeError(
                "Telegram session not authorized. "
                "Run 'python scripts/auth.py' first to authenticate."
            )

        # Resolve channel entity once
        self._channel = await self._client.get_entity(settings.TELEGRAM_CHANNEL)
        logger.info(
            f"Connected to Telegram. Channel: {self._channel.title} "
            f"({settings.TELEGRAM_CHANNEL})"
        )

    async def disconnect(self) -> None:
        """Disconnect from Telegram gracefully."""
        if self._client:
            await self._client.disconnect()
            self._client = None
            self._channel = None
            logger.info("Disconnected from Telegram")

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected."""
        return self._client is not None and self._client.is_connected()

    async def fetch_new_messages(
        self,
        last_message_id: int | None = None,
        limit: int = 20,
    ) -> list[Message]:
        """
        Fetch new messages from the channel since the last processed message.

        Args:
            last_message_id: The ID of the last processed message.
                             Only messages AFTER this ID are returned.
                             Pass None to get the most recent messages.
            limit: Maximum number of messages to fetch.

        Returns:
            List of Telethon Message objects, ordered most recent first.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            if last_message_id is not None:
                # Fetch messages newer than the last processed one
                messages = await self._client.get_messages(
                    self._channel,
                    limit=limit,
                    min_id=last_message_id,
                )
            else:
                # No previous reference — get the latest messages
                messages = await self._client.get_messages(
                    self._channel,
                    limit=limit,
                )

            # Filter to only text messages (skip photos, videos, etc. without text)
            text_messages = [m for m in messages if m.text]

            logger.info(
                f"Fetched {len(text_messages)} text messages "
                f"(total: {len(messages)}, since_id: {last_message_id})"
            )
            return text_messages

        except Exception as e:
            logger.error(f"Failed to fetch messages: {e}")
            raise

    async def fetch_initial_messages(
        self,
        count: int | None = None,
    ) -> list[Message]:
        """
        Fetch the most recent N messages for initial backfill.
        Used on first run when the database is empty.

        Args:
            count: Number of messages to fetch. Defaults to config value.

        Returns:
            List of Telethon Message objects, ordered most recent first.
        """
        if count is None:
            count = settings.INITIAL_FETCH_COUNT

        if not self.is_connected:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            messages = await self._client.get_messages(
                self._channel,
                limit=count,
            )

            text_messages = [m for m in messages if m.text]

            logger.info(
                f"Backfill: fetched {len(text_messages)} text messages "
                f"(requested: {count})"
            )
            return text_messages

        except Exception as e:
            logger.error(f"Failed to fetch initial messages: {e}")
            raise
