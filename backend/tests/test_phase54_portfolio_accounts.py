"""
Test Suite for PHASE 5.4 Portfolio Accounts Engine
===================================================

Tests for unified portfolio state aggregation across multiple exchanges.
All data is SIMULATED for demo purposes.

Test exchanges: BINANCE, BYBIT, OKX
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')


class TestPortfolioAccountsHealth:
    """Health and status endpoints tests"""
    
    def test_health_endpoint_returns_healthy(self):
        """GET /api/portfolio-accounts/health - should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "healthy"
        assert data.get("version") == "phase_5.4"
        
        # Verify all components are listed
        components = data.get("components", [])
        expected_components = [
            "account_aggregator",
            "balance_aggregator", 
            "position_aggregator",
            "margin_engine",
            "portfolio_state_builder"
        ]
        for comp in expected_components:
            assert comp in components, f"Component {comp} missing from health check"
        
        # Verify component_status exists
        assert "component_status" in data
        assert "timestamp" in data
        print(f"Health check passed with all {len(components)} components")
    
    def test_status_endpoint(self):
        """GET /api/portfolio-accounts/status - should return detailed status"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "state_builder" in data
        assert "components" in data
        assert "timestamp" in data
        print("Status endpoint returned valid data")


class TestPortfolioState:
    """Portfolio state endpoint tests"""
    
    def test_get_portfolio_state(self):
        """GET /api/portfolio-accounts/state - should return unified portfolio state"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/state")
        assert response.status_code == 200
        
        data = response.json()
        assert "state" in data
        
        state = data["state"]
        
        # Verify core state fields
        assert "totalEquity" in state
        assert "totalFreeBalance" in state
        assert "totalUsedMargin" in state
        assert "totalUnrealizedPnl" in state
        assert "totalRealizedPnl" in state
        assert "totalNotional" in state
        assert "exchangeCount" in state
        assert "positionsCount" in state
        assert "balancesCount" in state
        assert "longPositionsCount" in state
        assert "shortPositionsCount" in state
        assert "marginUtilization" in state
        assert "leverageExposure" in state
        assert "riskLevel" in state
        assert "timestamp" in state
        
        # Verify numerical values are reasonable (simulated data)
        assert state["totalEquity"] > 0, "Total equity should be positive"
        assert state["exchangeCount"] >= 1, "Should have at least 1 exchange"
        assert state["positionsCount"] >= 0, "Positions count should be non-negative"
        
        print(f"Portfolio state: equity=${state['totalEquity']:,.2f}, "
              f"{state['exchangeCount']} exchanges, "
              f"{state['positionsCount']} positions")
    
    def test_refresh_portfolio(self):
        """POST /api/portfolio-accounts/refresh - should refresh data from exchanges"""
        payload = {
            "exchanges": ["BINANCE", "BYBIT", "OKX"],
            "save_snapshot": True
        }
        
        response = requests.post(f"{BASE_URL}/api/portfolio-accounts/refresh", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("refreshed") == True
        assert "exchanges" in data
        assert "state" in data
        assert "timestamp" in data
        
        # Verify exchanges were refreshed
        assert data["exchanges"] == ["BINANCE", "BYBIT", "OKX"]
        
        print(f"Portfolio refreshed for {len(data['exchanges'])} exchanges")


class TestPortfolioAccounts:
    """Account aggregation endpoint tests"""
    
    def test_get_all_accounts(self):
        """GET /api/portfolio-accounts/accounts - should return list of accounts"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/accounts")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "accounts" in data
        assert "summary" in data
        
        # Verify accounts structure
        accounts = data["accounts"]
        assert len(accounts) > 0, "Should have at least one account"
        
        for account in accounts:
            assert "exchange" in account
            assert "account_id" in account
            assert "status" in account
            assert "equity" in account
            assert "free_balance" in account
            assert "used_margin" in account
            assert "unrealized_pnl" in account
            assert "realized_pnl" in account
            
            # Verify account has CONNECTED status (simulated)
            assert account["status"] == "CONNECTED"
        
        # Verify summary
        summary = data["summary"]
        assert "total_accounts" in summary
        assert "total_equity" in summary
        
        print(f"Found {data['count']} accounts with total equity ${summary['total_equity']:,.2f}")
    
    def test_get_account_by_exchange(self):
        """GET /api/portfolio-accounts/accounts?exchange=BINANCE - should return specific account"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/accounts?exchange=BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert "account" in data
        
        account = data["account"]
        assert account["exchange"] == "BINANCE"
        assert account["equity"] > 0
        
        print(f"BINANCE account: equity=${account['equity']:,.2f}")


class TestPortfolioBalances:
    """Balance aggregation endpoint tests"""
    
    def test_get_all_balances(self):
        """GET /api/portfolio-accounts/balances - should return balances aggregated by asset"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/balances")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "balances" in data
        assert "aggregated_by_asset" in data
        assert "summary" in data
        
        # Verify balances structure
        balances = data["balances"]
        assert len(balances) > 0, "Should have at least one balance"
        
        for balance in balances:
            assert "exchange" in balance
            assert "asset" in balance
            assert "free" in balance
            assert "locked" in balance
            assert "total" in balance
            assert "usd_value" in balance
        
        # Verify aggregated by asset
        aggregated = data["aggregated_by_asset"]
        assert len(aggregated) > 0, "Should have aggregated balances"
        
        # Check USDT is present (common stablecoin)
        if "USDT" in aggregated:
            usdt = aggregated["USDT"]
            assert "total_amount" in usdt
            assert "total_usd_value" in usdt
            assert "exchange_breakdown" in usdt
        
        print(f"Found {data['count']} balances across {len(aggregated)} assets")
    
    def test_get_balances_by_exchange(self):
        """GET /api/portfolio-accounts/balances?exchange=BINANCE - should return exchange balances"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/balances?exchange=BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "BINANCE"
        assert "count" in data
        assert "balances" in data
        
        # All balances should be from BINANCE
        for balance in data["balances"]:
            assert balance["exchange"] == "BINANCE"
        
        print(f"BINANCE has {data['count']} balance entries")
    
    def test_get_balance_distribution(self):
        """GET /api/portfolio-accounts/balances/distribution - should return asset and exchange distribution"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/balances/distribution")
        assert response.status_code == 200
        
        data = response.json()
        assert "by_asset" in data
        assert "by_exchange" in data
        assert "total_usd_value" in data
        
        # Distribution should be percentages
        by_asset = data["by_asset"]
        by_exchange = data["by_exchange"]
        
        if by_asset:
            total_asset_pct = sum(by_asset.values())
            assert 99 <= total_asset_pct <= 101, f"Asset distribution should sum to ~100%, got {total_asset_pct}"
        
        if by_exchange:
            total_exchange_pct = sum(by_exchange.values())
            assert 99 <= total_exchange_pct <= 101, f"Exchange distribution should sum to ~100%, got {total_exchange_pct}"
        
        print(f"Total USD value: ${data['total_usd_value']:,.2f}")


class TestPortfolioPositions:
    """Position aggregation endpoint tests"""
    
    def test_get_all_positions(self):
        """GET /api/portfolio-accounts/positions - should return positions aggregated by symbol"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/positions")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "positions" in data
        assert "aggregated_by_symbol" in data
        assert "summary" in data
        
        # Verify positions structure
        positions = data["positions"]
        
        for position in positions:
            assert "exchange" in position
            assert "symbol" in position
            assert "side" in position
            assert "size" in position
            assert "entry_price" in position
            assert "mark_price" in position
            assert "unrealized_pnl" in position
            assert "leverage" in position
            assert "notional_value" in position
        
        # Verify summary
        summary = data["summary"]
        assert "total_positions" in summary
        assert "total_notional" in summary
        assert "total_unrealized_pnl" in summary
        assert "long_short_split" in summary
        
        print(f"Found {data['count']} positions with total notional ${summary['total_notional']:,.2f}")
    
    def test_get_positions_by_exchange(self):
        """GET /api/portfolio-accounts/positions?exchange=BINANCE - should return exchange positions"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/positions?exchange=BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "BINANCE"
        assert "count" in data
        assert "positions" in data
        
        # All positions should be from BINANCE
        for position in data["positions"]:
            assert position["exchange"] == "BINANCE"
        
        print(f"BINANCE has {data['count']} positions")
    
    def test_get_long_short_split(self):
        """GET /api/portfolio-accounts/positions/long-short - should return long/short split"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/positions/long-short")
        assert response.status_code == 200
        
        data = response.json()
        assert "split" in data
        assert "total_unrealized_pnl" in data
        assert "total_notional" in data
        
        split = data["split"]
        assert "long_count" in split
        assert "short_count" in split
        assert "long_notional" in split
        assert "short_notional" in split
        assert "net_notional" in split
        assert "long_pct" in split
        
        # Verify counts are non-negative
        assert split["long_count"] >= 0
        assert split["short_count"] >= 0
        
        # Verify long percentage is valid
        if split["long_notional"] + split["short_notional"] > 0:
            assert 0 <= split["long_pct"] <= 100
        
        print(f"Long/Short split: {split['long_count']} long, {split['short_count']} short, "
              f"long_pct={split['long_pct']}%")


