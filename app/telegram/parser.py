"""
Parser Engine
=============
Multi-layer message parser for extracting Erbil USD/IQD exchange rates.

Architecture:
    Layer 1 — Primary regex: matches the exact observed format from @dolaraka12
    Layer 2 — Relaxed regex: flexible fallback if format changes slightly
    Layer 3 — Anomaly guard: rejects rates deviating >10k from last stored
    Layer 4 — Full logging: every failure is logged with raw message text

Parser operates LINE-BY-LINE within each message, not at message level.
Only lines containing هەولێر + (پێنجی or سوور) are considered.
"""

import re
import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


# ── Parse Result ──────────────────────────────────────────────────────

@dataclass
class ParseResult:
    """Validated extraction result from a single Telegram message."""
    penzi_price: int
    sur_price: int
    average_price: int
    message_id: str


# ── Compiled Regex Patterns ───────────────────────────────────────────

# Layer 1: Primary — matches "$100=153,300" or "$100=153300" or "100$=153,300"
# Captures the price group (digits with optional commas/dots/spaces)
_PRIMARY_PRICE_RE = re.compile(
    r'[\$]?\s*100\s*[\$]?\s*=\s*([0-9]{3,6}(?:[,.\s][0-9]{3})*)',
)

# Layer 2: Relaxed — any number in the 100k-200k range on qualifying lines
# Matches standalone numbers like 153300, 153,300, 153.300
_RELAXED_PRICE_RE = re.compile(
    r'([1][0-9]{2}[,.\s]?[0-9]{3})',
)


# ── MessageParser Class ───────────────────────────────────────────────

class MessageParser:
    """
    Parses Telegram messages to extract Erbil Penzi and Sur exchange rates.

    Usage:
        parser = MessageParser()
        result = parser.parse_message(message_text, message_id, last_average)
        if result:
            # Valid extraction — store in DB
    """

    def __init__(self):
        self.city_keywords = settings.CITY_KEYWORDS
        self.penzi_keywords = settings.PENZI_KEYWORDS
        self.sur_keywords = settings.SUR_KEYWORDS
        self.exclude_keywords = settings.EXCLUDE_KEYWORDS
        self.min_price = settings.MIN_VALID_PRICE
        self.max_price = settings.MAX_VALID_PRICE
        self.max_deviation = settings.MAX_ANOMALY_DEVIATION

    def parse_message(
        self,
        text: str,
        message_id: str,
        last_average: int | None = None,
    ) -> ParseResult | None:
        """
        Full parsing pipeline for a single message.

        Args:
            text: Raw message text from Telegram.
            message_id: Telegram message ID (for tracing).
            last_average: Last stored average rate (for anomaly detection).
                          Pass None if no previous rate exists.

        Returns:
            ParseResult if valid extraction, None otherwise.
        """
        if not text or not text.strip():
            logger.debug(f"[msg={message_id}] Empty message, skipping")
            return None

        # ── Step 1: Exclusion check (message-level) ───────────────
        if self._is_excluded(text):
            logger.debug(f"[msg={message_id}] Excluded (gold/official keyword found)")
            return None

        # ── Step 2: Line-by-line extraction ───────────────────────
        penzi_price = None
        sur_price = None

        lines = text.split('\n')
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Does this line mention Erbil?
            if not self._has_city_keyword(line_stripped):
                continue

            # Is it a Penzi or Sur line?
            is_penzi = self._has_keyword(line_stripped, self.penzi_keywords)
            is_sur = self._has_keyword(line_stripped, self.sur_keywords)

            if not is_penzi and not is_sur:
                continue

            # Extract price from this line
            price = self._extract_price(line_stripped)
            if price is None:
                logger.debug(
                    f"[msg={message_id}] Price extraction failed on line: {line_stripped}"
                )
                continue

            # Validate range
            if not self._validate_price(price):
                logger.warning(
                    f"[msg={message_id}] Price {price:,} out of range "
                    f"({self.min_price:,}-{self.max_price:,}), line: {line_stripped}"
                )
                continue

            # Assign to correct type
            if is_penzi and penzi_price is None:
                penzi_price = price
                logger.debug(f"[msg={message_id}] Penzi extracted: {price:,}")
            elif is_sur and sur_price is None:
                sur_price = price
                logger.debug(f"[msg={message_id}] Sur extracted: {price:,}")

        # ── Step 3: Completeness check ────────────────────────────
        if penzi_price is None or sur_price is None:
            found = []
            if penzi_price is not None:
                found.append(f"penzi={penzi_price:,}")
            if sur_price is not None:
                found.append(f"sur={sur_price:,}")
            logger.debug(
                f"[msg={message_id}] Incomplete extraction "
                f"(found: {', '.join(found) if found else 'nothing'})"
            )
            return None

        # ── Step 4: Compute average ───────────────────────────────
        average = round((penzi_price + sur_price) / 2)

        # ── Step 5: Anomaly check ─────────────────────────────────
        if last_average is not None:
            deviation = abs(average - last_average)
            if deviation > self.max_deviation:
                logger.warning(
                    f"[msg={message_id}] ANOMALY DETECTED: "
                    f"avg={average:,}, prev={last_average:,}, "
                    f"deviation={deviation:,} (max={self.max_deviation:,}). "
                    f"Skipping."
                )
                return None

        # ── Success ───────────────────────────────────────────────
        logger.info(
            f"[msg={message_id}] Parsed OK: "
            f"penzi={penzi_price:,}, sur={sur_price:,}, avg={average:,}"
        )
        return ParseResult(
            penzi_price=penzi_price,
            sur_price=sur_price,
            average_price=average,
            message_id=message_id,
        )

    # ── Internal Methods ──────────────────────────────────────────────

    def _is_excluded(self, text: str) -> bool:
        """Check if the message should be excluded entirely (gold, etc.)."""
        for keyword in self.exclude_keywords:
            if keyword in text:
                return True
        return False

    def _has_city_keyword(self, line: str) -> bool:
        """Check if the line contains an Erbil city keyword."""
        for keyword in self.city_keywords:
            if keyword in line:
                return True
        return False

    def _has_keyword(self, line: str, keywords: list[str]) -> bool:
        """Check if the line contains any of the given keywords."""
        for keyword in keywords:
            if keyword in line:
                return True
        return False

    def _extract_price(self, line: str) -> int | None:
        """
        Extract the IQD price from a line using multi-layer regex.

        Layer 1: Primary pattern — $100=XXX,XXX or 100$=XXX,XXX
        Layer 2: Relaxed pattern — any 6-digit number in 100k-200k range

        Returns the extracted price as an integer, or None if extraction fails.
        """
        # Strip bold markers
        clean = line.replace('*', '').strip()

        # Layer 1: Primary regex
        match = _PRIMARY_PRICE_RE.search(clean)
        if match:
            price = self._normalize_price(match.group(1))
            if price is not None:
                return price

        # Layer 2: Relaxed regex (fallback)
        match = _RELAXED_PRICE_RE.search(clean)
        if match:
            price = self._normalize_price(match.group(1))
            if price is not None:
                return price

        return None

    def _normalize_price(self, raw: str) -> int | None:
        """
        Normalize a raw price string to an integer.

        Handles: "153,300" → 153300, "153.300" → 153300,
                 "153 300" → 153300, "153300" → 153300
        """
        try:
            cleaned = raw.replace(',', '').replace('.', '').replace(' ', '')
            return int(cleaned)
        except (ValueError, TypeError):
            return None

    def _validate_price(self, price: int) -> bool:
        """Check if price falls within the valid range."""
        return self.min_price <= price <= self.max_price
