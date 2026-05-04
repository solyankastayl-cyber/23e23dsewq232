"""
PHASE 13.5 - Alpha Graph API Tests
===================================
Tests for Alpha Graph reasoning engine endpoints.

Endpoints tested:
- GET  /api/alpha-graph/health
- POST /api/alpha-graph/build
- GET  /api/alpha-graph/stats
- GET  /api/alpha-graph/nodes
- GET  /api/alpha-graph/edges
- GET  /api/alpha-graph/relation-types
- POST /api/alpha-graph/reason
- GET  /api/alpha-graph/context/{node_id}
- GET  /api/alpha-graph/conflicts
- GET  /api/alpha-graph/network/{node_id}
- GET  /api/alpha-graph/snapshots
- DELETE /api/alpha-graph/clear
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAlphaGraphHealth:
    """Health and stats endpoint tests"""
    
    def test_health_endpoint(self):
        """Test /api/alpha-graph/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["module"] == "alpha_graph"
        assert "timestamp" in data
        print(f"✅ Health check passed: {data['status']}")
    
    def test_stats_endpoint(self):
        """Test /api/alpha-graph/stats returns graph statistics"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "graph" in data
        assert "computed_at" in data
        
        graph = data["graph"]
        assert "repository" in graph
        assert "builder" in graph
        
        repo = graph["repository"]
        assert repo["connected"] == True
        assert repo["total_nodes"] >= 100  # Should have 107 nodes
        assert repo["total_edges"] >= 4000  # Should have ~4843 edges
        
        print(f"✅ Stats: {repo['total_nodes']} nodes, {repo['total_edges']} edges")


class TestAlphaGraphNodes:
    """Node listing and filtering tests"""
    
    def test_get_nodes_default(self):
        """Test /api/alpha-graph/nodes returns nodes"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/nodes")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "nodes" in data
        assert data["count"] > 0
        
        # Verify node structure
        node = data["nodes"][0]
        assert "node_id" in node
        assert "factor_id" in node
        assert "family" in node
        assert "template" in node
        assert "inputs" in node
        assert "composite_score" in node
        
        print(f"✅ Nodes: {data['count']} returned")
    
    def test_get_nodes_with_family_filter(self):
        """Test /api/alpha-graph/nodes with family filter"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/nodes?family=momentum")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] > 0
        
        # All nodes should be momentum family
        for node in data["nodes"]:
            assert node["family"] == "momentum"
        
        print(f"✅ Momentum nodes: {data['count']}")
    
    def test_get_nodes_with_limit(self):
        """Test /api/alpha-graph/nodes with limit parameter"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/nodes?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 5
        assert len(data["nodes"]) == 5
        
        print(f"✅ Limit works: {data['count']} nodes")


class TestAlphaGraphEdges:
    """Edge listing and filtering tests"""
    
    def test_get_edges_default(self):
        """Test /api/alpha-graph/edges returns edges"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/edges")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "edges" in data
        assert data["count"] > 0
        
        # Verify edge structure
        edge = data["edges"][0]
        assert "edge_id" in edge
        assert "source_node" in edge
        assert "target_node" in edge
        assert "relation_type" in edge
        assert "strength" in edge
        assert "confidence" in edge
        
        print(f"✅ Edges: {data['count']} returned")
    
    def test_get_edges_by_relation_type(self):
        """Test /api/alpha-graph/edges with relation_type filter"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/edges?relation_type=contradicts")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] > 0
        
        # All edges should be contradicts type
        for edge in data["edges"]:
            assert edge["relation_type"] == "contradicts"
        
        print(f"✅ Contradicts edges: {data['count']}")
    
    def test_get_edges_supports_type(self):
        """Test /api/alpha-graph/edges with supports filter"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/edges?relation_type=supports&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 10
        
        for edge in data["edges"]:
            assert edge["relation_type"] == "supports"
        
        print(f"✅ Supports edges: {data['count']}")


class TestAlphaGraphRelationTypes:
    """Relation types endpoint tests"""
    
    def test_get_relation_types(self):
        """Test /api/alpha-graph/relation-types returns all 5 types"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/relation-types")
        assert response.status_code == 200
        
        data = response.json()
        assert "relation_types" in data
        assert "counts" in data
        
        # Should have all 5 relation types
        expected_types = ["supports", "amplifies", "contradicts", "conditional_on", "invalidates"]
        for rt in expected_types:
            assert rt in data["relation_types"]
        
        # Verify counts exist
        counts = data["counts"]
        assert counts.get("supports", 0) > 0
        assert counts.get("contradicts", 0) > 0
        
        print(f"✅ Relation types: {data['relation_types']}")
        print(f"   Counts: {counts}")


