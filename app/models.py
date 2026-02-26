"""
Pydantic Response Models
========================
Type-safe API response serialization for all endpoints.
"""

from pydantic import BaseModel, Field


# ── Rate Responses ────────────────────────────────────────────────────

class RateResponse(BaseModel):
    """Response for GET /api/rate/latest"""
    city: str = Field(default="Erbil", description="City name")
    penzi: int = Field(description="Penzi (پێنجی) price per 100 USD")
    sur: int = Field(description="Sur (سوور) price per 100 USD")
    average: int = Field(description="Average of Penzi and Sur")
    daily_change: int | None = Field(default=None, description="Change in average compared to 24 hours ago")
    last_updated: str = Field(description="Timestamp in Iraq time (UTC+3)")


class HistoryResponse(BaseModel):
    """Response for GET /api/rate/history"""
    city: str = Field(default="Erbil", description="City name")
    count: int = Field(description="Number of records returned")
    rates: list[RateResponse] = Field(description="Historical rate records")


# ── Conversion Responses ──────────────────────────────────────────────

class UsdToIqdResponse(BaseModel):
    """Response for GET /api/convert/usd-to-iqd"""
    usd: float = Field(description="Input amount in USD")
    iqd: float = Field(description="Converted amount in IQD")
    rate_per_100: int = Field(description="Current rate per 100 USD")


class IqdToUsdResponse(BaseModel):
    """Response for GET /api/convert/iqd-to-usd"""
    iqd: float = Field(description="Input amount in IQD")
    usd: float = Field(description="Converted amount in USD")
    rate_per_100: int = Field(description="Current rate per 100 USD")


# ── Health Check ──────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Response for GET /api/health"""
    status: str = Field(description="Service status: 'ok' or 'degraded'")
    last_fetch: str | None = Field(description="Timestamp of last stored rate")
    rates_count: int = Field(description="Total exchange rate records in database")


# ── Error Response ────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response format"""
    error: str = Field(description="Human-readable error message")
    code: str = Field(description="Machine-readable error code")
