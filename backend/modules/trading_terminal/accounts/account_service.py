"""
Account Service (TR1)
=====================

Main service for exchange account management.

Features:
- Create/delete connections
- Validate API keys
- Get account state
- Enable/disable connections
"""

import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import hashlib

from .account_types import (
    ExchangeType,
    ConnectionStatus,
    ExchangeConnection,
    AccountState,
    AccountBalance,
    AccountPosition
)


class AccountService:
    """
    Exchange Account Management Service.
    
    Manages connections to exchanges and retrieves account state.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Connections storage (in-memory for now)
        self._connections: Dict[str, ExchangeConnection] = {}
        
        # Account state cache
        self._state_cache: Dict[str, AccountState] = {}
        self._cache_ttl = 30  # seconds
        
        # Mock data for demo
        self._init_mock_connection()
        
        self._initialized = True
        print("[AccountService] Initialized")
    
    def _init_mock_connection(self):
        """Initialize mock connection for demo"""
        mock = ExchangeConnection(
            connection_id="conn_mock_001",
            exchange=ExchangeType.MOCK,
            label="Demo Account",
            description="Mock exchange for testing",
            api_key="mock_api_key_12345",
            api_secret="mock_secret",
            permissions=["READ", "SPOT_TRADE", "FUTURES_TRADE"],
            status=ConnectionStatus.ACTIVE,
            is_testnet=True
        )
        self._connections[mock.connection_id] = mock
    
    # ===========================================
    # Connection Management
    # ===========================================
    
    def create_connection(
        self,
        exchange: str,
        label: str,
        api_key: str,
        api_secret: str,
        passphrase: str = "",
        is_testnet: bool = False,
        description: str = "",
        created_by: str = "admin"
    ) -> Dict[str, Any]:
        """
        Create a new exchange connection.
        """
        try:
            exchange_type = ExchangeType(exchange.upper())
        except ValueError:
            return {
                "success": False,
                "error": f"Unsupported exchange: {exchange}"
            }
        
        connection = ExchangeConnection(
            exchange=exchange_type,
            label=label,
            description=description,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            is_testnet=is_testnet,
            status=ConnectionStatus.VALIDATING,
            created_by=created_by
        )
        
        # Validate keys
        validation = self._validate_connection(connection)
        
        if validation["valid"]:
            connection.status = ConnectionStatus.ACTIVE
            connection.permissions = validation.get("permissions", [])
            connection.last_validated_at = datetime.now(timezone.utc)
        else:
            connection.status = ConnectionStatus.ERROR
            connection.last_error = validation.get("error", "Validation failed")
        
        self._connections[connection.connection_id] = connection
        
        return {
            "success": True,
            "connection": connection.to_dict(),
            "validation": validation
        }
    
    def get_connection(self, connection_id: str) -> Optional[ExchangeConnection]:
        """Get connection by ID"""
        return self._connections.get(connection_id)
    
    def get_all_connections(self) -> List[ExchangeConnection]:
        """Get all connections"""
        return list(self._connections.values())
    
    def get_active_connections(self) -> List[ExchangeConnection]:
        """Get only active connections"""
        return [c for c in self._connections.values() if c.status == ConnectionStatus.ACTIVE]
    
    def delete_connection(self, connection_id: str) -> Dict[str, Any]:
        """Delete a connection"""
        if connection_id not in self._connections:
            return {"success": False, "error": "Connection not found"}
        
        del self._connections[connection_id]
        
        # Clear state cache
        if connection_id in self._state_cache:
            del self._state_cache[connection_id]
        
        return {"success": True, "message": f"Connection {connection_id} deleted"}
    
    def enable_connection(self, connection_id: str) -> Dict[str, Any]:
        """Enable a connection"""
        conn = self._connections.get(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        conn.status = ConnectionStatus.ACTIVE
        conn.updated_at = datetime.now(timezone.utc)
        
        return {"success": True, "message": "Connection enabled", "connection": conn.to_dict()}
    
    def disable_connection(self, connection_id: str) -> Dict[str, Any]:
        """Disable a connection"""
        conn = self._connections.get(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        conn.status = ConnectionStatus.DISABLED
        conn.updated_at = datetime.now(timezone.utc)
        
        return {"success": True, "message": "Connection disabled", "connection": conn.to_dict()}
    
    # ===========================================
    # Validation
    # ===========================================
    
    def _validate_connection(self, connection: ExchangeConnection) -> Dict[str, Any]:
        """Validate exchange connection"""
        
        if connection.exchange == ExchangeType.MOCK:
            return {
                "valid": True,
                "permissions": ["READ", "SPOT_TRADE", "FUTURES_TRADE"],
                "message": "Mock connection validated"
            }
        
        # Real exchange validation would go here
        # For now, simulate validation
        if not connection.api_key or not connection.api_secret:
            return {
                "valid": False,
                "error": "API key and secret required"
            }
        
        # Simulate API call delay
        time.sleep(0.1)
        
        return {
            "valid": True,
            "permissions": ["READ", "SPOT_TRADE"],
            "message": "Connection validated"
        }
    
    def validate_connection(self, connection_id: str) -> Dict[str, Any]:
        """Validate an existing connection"""
        conn = self._connections.get(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        validation = self._validate_connection(conn)
        
        if validation["valid"]:
            conn.status = ConnectionStatus.ACTIVE
            conn.permissions = validation.get("permissions", [])
            conn.last_validated_at = datetime.now(timezone.utc)
            conn.last_error = ""
        else:
            conn.status = ConnectionStatus.ERROR
            conn.last_error = validation.get("error", "")
        
        conn.updated_at = datetime.now(timezone.utc)
        
        return {
            "success": True,
            "validation": validation,
            "connection": conn.to_dict()
        }
    
    # ===========================================
    # Account State
    # ===========================================
    
    def get_account_state(self, connection_id: str, force_refresh: bool = False) -> Optional[AccountState]:
        """
        Get account state from exchange.
        
        Uses cache unless force_refresh is True.
        """
        conn = self._connections.get(connection_id)
        if not conn:
            return None
        
        if conn.status != ConnectionStatus.ACTIVE:
            return None
        
        # Check cache
        cached = self._state_cache.get(connection_id)
        if cached and not force_refresh:
            cache_age = (datetime.now(timezone.utc) - cached.updated_at).total_seconds()
            if cache_age < self._cache_ttl:
                return cached
        
        # Fetch from exchange
        state = self._fetch_account_state(conn)
        
        if state:
            self._state_cache[connection_id] = state
        
        return state
    
    def _fetch_account_state(self, connection: ExchangeConnection) -> AccountState:
        """Fetch account state from exchange adapter"""
        
        if connection.exchange == ExchangeType.MOCK:
            return self._get_mock_state(connection)
        
        # Real exchange integration would use broker adapters
        # For now, return empty state
        return AccountState(
            connection_id=connection.connection_id,
            exchange=connection.exchange.value
        )
    
    def _get_mock_state(self, connection: ExchangeConnection) -> AccountState:
        """Generate mock account state for demo"""
        return AccountState(
            connection_id=connection.connection_id,
            exchange=connection.exchange.value,
            balances=[
                AccountBalance(asset="USDT", free=10000.0, locked=500.0, total=10500.0, usd_value=10500.0),
                AccountBalance(asset="BTC", free=0.5, locked=0.0, total=0.5, usd_value=21500.0),
                AccountBalance(asset="ETH", free=5.0, locked=1.0, total=6.0, usd_value=12000.0)
            ],
            total_balance_usd=44000.0,
            positions=[
                AccountPosition(
                    symbol="BTCUSDT",
                    side="LONG",
                    size=0.3,
                    entry_price=42000.0,
                    mark_price=43500.0,
                    unrealized_pnl=450.0,
                    leverage=5.0,
                    margin_type="CROSS"
                ),
                AccountPosition(
                    symbol="ETHUSDT",
                    side="SHORT",
                    size=2.0,
                    entry_price=2100.0,
                    mark_price=2050.0,
                    unrealized_pnl=100.0,
                    leverage=3.0,
                    margin_type="ISOLATED"
                )
            ],
            total_unrealized_pnl=550.0,
            equity=44550.0,
            available_margin=35000.0,
            used_margin=9000.0
        )
    
    # ===========================================
    # Summary
    # ===========================================
    
    def get_accounts_summary(self) -> Dict[str, Any]:
        """Get summary of all accounts"""
        connections = self.get_all_connections()
        
        total_equity = 0.0
        active_count = 0
        
        for conn in connections:
            if conn.status == ConnectionStatus.ACTIVE:
                active_count += 1
                state = self.get_account_state(conn.connection_id)
                if state:
                    total_equity += state.equity
        
        return {
            "total_connections": len(connections),
            "active_connections": active_count,
            "total_equity_usd": round(total_equity, 2),
            "exchanges": list(set(c.exchange.value for c in connections))
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "AccountService",
            "status": "healthy",
            "phase": "TR1",
            "connections_count": len(self._connections),
            "active_connections": len(self.get_active_connections()),
            "cache_entries": len(self._state_cache)
        }


# Global singleton
account_service = AccountService()