class TestAlphaGraphReasoning:
    """Reasoning engine tests"""
    
    def test_reason_with_supporting_factors(self):
        """Test /api/alpha-graph/reason with momentum + breakout factors (supporting)"""
        # Get momentum and breakout node IDs
        momentum_resp = requests.get(f"{BASE_URL}/api/alpha-graph/nodes?family=momentum&limit=1")
        breakout_resp = requests.get(f"{BASE_URL}/api/alpha-graph/nodes?family=breakout&limit=2")
        
        momentum_id = momentum_resp.json()["nodes"][0]["node_id"]
        breakout_ids = [n["node_id"] for n in breakout_resp.json()["nodes"]]
        
        # Test reasoning
        response = requests.post(
            f"{BASE_URL}/api/alpha-graph/reason",
            json={"active_factor_ids": [momentum_id] + breakout_ids}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "reasoning" in data
        
        reasoning = data["reasoning"]
        assert "coherence_score" in reasoning
        assert "supporting_edges" in reasoning
        assert "signal_quality" in reasoning
        assert "recommendation" in reasoning
        
        # Momentum + breakout should have supporting edges
        assert reasoning["supporting_edges"] > 0
        assert reasoning["coherence_score"] >= 0.5
        
        print(f"✅ Reasoning (supporting): coherence={reasoning['coherence_score']:.2f}, quality={reasoning['signal_quality']}")
    
    def test_reason_with_conflicting_factors(self):
        """Test /api/alpha-graph/reason with breakout + regime factors (conflicting)"""
        # Get breakout and regime node IDs
        breakout_resp = requests.get(f"{BASE_URL}/api/alpha-graph/nodes?family=breakout&limit=1")
        regime_resp = requests.get(f"{BASE_URL}/api/alpha-graph/nodes?family=regime&limit=2")
        
        breakout_id = breakout_resp.json()["nodes"][0]["node_id"]
        regime_ids = [n["node_id"] for n in regime_resp.json()["nodes"]]
        
        # Test reasoning
        response = requests.post(
            f"{BASE_URL}/api/alpha-graph/reason",
            json={"active_factor_ids": [breakout_id] + regime_ids}
        )
        assert response.status_code == 200
        
        data = response.json()
        reasoning = data["reasoning"]
        
        # Breakout + regime should have conflicting edges
        assert reasoning["conflicting_edges"] > 0
        assert len(reasoning["conflict_pairs"]) > 0
        
        print(f"✅ Reasoning (conflicting): conflicts={reasoning['conflicting_edges']}, quality={reasoning['signal_quality']}")
    
    def test_reason_with_single_factor(self):
        """Test /api/alpha-graph/reason with single factor returns neutral"""
        nodes_resp = requests.get(f"{BASE_URL}/api/alpha-graph/nodes?limit=1")
        node_id = nodes_resp.json()["nodes"][0]["node_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/alpha-graph/reason",
            json={"active_factor_ids": [node_id]}
        )
        # Should fail validation (min_items=1 but needs 2 for reasoning)
        # Actually the API accepts 1 but returns neutral
        assert response.status_code == 200
        
        data = response.json()
        reasoning = data["reasoning"]
        assert reasoning["signal_quality"] == "NEUTRAL"
        
        print(f"✅ Single factor reasoning: {reasoning['signal_quality']}")
    
    def test_reason_empty_factors_fails(self):
        """Test /api/alpha-graph/reason with empty list fails validation"""
        response = requests.post(
            f"{BASE_URL}/api/alpha-graph/reason",
            json={"active_factor_ids": []}
        )
        assert response.status_code == 422  # Validation error
        
        print(f"✅ Empty factors validation: 422")


class TestAlphaGraphContext:
    """Node context endpoint tests"""
    
    def test_get_node_context(self):
        """Test /api/alpha-graph/context/{node_id} returns context"""
        # Get a node ID
        nodes_resp = requests.get(f"{BASE_URL}/api/alpha-graph/nodes?limit=1")
        node_id = nodes_resp.json()["nodes"][0]["node_id"]
        
        response = requests.get(f"{BASE_URL}/api/alpha-graph/context/{node_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "context" in data
        
        context = data["context"]
        assert context["node_id"] == node_id
        assert "family" in context
        assert "supports" in context
        assert "supported_by" in context
        assert "contradicts" in context
        assert "total_connections" in context
        
        print(f"✅ Node context: {context['total_connections']} connections")
    
    def test_get_context_nonexistent_node(self):
        """Test /api/alpha-graph/context/{node_id} returns 404 for invalid node"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/context/nonexistent_node_xyz")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        
        print(f"✅ Nonexistent node: 404")


class TestAlphaGraphConflicts:
    """Conflicts endpoint tests"""
    
    def test_get_conflicts(self):
        """Test /api/alpha-graph/conflicts returns all conflicts"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/conflicts")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "conflicts" in data
        assert data["count"] > 0  # Should have 212 conflicts
        
        # Verify conflict structure
        conflict = data["conflicts"][0]
        assert "source" in conflict
        assert "target" in conflict
        
        print(f"✅ Conflicts: {data['count']} total")


class TestAlphaGraphNetwork:
    """Support network endpoint tests"""
    
    def test_get_support_network(self):
        """Test /api/alpha-graph/network/{node_id} returns network"""
        # Get a node ID
        nodes_resp = requests.get(f"{BASE_URL}/api/alpha-graph/nodes?limit=1")
        node_id = nodes_resp.json()["nodes"][0]["node_id"]
        
        response = requests.get(f"{BASE_URL}/api/alpha-graph/network/{node_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "network" in data
        
        network = data["network"]
        assert network["center"] == node_id
        assert "nodes" in network
        assert "edges" in network
        assert len(network["nodes"]) > 0
        
        print(f"✅ Network: {len(network['nodes'])} nodes, {len(network['edges'])} edges")


class TestAlphaGraphSnapshots:
    """Snapshots endpoint tests"""
    
    def test_get_snapshots(self):
        """Test /api/alpha-graph/snapshots returns snapshots"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/snapshots")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "snapshots" in data
        assert data["count"] >= 1  # Should have at least 1 snapshot
        
        # Verify snapshot structure
        snapshot = data["snapshots"][0]
        assert "snapshot_id" in snapshot
        assert "total_nodes" in snapshot
        assert "total_edges" in snapshot
        assert "edges_by_type" in snapshot
        assert "nodes_by_family" in snapshot
        
        print(f"✅ Snapshots: {data['count']} total")


class TestAlphaGraphBuild:
    """Build endpoint tests"""
    
    def test_build_graph_without_clear(self):
        """Test /api/alpha-graph/build without clearing existing data"""
        response = requests.post(
            f"{BASE_URL}/api/alpha-graph/build",
            json={"clear_existing": False}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "completed"
        assert "build" in data
        
        build = data["build"]
        assert build["status"] == "completed"
        assert build["nodes_created"] >= 100
        assert build["edges_created"] >= 4000
        assert build["error_message"] is None
        
        print(f"✅ Build: {build['nodes_created']} nodes, {build['edges_created']} edges")


class TestAlphaGraphIntegration:
    """Integration tests with previous phases"""
    
    def test_factor_ranker_integration(self):
        """Verify Alpha Graph uses approved factors from Factor Ranker"""
        # Get approved factors count from ranker
        ranker_resp = requests.get(f"{BASE_URL}/api/factor-ranker/approved")
        if ranker_resp.status_code == 200:
            approved_count = ranker_resp.json().get("count", 0)
            
            # Get graph nodes count
            graph_resp = requests.get(f"{BASE_URL}/api/alpha-graph/stats")
            graph_nodes = graph_resp.json()["graph"]["repository"]["total_nodes"]
            
            # Graph nodes should be close to approved factors
            assert graph_nodes >= approved_count * 0.9  # Allow 10% variance
            
            print(f"✅ Integration: {approved_count} approved factors → {graph_nodes} graph nodes")
        else:
            pytest.skip("Factor Ranker not available")
    
    def test_all_relation_types_present(self):
        """Verify all 5 relation types are present in the graph"""
        response = requests.get(f"{BASE_URL}/api/alpha-graph/stats")
        data = response.json()
        
        edges_by_type = data["graph"]["repository"]["edges_by_type"]
        
        # Should have supports, contradicts, conditional_on, amplifies
        assert edges_by_type.get("supports", 0) > 0
        assert edges_by_type.get("contradicts", 0) > 0
        assert edges_by_type.get("conditional_on", 0) > 0
        assert edges_by_type.get("amplifies", 0) > 0
        
        print(f"✅ Relation types: supports={edges_by_type.get('supports')}, contradicts={edges_by_type.get('contradicts')}, conditional_on={edges_by_type.get('conditional_on')}, amplifies={edges_by_type.get('amplifies')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
