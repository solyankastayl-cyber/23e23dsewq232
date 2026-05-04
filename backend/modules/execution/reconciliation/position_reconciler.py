"""
Position Reconciler
===================

PHASE 4.2 - Reconciles positions between system and exchange.
"""

import time
import uuid
from typing import Dict, List, Optional, Tuple

from .reconciliation_types import (
    ExchangePosition,
    InternalPosition,
    Discrepancy,
    DiscrepancyType,
    DiscrepancySeverity,
    ResolutionStrategy
)


class PositionReconciler:
    """
    Reconciles positions:
    - Detects ghost positions (exchange only)
    - Detects missing positions (system only)
    - Detects size/side mismatches
    """
    
    def __init__(self):
        # Thresholds
        self._size_tolerance_pct = 0.1  # 0.1% size difference allowed
        self._min_size_for_check = 0.0001  # Minimum size to consider
        
        # Internal position tracking (mock for demo)
        self._positions: Dict[str, InternalPosition] = {}
        
        print("[PositionReconciler] Initialized (PHASE 4.2)")
    
    def reconcile(
        self,
        exchange_positions: List[ExchangePosition],
        exchange: str = "BINANCE"
    ) -> List[Discrepancy]:
        """
        Reconcile positions.
        Returns list of discrepancies found.
        """
        
        discrepancies = []
        now = int(time.time() * 1000)
        
        # Get exchange positions by symbol
        exchange_by_symbol = {p.symbol: p for p in exchange_positions if p.size >= self._min_size_for_check}
        
        # Get internal positions by symbol
        internal_by_symbol = {p.symbol: p for p in self._positions.values() if p.size >= self._min_size_for_check}
        
        # Check for ghost positions (exchange has, we don't)
        for symbol, ex_pos in exchange_by_symbol.items():
            if symbol not in internal_by_symbol:
                discrepancy = Discrepancy(
                    discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                    discrepancy_type=DiscrepancyType.GHOST_POSITION,
                    severity=DiscrepancySeverity.CRITICAL,
                    exchange=exchange,
                    symbol=symbol,
                    internal_value=None,
                    exchange_value=ex_pos.to_dict(),
                    difference=ex_pos.size,
                    description=f"Ghost position detected: {symbol} {ex_pos.side} {ex_pos.size}",
                    details={
                        "exchangeSize": ex_pos.size,
                        "exchangeSide": ex_pos.side,
                        "entryPrice": ex_pos.entry_price
                    },
                    resolution_strategy=ResolutionStrategy.SOFT_SYNC,
                    detected_at=now
                )
                discrepancies.append(discrepancy)
        
        # Check for missing positions (we have, exchange doesn't)
        for symbol, int_pos in internal_by_symbol.items():
            if symbol not in exchange_by_symbol:
                discrepancy = Discrepancy(
                    discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                    discrepancy_type=DiscrepancyType.MISSING_POSITION,
                    severity=DiscrepancySeverity.HIGH,
                    exchange=exchange,
                    symbol=symbol,
                    internal_value=int_pos.to_dict(),
                    exchange_value=None,
                    difference=int_pos.size,
                    description=f"Missing position: {symbol} {int_pos.side} {int_pos.size} not on exchange",
                    details={
                        "internalSize": int_pos.size,
                        "internalSide": int_pos.side,
                        "positionId": int_pos.position_id
                    },
                    resolution_strategy=ResolutionStrategy.SOFT_SYNC,
                    detected_at=now
                )
                discrepancies.append(discrepancy)
        
        # Check for mismatches (both have, but differ)
        for symbol in set(exchange_by_symbol.keys()) & set(internal_by_symbol.keys()):
            ex_pos = exchange_by_symbol[symbol]
            int_pos = internal_by_symbol[symbol]
            
            # Size mismatch
            if int_pos.size > 0:
                size_diff = abs(ex_pos.size - int_pos.size)
                size_diff_pct = (size_diff / int_pos.size) * 100
                
                if size_diff_pct > self._size_tolerance_pct:
                    severity = DiscrepancySeverity.CRITICAL if size_diff_pct > 5 else DiscrepancySeverity.HIGH
                    
                    discrepancy = Discrepancy(
                        discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                        discrepancy_type=DiscrepancyType.POSITION_SIZE_MISMATCH,
                        severity=severity,
                        exchange=exchange,
                        symbol=symbol,
                        internal_value=int_pos.size,
                        exchange_value=ex_pos.size,
                        difference=size_diff,
                        difference_pct=size_diff_pct,
                        description=f"Position size mismatch: {symbol} internal={int_pos.size} exchange={ex_pos.size}",
                        details={
                            "internalSize": int_pos.size,
                            "exchangeSize": ex_pos.size,
                            "positionId": int_pos.position_id
                        },
                        resolution_strategy=ResolutionStrategy.SOFT_SYNC,
                        detected_at=now
                    )
                    discrepancies.append(discrepancy)
            
            # Side mismatch
            if ex_pos.side.upper() != int_pos.side.upper():
                discrepancy = Discrepancy(
                    discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                    discrepancy_type=DiscrepancyType.POSITION_SIDE_MISMATCH,
                    severity=DiscrepancySeverity.CRITICAL,
                    exchange=exchange,
                    symbol=symbol,
                    internal_value=int_pos.side,
                    exchange_value=ex_pos.side,
                    description=f"Position side mismatch: {symbol} internal={int_pos.side} exchange={ex_pos.side}",
                    details={
                        "internalSide": int_pos.side,
                        "exchangeSide": ex_pos.side,
                        "positionId": int_pos.position_id
                    },
                    resolution_strategy=ResolutionStrategy.HARD_SYNC,
                    detected_at=now
                )
                discrepancies.append(discrepancy)
        
        return discrepancies
    
    def add_position(self, position: InternalPosition):
        """Add internal position"""
        self._positions[position.symbol] = position
    
    def remove_position(self, symbol: str):
        """Remove internal position"""
        self._positions.pop(symbol, None)
    
    def get_positions(self) -> List[InternalPosition]:
        """Get all internal positions"""
        return list(self._positions.values())
    
    def sync_position(self, exchange_position: ExchangePosition) -> InternalPosition:
        """Sync internal position to match exchange"""
        
        internal = InternalPosition(
            position_id=f"pos_{uuid.uuid4().hex[:8]}",
            symbol=exchange_position.symbol,
            side=exchange_position.side,
            size=exchange_position.size,
            entry_price=exchange_position.entry_price,
            strategy_id="SYNCED",
            created_at=int(time.time() * 1000),
            updated_at=int(time.time() * 1000)
        )
        
        self._positions[exchange_position.symbol] = internal
        return internal
    
    def clear(self):
        """Clear all positions"""
        self._positions.clear()
    
    def get_health(self) -> Dict:
        """Get reconciler health"""
        return {
            "engine": "PositionReconciler",
            "version": "1.0.0",
            "phase": "4.2",
            "status": "active",
            "trackedPositions": len(self._positions),
            "sizeTolerance": self._size_tolerance_pct,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
position_reconciler = PositionReconciler()
