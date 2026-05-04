"""
PHASE 6.4 - Edge Discovery Routes
===================================
REST API endpoints for Edge Discovery Engine.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import random

from .edge_types import (
    EdgeStatus, EdgeCategory, PatternType, ValidationResult
)
from .feature_extractor import FeatureExtractor
from .pattern_scanner import PatternScanner
from .pattern_generator import PatternGenerator
from .signal_clusterer import SignalClusterer
from .edge_validator import EdgeValidator
from .edge_ranker import EdgeRanker
from .edge_repository import EdgeRepository

router = APIRouter(prefix="/api/edge-discovery", tags=["Edge Discovery Engine"])

# Initialize components
_repository: Optional[EdgeRepository] = None
_scanner: Optional[PatternScanner] = None
_generator: Optional[PatternGenerator] = None
_clusterer: Optional[SignalClusterer] = None
_validator: Optional[EdgeValidator] = None
_ranker: Optional[EdgeRanker] = None


def get_repository() -> EdgeRepository:
    global _repository
    if _repository is None:
        _repository = EdgeRepository()
    return _repository


def get_scanner() -> PatternScanner:
    global _scanner
    if _scanner is None:
        _scanner = PatternScanner()
    return _scanner


def get_generator() -> PatternGenerator:
    global _generator
    if _generator is None:
        _generator = PatternGenerator()
    return _generator


def get_clusterer() -> SignalClusterer:
    global _clusterer
    if _clusterer is None:
        _clusterer = SignalClusterer()
    return _clusterer


def get_validator() -> EdgeValidator:
    global _validator
    if _validator is None:
        _validator = EdgeValidator()
    return _validator


def get_ranker() -> EdgeRanker:
    global _ranker
    if _ranker is None:
        _ranker = EdgeRanker()
    return _ranker


# ==================== Request Models ====================

class DiscoveryRunRequest(BaseModel):
    symbol: str = "BTC"
    timeframe: str = "1d"
    pattern_types: Optional[List[str]] = None
    max_candidates: int = 20
    validate: bool = True


class ScanRequest(BaseModel):
    symbol: str = "BTC"
    timeframe: str = "1d"
    pattern_types: Optional[List[str]] = None
    min_confidence: float = 0.5


# ==================== Health ====================

@router.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "module": "edge_discovery_engine",
        "version": "phase6.4",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ==================== Static routes (before /{edge_id}) ====================

@router.get("/candidates")
async def get_candidates(
    status: Optional[str] = None,
    limit: int = 50
):
    """Get edge candidates"""
    repo = get_repository()
    candidates = repo.get_all_candidates(status)
    
    return {
        "count": len(candidates[:limit]),
        "candidates": candidates[:limit]
    }


@router.get("/validated")
async def get_validated_edges(limit: int = 50):
    """Get validated edges"""
    repo = get_repository()
    edges = repo.get_validated_edges(limit)
    
    return {
        "count": len(edges),
        "edges": edges
    }


@router.get("/top")
async def get_top_edges(limit: int = 10):
    """Get top ranked edges"""
    repo = get_repository()
    edges = repo.get_top_edges(limit)
    
    return {
        "count": len(edges),
        "top_edges": edges
    }


@router.get("/stats/overview")
async def get_stats():
    """Get discovery statistics"""
    repo = get_repository()
    stats = repo.get_statistics()
    
    return {
        "stats": stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/categories")
async def get_categories():
    """Get available edge categories"""
    return {
        "categories": [c.value for c in EdgeCategory],
        "pattern_types": [p.value for p in PatternType],
        "statuses": [s.value for s in EdgeStatus]
    }


# ==================== Discovery Operations ====================

@router.post("/run")
async def run_discovery(request: DiscoveryRunRequest):
    """
    Run full edge discovery pipeline.
    
    1. Scan for patterns
    2. Generate candidates
    3. Cluster patterns
    4. Validate candidates
    5. Rank and save edges
    """
    scanner = get_scanner()
    generator = get_generator()
    clusterer = get_clusterer()
    validator = get_validator()
    ranker = get_ranker()
    repo = get_repository()
    
    # Generate mock candles for discovery
    candles = _generate_mock_candles(request.symbol, request.timeframe, days=365)
    
    # Parse pattern types
    pattern_types = None
    if request.pattern_types:
        pattern_types = [PatternType(pt) for pt in request.pattern_types]
    
    # Step 1: Scan for patterns
    patterns = scanner.scan(candles, pattern_types=pattern_types)
    pattern_summary = scanner.get_pattern_summary(patterns)
    
    # Step 2: Cluster patterns
    clusters = clusterer.cluster_patterns(patterns)
    cluster_analysis = clusterer.analyze_clusters(clusters)
    
    # Step 3: Generate candidates
    candidates = generator.generate_candidates(patterns, max_candidates=request.max_candidates)
    
    # Save candidates
    for candidate in candidates:
        repo.save_candidate(candidate)
    
    # Step 4: Validate if requested
    validated_edges = []
    if request.validate:
        for candidate in candidates[:10]:  # Validate top 10
            validation = await validator.validate(candidate)
            edge = validator.create_discovered_edge(candidate, validation)
            
            if edge:
                validated_edges.append(edge)
                repo.save_edge(edge)
    
    # Step 5: Rank edges
    if validated_edges:
        validated_edges = ranker.rank_edges(validated_edges)
    
    return {
        "success": True,
        "discovery_summary": {
            "patterns_found": len(patterns),
            "pattern_breakdown": pattern_summary,
            "clusters_formed": len(clusters),
            "candidates_generated": len(candidates),
            "edges_validated": len(validated_edges)
        },
        "top_candidates": [c.to_dict() for c in candidates[:5]],
        "validated_edges": [e.to_dict() for e in validated_edges[:5]],
        "cluster_analysis": cluster_analysis
    }


@router.post("/scan")
async def scan_patterns(request: ScanRequest):
    """Scan for patterns without full discovery"""
    scanner = get_scanner()
    
    candles = _generate_mock_candles(request.symbol, request.timeframe, days=180)
    
    pattern_types = None
    if request.pattern_types:
        pattern_types = [PatternType(pt) for pt in request.pattern_types]
    
    patterns = scanner.scan(
        candles,
        pattern_types=pattern_types,
        min_confidence=request.min_confidence
    )
    
    summary = scanner.get_pattern_summary(patterns)
    
    return {
        "success": True,
        "patterns_found": len(patterns),
        "summary": summary,
        "sample_patterns": [p.to_dict() for p in patterns[:10]]
    }


@router.post("/validate/{edge_id}")
async def validate_candidate(edge_id: str):
    """Validate a specific candidate"""
    repo = get_repository()
    validator = get_validator()
    
    candidate_data = repo.get_candidate(edge_id)
    if not candidate_data:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Reconstruct candidate (simplified)
    from .edge_types import EdgeCandidate
    candidate = EdgeCandidate(
        edge_id=candidate_data["edge_id"],
        name=candidate_data["name"],
        description=candidate_data["description"],
        category=EdgeCategory(candidate_data["category"]),
        pattern_types=[PatternType(pt) for pt in candidate_data.get("pattern_types", [])],
        feature_conditions=candidate_data.get("feature_conditions", {}),
        expected_direction=candidate_data["expected_direction"],
        sample_size=candidate_data.get("sample_size", 0),
        win_rate_estimate=candidate_data.get("win_rate_estimate", 0),
        avg_return_estimate=candidate_data.get("avg_return_estimate", 0),
        status=EdgeStatus(candidate_data.get("status", "CANDIDATE"))
    )
    
    # Validate
    validation = await validator.validate(candidate)
    edge = validator.create_discovered_edge(candidate, validation)
    
    if edge:
        repo.save_edge(edge)
        return {
            "success": True,
            "validation": validation.to_dict(),
            "edge": edge.to_dict()
        }
    
    return {
        "success": False,
        "validation": validation.to_dict(),
        "message": "Validation failed"
    }


# ==================== Edge Management ====================

@router.get("/{edge_id}")
async def get_edge(edge_id: str):
    """Get edge by ID"""
    repo = get_repository()
    
    edge = repo.get_edge(edge_id)
    if not edge:
        candidate = repo.get_candidate(edge_id)
        if candidate:
            return {"type": "candidate", "data": candidate}
        raise HTTPException(status_code=404, detail="Edge not found")
    
    return {"type": "edge", "data": edge}


@router.patch("/{edge_id}/status")
async def update_edge_status(edge_id: str, status: str):
    """Update edge status"""
    repo = get_repository()
    
    try:
        EdgeStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    success = repo.update_edge_status(edge_id, status)
    if not success:
        success = repo.update_candidate_status(edge_id, status)
    
    return {"success": success, "edge_id": edge_id, "status": status}


@router.post("/{edge_id}/promote")
async def promote_to_production(edge_id: str):
    """Promote edge to production"""
    repo = get_repository()
    
    success = repo.promote_to_production(edge_id)
    if not success:
        raise HTTPException(status_code=404, detail="Edge not found")
    
    return {"success": True, "edge_id": edge_id, "status": "PRODUCTION"}


@router.post("/{edge_id}/deprecate")
async def deprecate_edge(edge_id: str):
    """Deprecate an edge"""
    repo = get_repository()
    
    success = repo.deprecate_edge(edge_id)
    if not success:
        raise HTTPException(status_code=404, detail="Edge not found")
    
    return {"success": True, "edge_id": edge_id, "status": "DEPRECATED"}


# ==================== Utilities ====================

def _generate_mock_candles(
    symbol: str,
    timeframe: str,
    days: int = 365
) -> List[Dict]:
    """Generate mock OHLCV data for testing"""
    intervals = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
    interval_seconds = intervals.get(timeframe, 3600)
    
    end_ts = datetime.now(timezone.utc).timestamp()
    start_ts = end_ts - (days * 86400)
    
    candles = []
    current_ts = start_ts
    
    base_prices = {"BTC": 50000, "ETH": 3000, "SOL": 100}
    price = base_prices.get(symbol, 1000)
    
    random.seed(42)  # For reproducibility
    
    while current_ts < end_ts:
        change = price * random.uniform(-0.03, 0.03)
        open_price = price
        close_price = price + change
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.015))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.015))
        
        candles.append({
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": int(current_ts * 1000),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": random.uniform(1000, 50000)
        })
        
        price = close_price
        current_ts += interval_seconds
    
    return candles
