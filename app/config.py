"""
Configuration & Constants Module
================================
Single source of truth for all settings, keywords, and thresholds.
Loads secrets from .env file, defines all parser keywords as constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Project Paths ─────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "rates.db"

# ── Load .env ─────────────────────────────────────────────────────────
load_dotenv(ENV_PATH)


class Settings:
    """Application settings loaded from environment variables and defaults."""

    # ── Telegram Credentials (from .env) ──────────────────────────────
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_PHONE: str = os.getenv("TELEGRAM_PHONE", "")
    TELEGRAM_CHANNEL: str = os.getenv("TELEGRAM_CHANNEL", "@iraqborsa")

    # ── Session ───────────────────────────────────────────────────────
    SESSION_NAME: str = "erbil_rate_session"
    SESSION_PATH: Path = PROJECT_ROOT / SESSION_NAME

    # ── Scheduler ─────────────────────────────────────────────────────
    FETCH_INTERVAL_SECONDS: int = 300  # 5 minutes

    # ── Database ──────────────────────────────────────────────────────
    DB_PATH: Path = DB_PATH
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # ── Parser: City Keywords ─────────────────────────────────────────
    # Lines must contain at least one of these to be considered Erbil
    CITY_KEYWORDS: list[str] = ["هەولێر"]

    # ── Parser: Rate Type Keywords ────────────────────────────────────
    PENZI_KEYWORDS: list[str] = ["پێنجی"]
    SUR_KEYWORDS: list[str] = ["سوور"]

    # ── Parser: Exclusion Keywords (skip entire message) ──────────────
    # Gold, official rate, central bank
    EXCLUDE_KEYWORDS: list[str] = [
        "ذهب",           # Arabic: gold
        "زێر",           # Kurdish: gold
        "الذهب",          # Arabic: the gold
    ]

    # ── Parser: Validation ────────────────────────────────────────────
    MIN_VALID_PRICE: int = 100_000   # Minimum valid IQD per 100 USD
    MAX_VALID_PRICE: int = 200_000   # Maximum valid IQD per 100 USD
    MAX_ANOMALY_DEVIATION: int = 10_000  # Max allowed change from last rate

    # ── Backfill ──────────────────────────────────────────────────────
    INITIAL_FETCH_COUNT: int = 1500  # Messages to fetch on first run

    # ── Timezone ──────────────────────────────────────────────────────
    TIMEZONE: str = "Asia/Baghdad"  # UTC+3, Iraq time

    def validate(self) -> list[str]:
        """Check that required settings are present. Returns list of errors."""
        errors = []
        if self.TELEGRAM_API_ID == 0:
            errors.append("TELEGRAM_API_ID is not set in .env")
        if not self.TELEGRAM_API_HASH:
            errors.append("TELEGRAM_API_HASH is not set in .env")
        if not self.TELEGRAM_PHONE:
            errors.append("TELEGRAM_PHONE is not set in .env")
        return errors


# ── Singleton instance ────────────────────────────────────────────────
settings = Settings()