class TestMarginEngine:
    """Margin calculation endpoint tests"""
    
    def test_get_portfolio_margin(self):
        """GET /api/portfolio-accounts/margin - should return margin info with risk levels"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/margin")
        assert response.status_code == 200
        
        data = response.json()
        assert "portfolio" in data
        assert "by_exchange" in data
        assert "stress_flags" in data
        assert "headroom" in data
        
        # Verify portfolio margin
        portfolio = data["portfolio"]
        assert "total_margin" in portfolio
        assert "total_used_margin" in portfolio
        assert "total_free_margin" in portfolio
        assert "margin_utilization_pct" in portfolio
        assert "avg_leverage_exposure" in portfolio
        assert "overall_risk_level" in portfolio
        
        # Verify risk level is valid
        valid_risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert portfolio["overall_risk_level"] in valid_risk_levels
        
        # Verify by_exchange has entries
        by_exchange = data["by_exchange"]
        assert len(by_exchange) > 0, "Should have margin info for at least one exchange"
        
        for exchange, margin in by_exchange.items():
            assert "total_margin" in margin
            assert "used_margin" in margin
            assert "free_margin" in margin
            assert "margin_utilization" in margin
            assert "risk_level" in margin
        
        print(f"Portfolio margin: ${portfolio['total_margin']:,.2f}, "
              f"utilization={portfolio['margin_utilization_pct']}%, "
              f"risk={portfolio['overall_risk_level']}")
    
    def test_get_margin_by_exchange(self):
        """GET /api/portfolio-accounts/margin?exchange=BINANCE - should return exchange margin"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/margin?exchange=BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "BINANCE"
        assert "margin" in data
        
        margin = data["margin"]
        assert "total_margin" in margin
        assert "risk_level" in margin
        
        print(f"BINANCE margin: ${margin['total_margin']:,.2f}, risk={margin['risk_level']}")


