"""
Market Data Service Locator
============================
Sprint A2.2: Singleton access to MarketDataIngestionService
"""

_market_data_ingestion_service = None


def init_market_data_ingestion_service(service):
    global _market_data_ingestion_service
    _market_data_ingestion_service = service
    return _market_data_ingestion_service


def get_market_data_ingestion_service():
    if _market_data_ingestion_service is None:
        raise RuntimeError("MarketDataIngestionService is not initialized")
    return _market_data_ingestion_service
