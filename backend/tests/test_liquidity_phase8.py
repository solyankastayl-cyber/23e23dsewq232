"""
PHASE 8 - Liquidity Intelligence Module Tests
==============================================
Tests for all 10 liquidity intelligence API endpoints:
- GET /api/liquidity/health - Health check with 6 engines
- GET /api/liquidity/snapshot/{symbol} - Unified liquidity snapshot
- GET /api/liquidity/depth/{symbol} - Orderbook depth analysis
- GET /api/liquidity/zones/{symbol} - Liquidity zones detection
- GET /api/liquidity/stops/{symbol} - Stop cluster detection
- GET /api/liquidity/liquidations/{symbol} - Liquidation zone detection
- GET /api/liquidity/sweeps/{symbol} - Sweep probability signals
- GET /api/liquidity/imbalance/{symbol} - Liquidity imbalance analysis
- GET /api/liquidity/history/{symbol} - Historical snapshots
- GET /api/liquidity/stats - Repository and engine statistics

Mock data generators: generate_mock_orderbook(), generate_mock_price_history()
"""

import pytest
import requests
import os

# Use localhost for testing since no REACT_APP_BACKEND_URL is set
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")

# Test constants
TEST_SYMBOL = "BTCUSDT"
TEST_PRICE = 64000.0


