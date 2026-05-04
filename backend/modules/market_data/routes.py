"""
Market Data Routes
==================
Sprint A2.2: Health, freshness, seed, refresh endpoints
"""

from fastapi import APIRouter

from .service_locator import get_market_data_ingestion_service

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.get("/health")
async def get_market_data_health():
    service = get_market_data_ingestion_service()
    return await service.get_health()


@router.get("/freshness")
async def get_market_data_freshness():
    service = get_market_data_ingestion_service()
    return await service.get_freshness()


@router.post("/seed")
async def seed_market_data():
    service = get_market_data_ingestion_service()
    return await service.seed_historical(limit=500)


@router.post("/refresh")
async def refresh_market_data():
    service = get_market_data_ingestion_service()
    return await service.refresh_latest(limit=3)