class TestExchangeDetails:
    """Exchange-specific endpoint tests"""
    
    def test_get_exchange_details_binance(self):
        """GET /api/portfolio-accounts/exchange/BINANCE - should return detailed info for BINANCE"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/exchange/BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "BINANCE"
        assert "summary" in data
        assert "account" in data
        assert "balances" in data
        assert "positions" in data
        assert "margin" in data
        
        # Verify summary
        summary = data["summary"]
        assert "equity" in summary
        assert "positions_count" in summary
        assert "balances_count" in summary
        assert "risk_level" in summary
        
        print(f"BINANCE: equity=${summary['equity']:,.2f}, "
              f"{summary['positions_count']} positions, "
              f"{summary['balances_count']} balances")
    
    def test_get_exchange_details_bybit(self):
        """GET /api/portfolio-accounts/exchange/BYBIT - should return detailed info for BYBIT"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/exchange/BYBIT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "BYBIT"
        assert "summary" in data
        
        print(f"BYBIT: equity=${data['summary']['equity']:,.2f}")
    
    def test_get_exchange_details_okx(self):
        """GET /api/portfolio-accounts/exchange/OKX - should return detailed info for OKX"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/exchange/OKX")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "OKX"
        assert "summary" in data
        
        print(f"OKX: equity=${data['summary']['equity']:,.2f}")
    
    def test_get_exchange_details_invalid_returns_simulated(self):
        """GET /api/portfolio-accounts/exchange/INVALID - returns simulated data for any exchange (demo mode)"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/exchange/INVALID")
        # In demo mode, simulated data is generated for any exchange
        assert response.status_code == 200
        data = response.json()
        assert data["exchange"] == "INVALID"
        # Should have simulated but empty positions/balances
        assert data["positions"] == []
        assert data["balances"] == []
        print("Demo mode: simulated data returned for unknown exchange")


class TestExposure:
    """Position exposure endpoint tests"""
    
    def test_get_all_exposure(self):
        """GET /api/portfolio-accounts/exposure - should return position exposure by symbol"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/exposure")
        assert response.status_code == 200
        
        data = response.json()
        assert "exposure" in data
        assert "timestamp" in data
        
        exposure = data["exposure"]
        
        for symbol, exp in exposure.items():
            assert "total_long_size" in exp
            assert "total_short_size" in exp
            assert "net_exposure" in exp
            assert "gross_exposure" in exp
            assert "long_notional" in exp
            assert "short_notional" in exp
            assert "exchanges_long" in exp
            assert "exchanges_short" in exp
        
        print(f"Found exposure info for {len(exposure)} symbols")
    
    def test_get_exposure_by_symbol(self):
        """GET /api/portfolio-accounts/exposure?symbol=BTCUSDT - should return specific symbol exposure"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/exposure?symbol=BTCUSDT")
        assert response.status_code == 200
        
        data = response.json()
        assert "exposure" in data
        
        # May or may not have BTCUSDT depending on simulated positions
        if "BTCUSDT" in data["exposure"]:
            exp = data["exposure"]["BTCUSDT"]
            assert "net_exposure" in exp
            print(f"BTCUSDT net exposure: {exp['net_exposure']}")
        else:
            print("BTCUSDT not found in current exposure")