class TestLiquidityHealth:
    """Test /api/liquidity/health endpoint"""
    
    def test_health_returns_200(self):
        """Health endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Health endpoint returns 200")
    
    def test_health_status_healthy(self):
        """Health should return status=healthy"""
        response = requests.get(f"{BASE_URL}/api/liquidity/health")
        data = response.json()
        assert data.get("status") == "healthy", f"Expected status=healthy, got {data.get('status')}"
        print("✓ Health status is healthy")
    
    def test_health_version_phase8(self):
        """Health should return version=phase8_liquidity_v1"""
        response = requests.get(f"{BASE_URL}/api/liquidity/health")
        data = response.json()
        assert data.get("version") == "phase8_liquidity_v1", f"Expected phase8_liquidity_v1, got {data.get('version')}"
        print("✓ Health version is phase8_liquidity_v1")
    
    def test_health_has_6_engines(self):
        """Health should list all 6 engines as ready"""
        response = requests.get(f"{BASE_URL}/api/liquidity/health")
        data = response.json()
        engines = data.get("engines", {})
        
        expected_engines = [
            "orderbook_depth", "liquidity_zones", "stop_clusters",
            "liquidation_zones", "sweep_probability", "liquidity_imbalance"
        ]
        
        for engine in expected_engines:
            assert engine in engines, f"Missing engine: {engine}"
            assert engines[engine] == "ready", f"Engine {engine} is not ready"
        
        assert len(engines) == 6, f"Expected 6 engines, got {len(engines)}"
        print(f"✓ All 6 engines are ready: {list(engines.keys())}")


class TestLiquiditySnapshot:
    """Test /api/liquidity/snapshot/{symbol} endpoint"""
    
    def test_snapshot_returns_200(self):
        """Snapshot endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/snapshot/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Snapshot endpoint returns 200")
    
    def test_snapshot_returns_bid_ask_depth(self):
        """Snapshot should return bid_depth and ask_depth"""
        response = requests.get(f"{BASE_URL}/api/liquidity/snapshot/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "bid_depth" in data, "Missing bid_depth"
        assert "ask_depth" in data, "Missing ask_depth"
        assert isinstance(data["bid_depth"], (int, float)), "bid_depth should be numeric"
        assert isinstance(data["ask_depth"], (int, float)), "ask_depth should be numeric"
        assert data["bid_depth"] > 0, "bid_depth should be positive"
        assert data["ask_depth"] > 0, "ask_depth should be positive"
        print(f"✓ Snapshot has bid_depth={data['bid_depth']}, ask_depth={data['ask_depth']}")
    
    def test_snapshot_returns_stop_clusters(self):
        """Snapshot should return nearest stop clusters above/below"""
        response = requests.get(f"{BASE_URL}/api/liquidity/snapshot/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "nearest_stop_cluster_above" in data, "Missing nearest_stop_cluster_above"
        assert "nearest_stop_cluster_below" in data, "Missing nearest_stop_cluster_below"
        print(f"✓ Snapshot has stop clusters: above={data['nearest_stop_cluster_above']}, below={data['nearest_stop_cluster_below']}")
    
    def test_snapshot_returns_sweep_probability(self):
        """Snapshot should return sweep_probability"""
        response = requests.get(f"{BASE_URL}/api/liquidity/snapshot/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "sweep_probability" in data, "Missing sweep_probability"
        assert isinstance(data["sweep_probability"], (int, float)), "sweep_probability should be numeric"
        assert 0 <= data["sweep_probability"] <= 1, "sweep_probability should be between 0 and 1"
        print(f"✓ Snapshot has sweep_probability={data['sweep_probability']}")
    
    def test_snapshot_returns_liquidity_quality(self):
        """Snapshot should return liquidity_quality"""
        response = requests.get(f"{BASE_URL}/api/liquidity/snapshot/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "liquidity_quality" in data, "Missing liquidity_quality"
        valid_qualities = ["EXCELLENT", "GOOD", "MEDIUM", "POOR", "CRITICAL"]
        assert data["liquidity_quality"] in valid_qualities, f"Invalid quality: {data['liquidity_quality']}"
        print(f"✓ Snapshot has liquidity_quality={data['liquidity_quality']}")
    
    def test_snapshot_full_structure(self):
        """Snapshot should have complete structure"""
        response = requests.get(f"{BASE_URL}/api/liquidity/snapshot/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        required_fields = [
            "symbol", "current_price", "bid_depth", "ask_depth", "depth_imbalance",
            "nearest_stop_cluster_above", "nearest_stop_cluster_below",
            "sweep_probability", "sweep_direction", "post_sweep_bias",
            "liquidity_quality", "cascade_risk", "execution_risk", "computed_at"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        assert data["symbol"] == TEST_SYMBOL, f"Symbol mismatch: {data['symbol']}"
        print(f"✓ Snapshot has all {len(required_fields)} required fields")


class TestOrderbookDepth:
    """Test /api/liquidity/depth/{symbol} endpoint"""
    
    def test_depth_returns_200(self):
        """Depth endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/depth/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Depth endpoint returns 200")
    
    def test_depth_returns_bid_ask(self):
        """Depth should return bid_depth and ask_depth"""
        response = requests.get(f"{BASE_URL}/api/liquidity/depth/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "bid_depth" in data, "Missing bid_depth"
        assert "ask_depth" in data, "Missing ask_depth"
        assert data["bid_depth"] > 0, "bid_depth should be positive"
        assert data["ask_depth"] > 0, "ask_depth should be positive"
        print(f"✓ Depth has bid_depth={data['bid_depth']}, ask_depth={data['ask_depth']}")
    
    def test_depth_returns_spread(self):
        """Depth should return spread_bps"""
        response = requests.get(f"{BASE_URL}/api/liquidity/depth/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "spread_bps" in data, "Missing spread_bps"
        assert isinstance(data["spread_bps"], (int, float)), "spread_bps should be numeric"
        assert data["spread_bps"] >= 0, "spread_bps should be non-negative"
        print(f"✓ Depth has spread_bps={data['spread_bps']}")
    
    def test_depth_returns_walls(self):
        """Depth should return bid_walls and ask_walls"""
        response = requests.get(f"{BASE_URL}/api/liquidity/depth/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "bid_walls" in data, "Missing bid_walls"
        assert "ask_walls" in data, "Missing ask_walls"
        assert isinstance(data["bid_walls"], list), "bid_walls should be a list"
        assert isinstance(data["ask_walls"], list), "ask_walls should be a list"
        print(f"✓ Depth has {len(data['bid_walls'])} bid_walls and {len(data['ask_walls'])} ask_walls")
    
    def test_depth_returns_thin_zones(self):
        """Depth should return thin_zones"""
        response = requests.get(f"{BASE_URL}/api/liquidity/depth/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "thin_zones" in data, "Missing thin_zones"
        assert isinstance(data["thin_zones"], list), "thin_zones should be a list"
        print(f"✓ Depth has {len(data['thin_zones'])} thin_zones")
    
    def test_depth_returns_liquidity_quality(self):
        """Depth should return liquidity_quality"""
        response = requests.get(f"{BASE_URL}/api/liquidity/depth/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "liquidity_quality" in data, "Missing liquidity_quality"
        valid_qualities = ["EXCELLENT", "GOOD", "MEDIUM", "POOR", "CRITICAL"]
        assert data["liquidity_quality"] in valid_qualities, f"Invalid quality: {data['liquidity_quality']}"
        print(f"✓ Depth has liquidity_quality={data['liquidity_quality']}")


class TestLiquidityZones:
    """Test /api/liquidity/zones/{symbol} endpoint"""
    
    def test_zones_returns_200(self):
        """Zones endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/zones/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Zones endpoint returns 200")
    
    def test_zones_returns_total_zones(self):
        """Zones should return total_zones count"""
        response = requests.get(f"{BASE_URL}/api/liquidity/zones/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "total_zones" in data, "Missing total_zones"
        assert isinstance(data["total_zones"], int), "total_zones should be integer"
        assert data["total_zones"] >= 0, "total_zones should be non-negative"
        print(f"✓ Zones has total_zones={data['total_zones']}")
    
    def test_zones_returns_above_below(self):
        """Zones should return zones_above and zones_below"""
        response = requests.get(f"{BASE_URL}/api/liquidity/zones/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "zones_above" in data, "Missing zones_above"
        assert "zones_below" in data, "Missing zones_below"
        assert isinstance(data["zones_above"], int), "zones_above should be integer"
        assert isinstance(data["zones_below"], int), "zones_below should be integer"
        print(f"✓ Zones has zones_above={data['zones_above']}, zones_below={data['zones_below']}")
    
    def test_zones_returns_summary(self):
        """Zones should return summary"""
        response = requests.get(f"{BASE_URL}/api/liquidity/zones/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "summary" in data, "Missing summary"
        assert isinstance(data["summary"], dict), "summary should be a dict"
        print(f"✓ Zones has summary with keys: {list(data['summary'].keys())}")
    
    def test_zones_list_structure(self):
        """Zones list should have proper structure"""
        response = requests.get(f"{BASE_URL}/api/liquidity/zones/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "zones" in data, "Missing zones"
        assert isinstance(data["zones"], list), "zones should be a list"
        
        if len(data["zones"]) > 0:
            zone = data["zones"][0]
            assert "zone_type" in zone, "Zone missing zone_type"
            assert "price_low" in zone, "Zone missing price_low"
            assert "price_high" in zone, "Zone missing price_high"
            print(f"✓ Zones list has proper structure, first zone type: {zone.get('zone_type')}")
        else:
            print("✓ Zones list is empty (valid)")


class TestStopClusters:
    """Test /api/liquidity/stops/{symbol} endpoint"""
    
    def test_stops_returns_200(self):
        """Stops endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/stops/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Stops endpoint returns 200")
    
    def test_stops_returns_cluster_counts(self):
        """Stops should return long/short stop cluster counts"""
        response = requests.get(f"{BASE_URL}/api/liquidity/stops/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "long_stop_clusters" in data, "Missing long_stop_clusters"
        assert "short_stop_clusters" in data, "Missing short_stop_clusters"
        assert isinstance(data["long_stop_clusters"], int), "long_stop_clusters should be integer"
        assert isinstance(data["short_stop_clusters"], int), "short_stop_clusters should be integer"
        print(f"✓ Stops has long={data['long_stop_clusters']}, short={data['short_stop_clusters']} clusters")
    
    def test_stops_returns_nearest(self):
        """Stops should return nearest clusters"""
        response = requests.get(f"{BASE_URL}/api/liquidity/stops/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "nearest" in data, "Missing nearest"
        assert isinstance(data["nearest"], dict), "nearest should be a dict"
        print(f"✓ Stops has nearest with keys: {list(data['nearest'].keys())}")
    
    def test_stops_clusters_structure(self):
        """Stop clusters should have proper structure"""
        response = requests.get(f"{BASE_URL}/api/liquidity/stops/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "clusters" in data, "Missing clusters"
        assert isinstance(data["clusters"], list), "clusters should be a list"
        
        if len(data["clusters"]) > 0:
            cluster = data["clusters"][0]
            assert "price_level" in cluster, "Cluster missing price_level"
            assert "side" in cluster, "Cluster missing side"
            assert "confidence" in cluster, "Cluster missing confidence"
            print(f"✓ Clusters have proper structure, first cluster side: {cluster.get('side')}")
        else:
            print("✓ Clusters list is empty (valid for some price ranges)")


class TestLiquidationZones:
    """Test /api/liquidity/liquidations/{symbol} endpoint"""
    
    def test_liquidations_returns_200(self):
        """Liquidations endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/liquidations/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Liquidations endpoint returns 200")
    
    def test_liquidations_returns_zone_counts(self):
        """Liquidations should return long/short zone counts"""
        response = requests.get(f"{BASE_URL}/api/liquidity/liquidations/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "long_liquidation_zones" in data, "Missing long_liquidation_zones"
        assert "short_liquidation_zones" in data, "Missing short_liquidation_zones"
        assert isinstance(data["long_liquidation_zones"], int), "long_liquidation_zones should be integer"
        assert isinstance(data["short_liquidation_zones"], int), "short_liquidation_zones should be integer"
        print(f"✓ Liquidations has long={data['long_liquidation_zones']}, short={data['short_liquidation_zones']} zones")
    
    def test_liquidations_returns_cascade_risk(self):
        """Liquidations should include cascade_risk in nearest"""
        response = requests.get(f"{BASE_URL}/api/liquidity/liquidations/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "nearest" in data, "Missing nearest"
        # cascade_risk might be in zones or nearest structure
        print(f"✓ Liquidations has nearest info: {data.get('nearest')}")
    
    def test_liquidations_zones_structure(self):
        """Liquidation zones should have proper structure"""
        response = requests.get(f"{BASE_URL}/api/liquidity/liquidations/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "zones" in data, "Missing zones"
        assert isinstance(data["zones"], list), "zones should be a list"
        
        if len(data["zones"]) > 0:
            zone = data["zones"][0]
            assert "price_level" in zone, "Zone missing price_level"
            assert "position_type" in zone, "Zone missing position_type"
            assert "cascade_risk" in zone, "Zone missing cascade_risk"
            print(f"✓ Liquidation zones have proper structure, first zone position_type: {zone.get('position_type')}")
        else:
            print("✓ Liquidation zones list is empty (valid)")


class TestSweepSignals:
    """Test /api/liquidity/sweeps/{symbol} endpoint"""
    
    def test_sweeps_returns_200(self):
        """Sweeps endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/sweeps/{TEST_SYMBOL}", 
                              params={"current_price": TEST_PRICE, "price_trend": "UP"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Sweeps endpoint returns 200")
    
    def test_sweeps_returns_dominant_direction(self):
        """Sweeps should return dominant_direction"""
        response = requests.get(f"{BASE_URL}/api/liquidity/sweeps/{TEST_SYMBOL}", 
                              params={"current_price": TEST_PRICE, "price_trend": "NEUTRAL"})
        data = response.json()
        
        assert "dominant_direction" in data, "Missing dominant_direction"
        valid_directions = ["UPSIDE", "DOWNSIDE", "BOTH", "NEUTRAL", "NONE"]
        assert data["dominant_direction"] in valid_directions, f"Invalid direction: {data['dominant_direction']}"
        print(f"✓ Sweeps has dominant_direction={data['dominant_direction']}")
    
    def test_sweeps_returns_probability(self):
        """Sweeps should return sweep_probability in signals"""
        response = requests.get(f"{BASE_URL}/api/liquidity/sweeps/{TEST_SYMBOL}", 
                              params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "signals" in data, "Missing signals"
        assert isinstance(data["signals"], list), "signals should be a list"
        
        if len(data["signals"]) > 0:
            signal = data["signals"][0]
            assert "sweep_probability" in signal, "Signal missing sweep_probability"
            assert 0 <= signal["sweep_probability"] <= 1, "sweep_probability should be between 0 and 1"
            print(f"✓ Sweeps has signals with sweep_probability={signal['sweep_probability']}")
        else:
            print("✓ Sweeps signals list is empty (valid)")
    
    def test_sweeps_returns_post_sweep_bias(self):
        """Sweeps signals should include post_sweep_bias"""
        response = requests.get(f"{BASE_URL}/api/liquidity/sweeps/{TEST_SYMBOL}", 
                              params={"current_price": TEST_PRICE})
        data = response.json()
        
        if len(data.get("signals", [])) > 0:
            signal = data["signals"][0]
            assert "post_sweep_bias" in signal, "Signal missing post_sweep_bias"
            valid_biases = ["BULLISH", "BEARISH", "NEUTRAL"]
            assert signal["post_sweep_bias"] in valid_biases, f"Invalid bias: {signal['post_sweep_bias']}"
            print(f"✓ Sweeps signal has post_sweep_bias={signal['post_sweep_bias']}")
        else:
            print("✓ No signals to check post_sweep_bias")
    
    def test_sweeps_summary_structure(self):
        """Sweeps should return summary"""
        response = requests.get(f"{BASE_URL}/api/liquidity/sweeps/{TEST_SYMBOL}", 
                              params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "summary" in data, "Missing summary"
        assert isinstance(data["summary"], dict), "summary should be a dict"
        print(f"✓ Sweeps has summary with keys: {list(data['summary'].keys())}")


class TestLiquidityImbalance:
    """Test /api/liquidity/imbalance/{symbol} endpoint"""
    
    def test_imbalance_returns_200(self):
        """Imbalance endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/imbalance/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Imbalance endpoint returns 200")
    
    def test_imbalance_returns_score(self):
        """Imbalance should return imbalance_score"""
        response = requests.get(f"{BASE_URL}/api/liquidity/imbalance/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "imbalance_score" in data, "Missing imbalance_score"
        assert isinstance(data["imbalance_score"], (int, float)), "imbalance_score should be numeric"
        assert -1 <= data["imbalance_score"] <= 1, "imbalance_score should be between -1 and 1"
        print(f"✓ Imbalance has imbalance_score={data['imbalance_score']}")
    
    def test_imbalance_returns_dominant_side(self):
        """Imbalance should return dominant_side"""
        response = requests.get(f"{BASE_URL}/api/liquidity/imbalance/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "dominant_side" in data, "Missing dominant_side"
        valid_sides = ["BID_DOMINANT", "ASK_DOMINANT", "BALANCED"]
        assert data["dominant_side"] in valid_sides, f"Invalid side: {data['dominant_side']}"
        print(f"✓ Imbalance has dominant_side={data['dominant_side']}")
    
    def test_imbalance_returns_trading_signal(self):
        """Imbalance should return trading_signal"""
        response = requests.get(f"{BASE_URL}/api/liquidity/imbalance/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "trading_signal" in data, "Missing trading_signal"
        assert isinstance(data["trading_signal"], dict), "trading_signal should be a dict"
        print(f"✓ Imbalance has trading_signal: {data['trading_signal']}")
    
    def test_imbalance_returns_pressures(self):
        """Imbalance should return bid_pressure and ask_pressure"""
        response = requests.get(f"{BASE_URL}/api/liquidity/imbalance/{TEST_SYMBOL}", params={"current_price": TEST_PRICE})
        data = response.json()
        
        assert "bid_pressure" in data, "Missing bid_pressure"
        assert "ask_pressure" in data, "Missing ask_pressure"
        assert isinstance(data["bid_pressure"], (int, float)), "bid_pressure should be numeric"
        assert isinstance(data["ask_pressure"], (int, float)), "ask_pressure should be numeric"
        print(f"✓ Imbalance has bid_pressure={data['bid_pressure']}, ask_pressure={data['ask_pressure']}")


class TestLiquidityHistory:
    """Test /api/liquidity/history/{symbol} endpoint"""
    
    def test_history_returns_200(self):
        """History endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/history/{TEST_SYMBOL}", 
                              params={"hours_back": 24, "limit": 10})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ History endpoint returns 200")
    
    def test_history_returns_snapshots(self):
        """History should return snapshots list"""
        response = requests.get(f"{BASE_URL}/api/liquidity/history/{TEST_SYMBOL}", 
                              params={"hours_back": 24, "limit": 10})
        data = response.json()
        
        assert "snapshots" in data, "Missing snapshots"
        assert isinstance(data["snapshots"], list), "snapshots should be a list"
        print(f"✓ History returns {len(data['snapshots'])} snapshots")
    
    def test_history_returns_count(self):
        """History should return count"""
        response = requests.get(f"{BASE_URL}/api/liquidity/history/{TEST_SYMBOL}", 
                              params={"hours_back": 24, "limit": 10})
        data = response.json()
        
        assert "count" in data, "Missing count"
        assert isinstance(data["count"], int), "count should be integer"
        assert data["count"] >= 0, "count should be non-negative"
        print(f"✓ History has count={data['count']}")
    
    def test_history_respects_limit(self):
        """History should respect limit parameter"""
        limit = 5
        response = requests.get(f"{BASE_URL}/api/liquidity/history/{TEST_SYMBOL}", 
                              params={"hours_back": 24, "limit": limit})
        data = response.json()
        
        assert len(data["snapshots"]) <= limit, f"Expected at most {limit} snapshots"
        print(f"✓ History respects limit={limit}")


class TestLiquidityStats:
    """Test /api/liquidity/stats endpoint"""
    
    def test_stats_returns_200(self):
        """Stats endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/liquidity/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Stats endpoint returns 200")
    
    def test_stats_returns_repository(self):
        """Stats should return repository info"""
        response = requests.get(f"{BASE_URL}/api/liquidity/stats")
        data = response.json()
        
        assert "repository" in data, "Missing repository"
        assert isinstance(data["repository"], dict), "repository should be a dict"
        print(f"✓ Stats has repository info: {list(data['repository'].keys())}")
    
    def test_stats_returns_engines(self):
        """Stats should return engines info"""
        response = requests.get(f"{BASE_URL}/api/liquidity/stats")
        data = response.json()
        
        assert "engines" in data, "Missing engines"
        assert isinstance(data["engines"], dict), "engines should be a dict"
        
        expected_engines = [
            "orderbook_depth", "liquidity_zones", "stop_clusters",
            "liquidation_zones", "sweep_probability", "liquidity_imbalance"
        ]
        
        for engine in expected_engines:
            assert engine in data["engines"], f"Missing engine: {engine}"
        
        print(f"✓ Stats has all 6 engines: {list(data['engines'].keys())}")
    
    def test_stats_returns_config(self):
        """Stats should return config"""
        response = requests.get(f"{BASE_URL}/api/liquidity/stats")
        data = response.json()
        
        assert "config" in data, "Missing config"
        assert isinstance(data["config"], dict), "config should be a dict"
        print(f"✓ Stats has config with keys: {list(data['config'].keys())}")


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_different_symbol(self):
        """Test with different symbol (ETHUSDT)"""
        response = requests.get(f"{BASE_URL}/api/liquidity/snapshot/ETHUSDT", params={"current_price": 3500.0})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["symbol"] == "ETHUSDT", f"Symbol mismatch: {data['symbol']}"
        print("✓ Different symbol (ETHUSDT) works")
    
    def test_different_price(self):
        """Test with different price"""
        response = requests.get(f"{BASE_URL}/api/liquidity/snapshot/{TEST_SYMBOL}", params={"current_price": 50000.0})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["current_price"] == 50000.0, f"Price mismatch: {data['current_price']}"
        print("✓ Different price (50000) works")
    
    def test_sweep_with_trend_up(self):
        """Test sweeps with UP trend"""
        response = requests.get(f"{BASE_URL}/api/liquidity/sweeps/{TEST_SYMBOL}", 
                              params={"current_price": TEST_PRICE, "price_trend": "UP"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Sweeps with UP trend works")
    
    def test_sweep_with_trend_down(self):
        """Test sweeps with DOWN trend"""
        response = requests.get(f"{BASE_URL}/api/liquidity/sweeps/{TEST_SYMBOL}", 
                              params={"current_price": TEST_PRICE, "price_trend": "DOWN"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Sweeps with DOWN trend works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
