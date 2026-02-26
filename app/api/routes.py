"""
API Route Handlers
==================
All REST API endpoints. Thin handlers that validate input,
call the database, apply formulas, and return Pydantic models.
Zero business logic lives here.
"""

from fastapi import APIRouter, Query, HTTPException, WebSocket, WebSocketDisconnect
from app.ws_manager import manager

from app import database as db
from app.models import (
    RateResponse,
    UsdToIqdResponse,
    IqdToUsdResponse,
    HistoryResponse,
    HealthResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api")


# ── GET /api/rate/latest ──────────────────────────────────────────────

@router.get(
    "/rate/latest",
    response_model=RateResponse,
    responses={503: {"model": ErrorResponse}},
    summary="Get latest Erbil exchange rate",
    description="Returns the most recently stored USD/IQD exchange rate for Erbil.",
)
async def get_latest_rate():
    rate = await db.get_latest_rate()
    if rate is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "No exchange rate data available yet.", "code": "NO_DATA"},
        )
    rate_24h = await db.get_rate_24h_ago()
    daily_change = rate["erbil_average"] - rate_24h["erbil_average"] if rate_24h else None

    return RateResponse(
        city="Erbil",
        penzi=rate["erbil_penzi"],
        sur=rate["erbil_sur"],
        average=rate["erbil_average"],
        daily_change=daily_change,
        last_updated=rate["created_at"],
    )


# ── WS /api/ws ────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── GET /api/convert/usd-to-iqd ──────────────────────────────────────

@router.get(
    "/convert/usd-to-iqd",
    response_model=UsdToIqdResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Convert USD to IQD",
    description="Converts a USD amount to IQD using the latest Erbil average rate.",
)
async def convert_usd_to_iqd(
    amount: float = Query(
        ...,
        gt=0,
        description="Amount in USD to convert (must be positive)",
    ),
):
    rate = await db.get_latest_rate()
    if rate is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "No exchange rate data available yet.", "code": "NO_DATA"},
        )

    average = rate["erbil_average"]
    iqd = amount * (average / 100)

    return UsdToIqdResponse(
        usd=amount,
        iqd=round(iqd, 2),
        rate_per_100=average,
    )


# ── GET /api/convert/iqd-to-usd ──────────────────────────────────────

@router.get(
    "/convert/iqd-to-usd",
    response_model=IqdToUsdResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Convert IQD to USD",
    description="Converts an IQD amount to USD using the latest Erbil average rate.",
)
async def convert_iqd_to_usd(
    amount: float = Query(
        ...,
        gt=0,
        description="Amount in IQD to convert (must be positive)",
    ),
):
    rate = await db.get_latest_rate()
    if rate is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "No exchange rate data available yet.", "code": "NO_DATA"},
        )

    average = rate["erbil_average"]
    usd = amount / (average / 100)

    return IqdToUsdResponse(
        iqd=amount,
        usd=round(usd, 2),
        rate_per_100=average,
    )


# ── GET /api/rate/history ─────────────────────────────────────────────

@router.get(
    "/rate/history",
    response_model=HistoryResponse,
    summary="Get historical exchange rates",
    description="Returns exchange rate records from the last N days.",
)
async def get_rate_history(
    days: int = Query(
        default=7,
        ge=1,
        le=365,
        description="Number of days of history to return (1-365)",
    ),
):
    history = await db.get_rate_history(days=days)
    rates = [
        RateResponse(
            city="Erbil",
            penzi=r["penzi"],
            sur=r["sur"],
            average=r["average"],
            last_updated=r["last_updated"],
        )
        for r in history
    ]
    return HistoryResponse(
        city="Erbil",
        count=len(rates),
        rates=rates,
    )


# ── GET /api/health ───────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service status, last fetch time, and total record count.",
)
async def health_check():
    rate = await db.get_latest_rate()
    count = await db.get_rates_count()

    return HealthResponse(
        status="ok" if rate is not None else "degraded",
        last_fetch=rate["created_at"] if rate else None,
        rates_count=count,
    )