class TestHistory:
    """Portfolio history endpoint tests"""
    
    def test_get_portfolio_history(self):
        """GET /api/portfolio-accounts/history - should return portfolio history"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "in_memory" in data
        assert "database" in data
        assert "timestamp" in data
        
        # Verify in_memory structure
        in_memory = data["in_memory"]
        assert "count" in in_memory
        assert "entries" in in_memory
        
        # Verify database structure
        database = data["database"]
        assert "count" in database
        assert "entries" in database
        
        print(f"History: {in_memory['count']} in-memory, {database['count']} in database")
    
    def test_get_history_with_limit(self):
        """GET /api/portfolio-accounts/history?limit=10 - should respect limit param"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/history?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        # Entries should be <= limit (may have fewer if not enough data)
        assert len(data["in_memory"]["entries"]) <= 10
        print("History limit parameter working correctly")


class TestAnalytics:
    """Portfolio analytics endpoint tests"""
    
    def test_get_analytics(self):
        """GET /api/portfolio-accounts/analytics - should return portfolio analytics"""
        response = requests.get(f"{BASE_URL}/api/portfolio-accounts/analytics")
        assert response.status_code == 200
        
        data = response.json()
        assert "analytics" in data
        assert "timestamp" in data
        
        analytics = data["analytics"]
        assert "period_days" in analytics
        
        # May have no_data=True if just started
        if not analytics.get("no_data"):
            if "equity" in analytics:
                equity = analytics["equity"]
                assert "start" in equity or "min" in equity
        
        print(f"Analytics retrieved for {analytics.get('period_days', 7)} day period")


class TestIntegration:
    """Integration tests for end-to-end flows"""
    
    def test_full_refresh_and_state_flow(self):
        """Test complete refresh -> state -> accounts -> positions flow"""
        # 1. Refresh portfolio
        refresh_resp = requests.post(
            f"{BASE_URL}/api/portfolio-accounts/refresh",
            json={"exchanges": ["BINANCE", "BYBIT", "OKX"]}
        )
        assert refresh_resp.status_code == 200
        
        # 2. Get state
        state_resp = requests.get(f"{BASE_URL}/api/portfolio-accounts/state")
        assert state_resp.status_code == 200
        state = state_resp.json()["state"]
        
        # 3. Get accounts
        accounts_resp = requests.get(f"{BASE_URL}/api/portfolio-accounts/accounts")
        assert accounts_resp.status_code == 200
        accounts_data = accounts_resp.json()
        
        # 4. Verify consistency
        assert state["exchangeCount"] == accounts_data["count"], \
            "Exchange count should match between state and accounts"
        
        # 5. Get positions
        positions_resp = requests.get(f"{BASE_URL}/api/portfolio-accounts/positions")
        assert positions_resp.status_code == 200
        positions_data = positions_resp.json()
        
        # 6. Verify positions count matches
        assert state["positionsCount"] == positions_data["count"], \
            "Positions count should match between state and positions"
        
        print("Integration test passed: refresh -> state -> accounts -> positions flow")
    
    def test_unified_portfolio_view(self):
        """Test that portfolio aggregates correctly across exchanges"""
        # Get all accounts
        accounts_resp = requests.get(f"{BASE_URL}/api/portfolio-accounts/accounts")
        assert accounts_resp.status_code == 200
        accounts = accounts_resp.json()["accounts"]
        
        # Sum equity from individual accounts
        individual_equity = sum(acc["equity"] for acc in accounts)
        
        # Get portfolio state
        state_resp = requests.get(f"{BASE_URL}/api/portfolio-accounts/state")
        assert state_resp.status_code == 200
        total_equity = state_resp.json()["state"]["totalEquity"]
        
        # They should match (or be very close due to timing)
        # Using a tolerance due to simulated data randomness
        assert abs(individual_equity - total_equity) < 0.01 * total_equity, \
            f"Individual equity sum {individual_equity} should match total {total_equity}"
        
        print(f"Unified portfolio view: total equity ${total_equity:,.2f} aggregated from "
              f"{len(accounts)} exchanges")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
