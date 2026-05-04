"""
PHASE 7 - Correlation Intelligence Module Backend Tests
=========================================================
Tests for cross-asset correlation analysis, lead/lag relationships, 
market regimes, and cross-asset trading signals.

Assets tracked: BTC, ETH, TOTAL, SPX, NASDAQ, DXY, US10Y, GOLD
Uses mock data generators for testing since no real market data feed.
"""

import pytest
import requests
import os

# Get base URL from environment - use localhost since public URL may not have routing configured
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# If public URL doesn't work, fallback to localhost
if 'emergentagent.com' in BASE_URL:
    BASE_URL = 'http://localhost:8001'


class TestCorrelationHealth:
    """Health check endpoint tests"""
    
    def test_health_status_healthy(self):
        """GET /api/correlation/health - должен вернуть status healthy"""
        response = requests.get(f"{BASE_URL}/api/correlation/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✅ Health status: {data['status']}")
    
    def test_health_version_phase7(self):
        """GET /api/correlation/health - должен вернуть version phase7_correlation_v1"""
        response = requests.get(f"{BASE_URL}/api/correlation/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["version"] == "phase7_correlation_v1"
        print(f"✅ Version: {data['version']}")
    
    def test_health_engines_ready(self):
        """GET /api/correlation/health - должен показать все движки ready"""
        response = requests.get(f"{BASE_URL}/api/correlation/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "engines" in data
        engines = data["engines"]
        
        expected_engines = ["matrix", "rolling", "lead_lag", "regime", "signals"]
        for engine in expected_engines:
            assert engines.get(engine) == "ready", f"Engine {engine} should be ready"
        
        print(f"✅ All engines ready: {list(engines.keys())}")


class TestCorrelationMatrix:
    """Correlation matrix endpoint tests"""
    
    def test_matrix_returns_pair_count(self):
        """GET /api/correlation/matrix - должен вернуть pair_count"""
        response = requests.get(f"{BASE_URL}/api/correlation/matrix")
        assert response.status_code == 200
        
        data = response.json()
        assert "pair_count" in data
        assert data["pair_count"] > 0
        print(f"✅ Matrix pair_count: {data['pair_count']}")
    
    def test_matrix_returns_summary(self):
        """GET /api/correlation/matrix - должен вернуть summary"""
        response = requests.get(f"{BASE_URL}/api/correlation/matrix")
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        summary = data["summary"]
        
        # Summary должен содержать статистику
        assert "total_pairs" in summary
        assert "avg_correlation" in summary
        print(f"✅ Matrix summary: {summary.get('total_pairs')} pairs, avg corr: {summary.get('avg_correlation', 0):.4f}")
    
    def test_matrix_returns_strongest(self):
        """GET /api/correlation/matrix - должен вернуть strongest"""
        response = requests.get(f"{BASE_URL}/api/correlation/matrix")
        assert response.status_code == 200
        
        data = response.json()
        assert "strongest" in data
        strongest = data["strongest"]
        
        assert isinstance(strongest, list)
        assert len(strongest) > 0
        
        # Each strongest entry should have value and pair info
        first = strongest[0]
        assert "value" in first
        assert "pair" in first
        print(f"✅ Strongest correlations: {len(strongest)} pairs, top: {first.get('value', 0):.4f}")
    
    def test_matrix_returns_full_structure(self):
        """GET /api/correlation/matrix - должен вернуть полную структуру"""
        response = requests.get(f"{BASE_URL}/api/correlation/matrix")
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields
        assert "symbol" in data
        assert "timeframe" in data
        assert "method" in data
        assert "window_size" in data
        assert "matrix" in data
        assert "computed_at" in data
        
        print(f"✅ Full matrix structure valid, timeframe: {data['timeframe']}, method: {data['method']}")


class TestRollingCorrelation:
    """Rolling correlation endpoint tests"""
    
    def test_rolling_btc_spx(self):
        """GET /api/correlation/rolling?asset_a=BTC&asset_b=SPX - должен вернуть rolling correlation"""
        response = requests.get(f"{BASE_URL}/api/correlation/rolling", params={
            "asset_a": "BTC",
            "asset_b": "SPX"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "current_value" in data
        assert "trend" in data
        assert "change" in data
        print(f"✅ BTC-SPX rolling correlation: current={data['current_value']:.4f}, trend={data['trend']}")
    
    def test_rolling_returns_trend(self):
        """GET /api/correlation/rolling - должен вернуть trend"""
        response = requests.get(f"{BASE_URL}/api/correlation/rolling", params={
            "asset_a": "BTC",
            "asset_b": "SPX"
        })
        assert response.status_code == 200
        
        data = response.json()
        trend = data["trend"]
        
        # Trend должен быть одним из значений
        valid_trends = ["INCREASING", "DECREASING", "STABLE"]
        assert trend in valid_trends, f"Trend should be one of {valid_trends}"
        print(f"✅ Trend: {trend}")
    
    def test_rolling_returns_change(self):
        """GET /api/correlation/rolling - должен вернуть change"""
        response = requests.get(f"{BASE_URL}/api/correlation/rolling", params={
            "asset_a": "BTC",
            "asset_b": "SPX"
        })
        assert response.status_code == 200
        
        data = response.json()
        change = data["change"]
        
        # Change должен содержать направление и значение
        assert "change" in change
        assert "direction" in change
        print(f"✅ Change: {change.get('change', 0):.4f}, direction: {change.get('direction')}")
    
    def test_rolling_returns_current_value(self):
        """GET /api/correlation/rolling - должен вернуть current_value"""
        response = requests.get(f"{BASE_URL}/api/correlation/rolling", params={
            "asset_a": "ETH",
            "asset_b": "BTC"
        })
        assert response.status_code == 200
        
        data = response.json()
        
        assert "current_value" in data
        assert isinstance(data["current_value"], (int, float))
        assert -1 <= data["current_value"] <= 1, "Correlation should be between -1 and 1"
        print(f"✅ ETH-BTC current_value: {data['current_value']:.4f}")


class TestLeadLag:
    """Lead/Lag relationship detection tests"""
    
    def test_lead_lag_spx_btc(self):
        """GET /api/correlation/lead-lag?asset_a=SPX&asset_b=BTC - должен вернуть leader"""
        response = requests.get(f"{BASE_URL}/api/correlation/lead-lag", params={
            "asset_a": "SPX",
            "asset_b": "BTC"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "leader" in data
        assert "follower" in data
        
        # Leader and follower should be one of the assets
        assert data["leader"] in ["SPX", "BTC"]
        assert data["follower"] in ["SPX", "BTC"]
        print(f"✅ Lead/Lag: {data['leader']} leads {data['follower']}")
    
    def test_lead_lag_returns_lag_candles(self):
        """GET /api/correlation/lead-lag - должен вернуть lag_candles"""
        response = requests.get(f"{BASE_URL}/api/correlation/lead-lag", params={
            "asset_a": "SPX",
            "asset_b": "BTC"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "lag_candles" in data
        assert isinstance(data["lag_candles"], int)
        assert data["lag_candles"] >= 0
        print(f"✅ Lag candles: {data['lag_candles']}")
    
    def test_lead_lag_returns_confidence(self):
        """GET /api/correlation/lead-lag - должен вернуть confidence"""
        response = requests.get(f"{BASE_URL}/api/correlation/lead-lag", params={
            "asset_a": "SPX",
            "asset_b": "BTC"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "confidence" in data
        assert 0 <= data["confidence"] <= 1, "Confidence should be between 0 and 1"
        print(f"✅ Confidence: {data['confidence']:.3f}")
    
    def test_lead_lag_returns_follower(self):
        """GET /api/correlation/lead-lag - должен вернуть follower"""
        response = requests.get(f"{BASE_URL}/api/correlation/lead-lag", params={
            "asset_a": "NASDAQ",
            "asset_b": "ETH"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "follower" in data
        assert data["follower"] in ["NASDAQ", "ETH"]
        print(f"✅ Follower: {data['follower']}")


class TestLeadLagAll:
    """Lead/Lag for all pairs endpoint tests"""
    
    def test_lead_lag_all_returns_results(self):
        """GET /api/correlation/lead-lag/all - должен вернуть результаты для всех пар"""
        response = requests.get(f"{BASE_URL}/api/correlation/lead-lag/all")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "pair_count" in data
        assert data["pair_count"] > 0
        print(f"✅ Lead/Lag all: {data['pair_count']} pairs analyzed")
    
    def test_lead_lag_all_returns_summary(self):
        """GET /api/correlation/lead-lag/all - должен вернуть summary"""
        response = requests.get(f"{BASE_URL}/api/correlation/lead-lag/all")
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        summary = data["summary"]
        
        # Summary должен содержать статистику
        assert "total_pairs" in summary or "valid_pairs" in summary
        print(f"✅ Summary: {summary}")
    
    def test_lead_lag_all_returns_leading_assets(self):
        """GET /api/correlation/lead-lag/all - должен вернуть leading_assets"""
        response = requests.get(f"{BASE_URL}/api/correlation/lead-lag/all")
        assert response.status_code == 200
        
        data = response.json()
        assert "leading_assets" in data
        
        # Leading assets should be a list
        leading_assets = data["leading_assets"]
        assert isinstance(leading_assets, list)
        print(f"✅ Leading assets: {[a.get('asset') for a in leading_assets[:3]]}")


class TestRegime:
    """Market regime classification tests"""
    
    def test_regime_classification(self):
        """GET /api/correlation/regime - должен классифицировать режим"""
        response = requests.get(f"{BASE_URL}/api/correlation/regime")
        assert response.status_code == 200
        
        data = response.json()
        assert "regime" in data
        
        # Regime должен быть одним из валидных значений
        valid_regimes = [
            "MACRO_DOMINANT", "CRYPTO_NATIVE", "RISK_ON", 
            "RISK_OFF", "DECOUPLING", "TRANSITIONING"
        ]
        assert data["regime"] in valid_regimes, f"Regime should be one of {valid_regimes}"
        print(f"✅ Current regime: {data['regime']}")
    
    def test_regime_returns_confidence(self):
        """GET /api/correlation/regime - должен вернуть confidence"""
        response = requests.get(f"{BASE_URL}/api/correlation/regime")
        assert response.status_code == 200
        
        data = response.json()
        assert "confidence" in data
        assert 0 <= data["confidence"] <= 1
        print(f"✅ Regime confidence: {data['confidence']:.3f}")
    
    def test_regime_returns_description(self):
        """GET /api/correlation/regime - должен вернуть description"""
        response = requests.get(f"{BASE_URL}/api/correlation/regime")
        assert response.status_code == 200
        
        data = response.json()
        assert "description" in data
        assert len(data["description"]) > 0
        print(f"✅ Description: {data['description'][:50]}...")
    
    def test_regime_returns_trading_implications(self):
        """GET /api/correlation/regime - должен вернуть trading_implications"""
        response = requests.get(f"{BASE_URL}/api/correlation/regime")
        assert response.status_code == 200
        
        data = response.json()
        assert "trading_implications" in data
        implications = data["trading_implications"]
        
        assert isinstance(implications, list)
        assert len(implications) > 0
        print(f"✅ Trading implications: {len(implications)} items")


class TestRegimeFavorable:
    """Regime favorability check tests"""
    
    def test_regime_favorable_long(self):
        """GET /api/correlation/regime/favorable?direction=LONG - должен проверить благоприятность для LONG"""
        response = requests.get(f"{BASE_URL}/api/correlation/regime/favorable", params={
            "direction": "LONG"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "direction" in data
        assert data["direction"] == "LONG"
        assert "favorable" in data
        assert "regime" in data
        print(f"✅ LONG favorable: {data['favorable']}, regime: {data['regime']}")
    
    def test_regime_favorable_short(self):
        """GET /api/correlation/regime/favorable?direction=SHORT - должен проверить благоприятность для SHORT"""
        response = requests.get(f"{BASE_URL}/api/correlation/regime/favorable", params={
            "direction": "SHORT"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["direction"] == "SHORT"
        assert "favorable" in data
        assert "reason" in data
        print(f"✅ SHORT favorable: {data['favorable']}, reason: {data['reason']}")


class TestSignals:
    """Cross-asset trading signals tests"""
    
    def test_signals_for_btc(self):
        """GET /api/correlation/signals?target_asset=BTC - должен вернуть cross-asset сигналы"""
        response = requests.get(f"{BASE_URL}/api/correlation/signals", params={
            "target_asset": "BTC"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "total_signals" in data
        assert "signals" in data
        print(f"✅ BTC signals: {data['total_signals']} total")
    
    def test_signals_returns_direction(self):
        """GET /api/correlation/signals - должен вернуть direction в сигналах"""
        response = requests.get(f"{BASE_URL}/api/correlation/signals", params={
            "target_asset": "BTC"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "net_direction" in data
        
        valid_directions = ["BULLISH", "BEARISH", "NEUTRAL"]
        assert data["net_direction"] in valid_directions
        print(f"✅ Net direction: {data['net_direction']}")
    
    def test_signals_returns_strength(self):
        """GET /api/correlation/signals - должен вернуть avg_strength"""
        response = requests.get(f"{BASE_URL}/api/correlation/signals", params={
            "target_asset": "BTC"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "avg_strength" in data
        
        # Strength should be 0-1
        if data["total_signals"] > 0:
            assert 0 <= data["avg_strength"] <= 1
        print(f"✅ Avg strength: {data['avg_strength']:.3f}")
    
    def test_signals_structure(self):
        """GET /api/correlation/signals - должен вернуть правильную структуру"""
        response = requests.get(f"{BASE_URL}/api/correlation/signals", params={
            "target_asset": "ETH",
            "min_strength": 0.2
        })
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields
        assert "total_signals" in data
        assert "net_direction" in data
        assert "avg_strength" in data
        assert "signals" in data
        assert "summary" in data
        assert "computed_at" in data
        
        print(f"✅ Signals structure valid, total: {data['total_signals']}")


class TestPairCorrelation:
    """Specific pair correlation analysis tests"""
    
    def test_btc_eth_pair(self):
        """GET /api/correlation/BTC/ETH - должен вернуть детальный анализ пары"""
        response = requests.get(f"{BASE_URL}/api/correlation/BTC/ETH")
        assert response.status_code == 200
        
        data = response.json()
        assert "pair" in data
        assert "correlation" in data
        assert "rolling" in data
        assert "lead_lag" in data
        print(f"✅ BTC-ETH pair analysis complete")
    
    def test_pair_returns_correlation_value(self):
        """GET /api/correlation/BTC/ETH - должен вернуть correlation value"""
        response = requests.get(f"{BASE_URL}/api/correlation/BTC/ETH")
        assert response.status_code == 200
        
        data = response.json()
        correlation = data["correlation"]
        
        assert "value" in correlation
        assert -1 <= correlation["value"] <= 1
        assert "strength" in correlation
        print(f"✅ BTC-ETH correlation: {correlation['value']:.4f}, strength: {correlation['strength']}")
    
    def test_pair_returns_rolling(self):
        """GET /api/correlation/BTC/ETH - должен вернуть rolling"""
        response = requests.get(f"{BASE_URL}/api/correlation/BTC/ETH")
        assert response.status_code == 200
        
        data = response.json()
        assert "rolling" in data
        
        rolling = data["rolling"]
        assert "current_value" in rolling
        assert "trend" in rolling
        print(f"✅ Rolling: current={rolling['current_value']:.4f}, trend={rolling['trend']}")
    
    def test_pair_returns_lead_lag(self):
        """GET /api/correlation/BTC/ETH - должен вернуть lead_lag"""
        response = requests.get(f"{BASE_URL}/api/correlation/BTC/ETH")
        assert response.status_code == 200
        
        data = response.json()
        assert "lead_lag" in data
        
        lead_lag = data["lead_lag"]
        assert "leader" in lead_lag
        assert "follower" in lead_lag
        print(f"✅ Lead/lag: {lead_lag['leader']} leads {lead_lag['follower']}")


class TestStats:
    """Repository and engine statistics tests"""
    
    def test_stats_returns_repository(self):
        """GET /api/correlation/stats - должен вернуть статистику репозитория"""
        response = requests.get(f"{BASE_URL}/api/correlation/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "repository" in data
        print(f"✅ Repository stats: {data['repository']}")
    
    def test_stats_returns_tracked_assets(self):
        """GET /api/correlation/stats - должен вернуть tracked assets"""
        response = requests.get(f"{BASE_URL}/api/correlation/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "tracked_assets" in data
        
        tracked = data["tracked_assets"]
        expected_assets = ["BTC", "ETH", "TOTAL", "SPX", "NASDAQ", "DXY", "GOLD", "US10Y"]
        
        for asset in expected_assets:
            assert asset in tracked, f"Asset {asset} should be tracked"
        
        print(f"✅ Tracked assets: {tracked}")
    
    def test_stats_returns_default_pairs(self):
        """GET /api/correlation/stats - должен вернуть default_pairs"""
        response = requests.get(f"{BASE_URL}/api/correlation/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "default_pairs" in data
        
        pairs = data["default_pairs"]
        assert isinstance(pairs, list)
        assert len(pairs) > 0
        
        # Check for some expected pairs
        assert "BTC_ETH" in pairs
        assert "BTC_SPX" in pairs
        print(f"✅ Default pairs: {len(pairs)} pairs, e.g., {pairs[:3]}")


class TestDataIntegrity:
    """Data integrity and consistency tests"""
    
    def test_correlation_values_in_range(self):
        """Verify all correlation values are between -1 and 1"""
        response = requests.get(f"{BASE_URL}/api/correlation/matrix")
        assert response.status_code == 200
        
        data = response.json()
        matrix = data.get("matrix", {})
        
        for pair_id, corr_data in matrix.items():
            value = corr_data.get("value", 0)
            assert -1 <= value <= 1, f"Correlation {pair_id} out of range: {value}"
        
        print(f"✅ All {len(matrix)} correlation values in valid range")
    
    def test_confidence_values_in_range(self):
        """Verify all confidence values are between 0 and 1"""
        response = requests.get(f"{BASE_URL}/api/correlation/lead-lag/all")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", {})
        
        for pair_id, result in results.items():
            confidence = result.get("confidence", 0)
            assert 0 <= confidence <= 1, f"Confidence {pair_id} out of range: {confidence}"
        
        print(f"✅ All {len(results)} confidence values in valid range")
    
    def test_timestamp_present(self):
        """Verify timestamps are present in responses"""
        endpoints = [
            "/api/correlation/health",
            "/api/correlation/matrix",
            "/api/correlation/regime",
            "/api/correlation/stats"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200
            data = response.json()
            
            # Check for timestamp field (various names)
            has_timestamp = any(key in data for key in ["timestamp", "computed_at", "retrieved_at", "checked_at"])
            assert has_timestamp, f"No timestamp in {endpoint}"
        
        print(f"✅ All {len(endpoints)} endpoints have timestamps")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
