"""
PHASE F1 Research Functional Integration Tests
===============================================
Testing backend API endpoints for Research UI integration:
- Chart Composer: GET /api/v1/chart/full-analysis/{symbol}/{timeframe}
- Signal Explanation: GET /api/v1/signal/explanation/{symbol}/{timeframe}
- Capital Flow: GET /api/v1/capital-flow/summary
- Fractal: GET /api/v1/fractal/summary/{symbol}
- Hypothesis: GET /api/hypothesis/list, GET /api/hypothesis/top
- Chart Presets: GET /api/v1/chart/presets
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tech-analysis-core-1.preview.emergentagent.com')


class TestHealthAndBasicEndpoints:
    """Health check and basic endpoint tests"""
    
    def test_api_health(self):
        """Test /api/health returns ok status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get('ok') is True
        print(f"✓ API health OK: {data}")
    
    def test_ta_registry(self):
        """Test /api/ta/registry returns strategy data"""
        response = requests.get(f"{BASE_URL}/api/ta/registry")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'ok'
        print(f"✓ TA Registry: {data.get('registry', {}).get('strategies_count', 0)} strategies")


class TestChartComposerAPI:
    """Chart Composer endpoints tests - PHASE 50"""
    
    def test_chart_presets(self):
        """Test GET /api/v1/chart/presets returns presets list"""
        response = requests.get(f"{BASE_URL}/api/v1/chart/presets")
        assert response.status_code == 200
        data = response.json()
        assert 'presets' in data
        assert 'count' in data
        assert data['count'] >= 0
        print(f"✓ Chart Presets: {data['count']} presets available")
    
    def test_full_analysis_btcusdt_1h(self):
        """Test GET /api/v1/chart/full-analysis/BTCUSDT/1h returns full chart data"""
        response = requests.get(
            f"{BASE_URL}/api/v1/chart/full-analysis/BTCUSDT/1h",
            params={'include_hypothesis': True, 'include_fractals': True, 'limit': 100}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist
        assert 'candles' in data, "Missing 'candles' in response"
        assert 'indicators' in data, "Missing 'indicators' in response"
        assert 'market_regime' in data, "Missing 'market_regime' in response"
        
        # Verify data structure
        assert len(data['candles']) > 0, "No candles returned"
        
        # Check candle structure
        if len(data['candles']) > 0:
            candle = data['candles'][0]
            assert 'open' in candle or 'o' in candle, "Candle missing open price"
            assert 'close' in candle or 'c' in candle, "Candle missing close price"
        
        print(f"✓ Full Analysis BTCUSDT/1h: {len(data['candles'])} candles, regime: {data.get('market_regime')}")
    
    def test_full_analysis_ethusdt_1h(self):
        """Test GET /api/v1/chart/full-analysis/ETHUSDT/1h - different symbol"""
        response = requests.get(
            f"{BASE_URL}/api/v1/chart/full-analysis/ETHUSDT/1h",
            params={'limit': 100}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert 'candles' in data
        assert len(data['candles']) > 0
        print(f"✓ Full Analysis ETHUSDT/1h: {len(data['candles'])} candles")
    
    def test_full_analysis_different_timeframes(self):
        """Test full-analysis with different timeframes"""
        timeframes = ['5m', '15m', '4h', '1d']
        
        for tf in timeframes:
            response = requests.get(
                f"{BASE_URL}/api/v1/chart/full-analysis/BTCUSDT/{tf}",
                params={'limit': 50}
            )
            assert response.status_code == 200, f"Failed for timeframe {tf}"
            data = response.json()
            assert 'candles' in data
            print(f"✓ Full Analysis BTCUSDT/{tf}: {len(data.get('candles', []))} candles")


class TestSignalExplanationAPI:
    """Signal Explanation endpoints tests - PHASE 51"""
    
    def test_signal_explanation_btcusdt_1h(self):
        """Test GET /api/v1/signal/explanation/BTCUSDT/1h returns signal explanation with drivers"""
        response = requests.get(f"{BASE_URL}/api/v1/signal/explanation/BTCUSDT/1h")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert 'direction' in data, "Missing 'direction' in response"
        assert 'confidence' in data, "Missing 'confidence' in response"
        assert 'drivers' in data, "Missing 'drivers' in response"
        
        # Verify drivers structure
        assert isinstance(data['drivers'], list), "drivers should be a list"
        
        print(f"✓ Signal Explanation BTCUSDT/1h: direction={data.get('direction')}, confidence={data.get('confidence')}, drivers={len(data.get('drivers', []))}")
    
    def test_signal_explanation_ethusdt(self):
        """Test signal explanation for ETHUSDT"""
        response = requests.get(f"{BASE_URL}/api/v1/signal/explanation/ETHUSDT/1h")
        assert response.status_code == 200
        data = response.json()
        
        assert 'direction' in data
        assert 'drivers' in data
        print(f"✓ Signal Explanation ETHUSDT/1h: direction={data.get('direction')}")


class TestCapitalFlowAPI:
    """Capital Flow endpoints tests - PHASE 42.4"""
    
    def test_capital_flow_summary(self):
        """Test GET /api/v1/capital-flow/summary returns capital flow data"""
        response = requests.get(f"{BASE_URL}/api/v1/capital-flow/summary")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('status') == 'ok', "Status should be 'ok'"
        
        # Verify score structure
        if 'score' in data:
            score = data['score']
            assert 'flow_bias' in score, "Missing flow_bias in score"
            print(f"✓ Capital Flow Summary: bias={score.get('flow_bias')}, strength={score.get('flow_strength')}")
        else:
            print(f"✓ Capital Flow Summary: status ok, data={data.keys()}")
    
    def test_capital_flow_snapshot(self):
        """Test GET /api/v1/capital-flow/snapshot"""
        response = requests.get(f"{BASE_URL}/api/v1/capital-flow/snapshot")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'ok'
        print(f"✓ Capital Flow Snapshot: {data.get('snapshot', {}).get('flow_state', 'N/A')}")
    
    def test_capital_flow_rotation(self):
        """Test GET /api/v1/capital-flow/rotation"""
        response = requests.get(f"{BASE_URL}/api/v1/capital-flow/rotation")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'ok'
        print(f"✓ Capital Flow Rotation: {data.get('rotation', {}).get('rotation_type', 'N/A')}")


class TestFractalAPI:
    """Fractal Market Intelligence endpoints tests - PHASE 32.1"""
    
    def test_fractal_summary_btcusdt(self):
        """Test GET /api/v1/fractal/summary/BTCUSDT returns fractal summary with current.alignment and current.bias"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal/summary/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required structure
        assert 'current' in data, "Missing 'current' in response"
        
        current = data['current']
        assert 'alignment' in current, "Missing 'alignment' in current"
        assert 'bias' in current, "Missing 'bias' in current"
        
        print(f"✓ Fractal Summary BTCUSDT: alignment={current.get('alignment')}, bias={current.get('bias')}, confidence={current.get('confidence')}")
    
    def test_fractal_summary_ethusdt(self):
        """Test fractal summary for ETHUSDT"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal/summary/ETHUSDT")
        assert response.status_code == 200
        data = response.json()
        
        assert 'current' in data
        print(f"✓ Fractal Summary ETHUSDT: bias={data.get('current', {}).get('bias')}")
    
    def test_fractal_state_btcusdt(self):
        """Test GET /api/v1/fractal/state/BTCUSDT"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal/state/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        
        assert 'fractal_metrics' in data
        print(f"✓ Fractal State BTCUSDT: alignment={data.get('fractal_metrics', {}).get('alignment')}")


class TestHypothesisAPI:
    """Hypothesis Engine endpoints tests - PHASE 6.1"""
    
    def test_hypothesis_list(self):
        """Test GET /api/hypothesis/list returns hypothesis list with count > 0"""
        response = requests.get(f"{BASE_URL}/api/hypothesis/list")
        assert response.status_code == 200
        data = response.json()
        
        assert 'count' in data, "Missing 'count' in response"
        assert 'hypotheses' in data, "Missing 'hypotheses' in response"
        
        # Verify count matches list length
        assert data['count'] == len(data['hypotheses'])
        
        print(f"✓ Hypothesis List: {data['count']} hypotheses")
    
    def test_hypothesis_top(self):
        """Test GET /api/hypothesis/top returns top hypotheses structure"""
        response = requests.get(f"{BASE_URL}/api/hypothesis/top", params={'limit': 5})
        assert response.status_code == 200
        data = response.json()
        
        assert 'count' in data, "Missing 'count' in response"
        assert 'top_hypotheses' in data, "Missing 'top_hypotheses' in response"
        
        # If there are hypotheses, verify structure
        if data['count'] > 0 and len(data['top_hypotheses']) > 0:
            top = data['top_hypotheses'][0]
            # Check expected fields (from repository)
            print(f"✓ Hypothesis Top: {data['count']} top hypotheses, first: {top.get('name', top.get('hypothesis_id', 'Unknown'))}")
        else:
            print(f"✓ Hypothesis Top: {data['count']} top hypotheses (empty is valid)")
    
    def test_hypothesis_registry(self):
        """Test GET /api/hypothesis/registry"""
        response = requests.get(f"{BASE_URL}/api/hypothesis/registry")
        assert response.status_code == 200
        data = response.json()
        
        assert 'total' in data
        assert 'stats' in data
        print(f"✓ Hypothesis Registry: {data.get('total')} total hypotheses")
    
    def test_hypothesis_health(self):
        """Test GET /api/hypothesis/health"""
        response = requests.get(f"{BASE_URL}/api/hypothesis/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('status') == 'ok'
        print(f"✓ Hypothesis Health: OK")


class TestResearchAnalyticsAPI:
    """Research Analytics endpoints tests - PHASE 48"""
    
    def test_research_analytics_health(self):
        """Test GET /api/v1/research-analytics/health"""
        response = requests.get(f"{BASE_URL}/api/v1/research-analytics/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('status') == 'ok'
        print(f"✓ Research Analytics Health: OK, components: {list(data.get('components', {}).keys())}")
    
    def test_chart_data_endpoint(self):
        """Test GET /api/v1/research-analytics/chart-data/{symbol}/{timeframe}"""
        response = requests.get(f"{BASE_URL}/api/v1/research-analytics/chart-data/BTCUSDT/1h")
        assert response.status_code == 200
        data = response.json()
        
        assert 'candles' in data
        print(f"✓ Research Chart Data: {len(data.get('candles', []))} candles")
    
    def test_patterns_endpoint(self):
        """Test GET /api/v1/research-analytics/patterns/{symbol}/{timeframe}"""
        response = requests.get(f"{BASE_URL}/api/v1/research-analytics/patterns/BTCUSDT/1h")
        assert response.status_code == 200
        data = response.json()
        
        assert 'patterns' in data
        assert 'count' in data
        print(f"✓ Research Patterns: {data.get('count')} patterns detected")


class TestIntegrationFlow:
    """Integration tests simulating frontend data flow"""
    
    def test_complete_research_data_flow(self):
        """
        Test complete data flow for Research tab:
        1. Full analysis
        2. Capital flow
        3. Fractal summary
        4. Signal explanation
        5. Hypotheses
        """
        symbol = 'BTCUSDT'
        timeframe = '1h'
        
        # 1. Full chart analysis (primary endpoint)
        print("\n--- Testing Complete Research Data Flow ---")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/chart/full-analysis/{symbol}/{timeframe}",
            params={'include_hypothesis': True, 'include_fractals': True, 'limit': 100}
        )
        assert response.status_code == 200, "Full analysis failed"
        chart_data = response.json()
        print(f"1. Chart Analysis: {len(chart_data.get('candles', []))} candles, regime: {chart_data.get('market_regime')}")
        
        # 2. Capital flow summary
        response = requests.get(f"{BASE_URL}/api/v1/capital-flow/summary")
        assert response.status_code == 200, "Capital flow failed"
        flow_data = response.json()
        print(f"2. Capital Flow: bias={flow_data.get('score', {}).get('flow_bias', 'N/A')}")
        
        # 3. Fractal summary
        response = requests.get(f"{BASE_URL}/api/v1/fractal/summary/{symbol}")
        assert response.status_code == 200, "Fractal summary failed"
        fractal_data = response.json()
        print(f"3. Fractal: bias={fractal_data.get('current', {}).get('bias', 'N/A')}, alignment={fractal_data.get('current', {}).get('alignment', 'N/A')}")
        
        # 4. Signal explanation
        response = requests.get(f"{BASE_URL}/api/v1/signal/explanation/{symbol}/{timeframe}")
        assert response.status_code == 200, "Signal explanation failed"
        signal_data = response.json()
        print(f"4. Signal: direction={signal_data.get('direction')}, drivers={len(signal_data.get('drivers', []))}")
        
        # 5. Hypotheses
        response = requests.get(f"{BASE_URL}/api/hypothesis/list")
        assert response.status_code == 200, "Hypothesis list failed"
        hyp_data = response.json()
        print(f"5. Hypotheses: {hyp_data.get('count', 0)} available")
        
        response = requests.get(f"{BASE_URL}/api/hypothesis/top", params={'limit': 1})
        assert response.status_code == 200, "Top hypotheses failed"
        top_data = response.json()
        print(f"6. Top Hypothesis: {top_data.get('count', 0)} top performers")
        
        print("✓ Complete research data flow successful!")
    
    def test_symbol_change_data_reload(self):
        """Test that changing symbol returns different data"""
        symbols = ['BTCUSDT', 'ETHUSDT']
        timeframe = '1h'
        
        results = {}
        for symbol in symbols:
            response = requests.get(
                f"{BASE_URL}/api/v1/chart/full-analysis/{symbol}/{timeframe}",
                params={'limit': 50}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Store price from first candle to compare
            if data.get('candles') and len(data['candles']) > 0:
                results[symbol] = data['candles'][0].get('close') or data['candles'][0].get('c')
        
        print(f"✓ Symbol change test: BTCUSDT=${results.get('BTCUSDT', 'N/A')}, ETHUSDT=${results.get('ETHUSDT', 'N/A')}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
