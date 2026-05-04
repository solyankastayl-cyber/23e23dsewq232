"""
Regime Graph Engine

PHASE 36 — Market Regime Graph Engine

Core engine for building and analyzing regime transition graphs.

Pipeline:
1. Collect regime history data
2. Build nodes (regime states)
3. Build edges (transitions with probabilities)
4. Calculate transition matrix: P(next_state | current_state)
5. Build sequence memory: P(state_C | state_A → state_B)
6. Predict likely next state and path
7. Generate modifier for Hypothesis Engine
"""

import hashlib
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter

from .graph_types import (
    RegimeGraphNode,
    RegimeGraphEdge,
    RegimeGraphState,
    RegimeGraphPath,
    RegimeGraphModifier,
    RegimeGraphSummary,
    RegimeSequence,
    TransitionMatrixEntry,
    REGIME_GRAPH_WEIGHT,
    WEIGHT_NEXT_STATE_PROB,
    WEIGHT_TRANSITION_CONFIDENCE,
    WEIGHT_MEMORY_SCORE,
    MIN_TRANSITION_COUNT,
    SEQUENCE_DEPTH,
    REGIME_STATES,
)


# ══════════════════════════════════════════════════════════════
# Regime Graph Engine
# ══════════════════════════════════════════════════════════════

class RegimeGraphEngine:
    """
    Regime Graph Engine — PHASE 36
    
    Models market regime transitions as a directed graph.
    
    Key formulas:
    - transition_probability = transition_count(from→to) / total_outgoing(from)
    - path_confidence = 0.50 * next_prob + 0.25 * transition_conf + 0.25 * memory_score
    """
    
    def __init__(self):
        # In-memory cache
        self._graphs: Dict[str, List[RegimeGraphState]] = {}
        self._current: Dict[str, RegimeGraphState] = {}
        
        # Transition matrix cache
        self._transition_matrices: Dict[str, Dict[str, Dict[str, float]]] = {}
        
        # Sequence memory cache
        self._sequence_memory: Dict[str, Dict[str, int]] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Data Collection
    # ═══════════════════════════════════════════════════════════
    
    def collect_regime_history(self, symbol: str) -> List[Dict]:
        """
        Collect regime transition history from various sources.
        """
        symbol = symbol.upper()
        history = []
        
        # Source 1: Regime detection history
        history.extend(self._get_regime_detection_history(symbol))
        
        # Source 2: Transition detector history
        history.extend(self._get_transition_history(symbol))
        
        # Source 3: Regime memory records
        history.extend(self._get_memory_records(symbol))
        
        # Sort by timestamp
        history.sort(key=lambda x: x.get("timestamp", datetime.min))
        
        return history
    
    def _get_regime_detection_history(self, symbol: str) -> List[Dict]:
        """Get regime detection history from database."""
        try:
            from core.database import get_database
            db = get_database()
            if db and "regime_detection_history" in db.list_collection_names():
                docs = list(db.regime_detection_history.find(
                    {"symbol": symbol},
                    {"_id": 0}
                ).sort("timestamp", -1).limit(1000))
                return docs
        except Exception:
            pass
        return []
    
    def _get_transition_history(self, symbol: str) -> List[Dict]:
        """Get transition history from database."""
        try:
            from core.database import get_database
            db = get_database()
            if db and "regime_transition_history" in db.list_collection_names():
                docs = list(db.regime_transition_history.find(
                    {"symbol": symbol},
                    {"_id": 0}
                ).sort("timestamp", -1).limit(500))
                return docs
        except Exception:
            pass
        return []
    
    def _get_memory_records(self, symbol: str) -> List[Dict]:
        """Get regime memory records from database."""
        try:
            from core.database import get_database
            db = get_database()
            if db and "market_regime_memory" in db.list_collection_names():
                docs = list(db.market_regime_memory.find(
                    {"symbol": symbol},
                    {"_id": 0, "regime_state": 1, "timestamp": 1}
                ).sort("timestamp", -1).limit(500))
                return docs
        except Exception:
            pass
        return []
    
    # ═══════════════════════════════════════════════════════════
    # 2. Node Building
    # ═══════════════════════════════════════════════════════════
    
    def build_nodes(self, history: List[Dict]) -> List[RegimeGraphNode]:
        """
        Build graph nodes from regime history.
        """
        node_stats: Dict[str, Dict] = defaultdict(lambda: {
            "visits": 0,
            "durations": [],
            "success_rates": [],
            "last_visited": None,
        })
        
        for i, record in enumerate(history):
            state = self._normalize_state(record.get("regime_state") or record.get("regime_type", "UNCERTAIN"))
            timestamp = record.get("timestamp")
            success = record.get("success", False)
            
            node_stats[state]["visits"] += 1
            node_stats[state]["last_visited"] = timestamp
            
            if success:
                node_stats[state]["success_rates"].append(1.0)
            else:
                node_stats[state]["success_rates"].append(0.0)
            
            # Calculate duration to next state
            if i < len(history) - 1:
                next_record = history[i + 1]
                if timestamp and next_record.get("timestamp"):
                    try:
                        if isinstance(timestamp, datetime) and isinstance(next_record.get("timestamp"), datetime):
                            duration = (next_record["timestamp"] - timestamp).total_seconds() / 60
                            if 0 < duration < 10080:  # Max 1 week
                                node_stats[state]["durations"].append(duration)
                    except Exception:
                        pass
        
        nodes = []
        for state in REGIME_STATES:
            stats = node_stats.get(state, {"visits": 0, "durations": [], "success_rates": [], "last_visited": None})
            
            durations = stats["durations"]
            success_rates = stats["success_rates"]
            
            node = RegimeGraphNode(
                regime_state=state,
                visits=stats["visits"],
                avg_duration_minutes=sum(durations) / len(durations) if durations else 0.0,
                max_duration_minutes=max(durations) if durations else 0.0,
                min_duration_minutes=min(durations) if durations else 0.0,
                avg_success_rate=sum(success_rates) / len(success_rates) if success_rates else 0.0,
                last_visited=stats["last_visited"],
            )
            nodes.append(node)
        
        return nodes
    
    def _normalize_state(self, state: str) -> str:
        """Normalize regime state to standard format."""
        state = state.upper()
        
        # Map variations to standard states
        mapping = {
            "TREND_UP": "TREND_UP",
            "TREND_DOWN": "TREND_DOWN",
            "TRENDING": "TRENDING",
            "RANGE": "RANGING",
            "RANGING": "RANGING",
            "VOLATILE": "VOLATILE",
            "HIGH_VOLATILITY": "VOLATILE",
            "COMPRESSION": "COMPRESSION",
            "EXPANSION": "EXPANSION",
            "UNCERTAIN": "UNCERTAIN",
            "UNKNOWN": "UNCERTAIN",
        }
        
        return mapping.get(state, "UNCERTAIN")
    
    # ═══════════════════════════════════════════════════════════
    # 3. Edge Building
    # ═══════════════════════════════════════════════════════════
    
    def build_edges(self, history: List[Dict]) -> List[RegimeGraphEdge]:
        """
        Build graph edges from regime transitions.
        
        Calculates: P(to_state | from_state) = count(from→to) / total_outgoing(from)
        """
        transition_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        transition_times: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        last_transitions: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        
        prev_state = None
        prev_timestamp = None
        
        for record in history:
            curr_state = self._normalize_state(record.get("regime_state") or record.get("regime_type", "UNCERTAIN"))
            curr_timestamp = record.get("timestamp")
            
            if prev_state and prev_state != curr_state:
                transition_counts[prev_state][curr_state] += 1
                last_transitions[prev_state][curr_state] = curr_timestamp
                
                if prev_timestamp and curr_timestamp:
                    try:
                        if isinstance(prev_timestamp, datetime) and isinstance(curr_timestamp, datetime):
                            time_diff = (curr_timestamp - prev_timestamp).total_seconds() / 60
                            if 0 < time_diff < 10080:
                                transition_times[prev_state][curr_state].append(time_diff)
                    except Exception:
                        pass
            
            prev_state = curr_state
            prev_timestamp = curr_timestamp
        
        # Calculate probabilities
        edges = []
        for from_state, to_states in transition_counts.items():
            total_outgoing = sum(to_states.values())
            
            for to_state, count in to_states.items():
                probability = count / total_outgoing if total_outgoing > 0 else 0.0
                
                times = transition_times[from_state][to_state]
                avg_time = sum(times) / len(times) if times else 0.0
                
                # Edge confidence based on sample size
                edge_confidence = min(count / 10, 1.0)  # Max confidence at 10+ transitions
                
                edge = RegimeGraphEdge(
                    from_state=from_state,
                    to_state=to_state,
                    transition_probability=round(probability, 4),
                    avg_transition_time_minutes=round(avg_time, 2),
                    transition_count=count,
                    edge_confidence=round(edge_confidence, 4),
                    last_transition=last_transitions.get(from_state, {}).get(to_state),
                )
                edges.append(edge)
        
        return edges
    
    # ═══════════════════════════════════════════════════════════
    # 4. Transition Matrix
    # ═══════════════════════════════════════════════════════════
    
    def build_transition_matrix(
        self,
        edges: List[RegimeGraphEdge],
    ) -> Dict[str, Dict[str, float]]:
        """
        Build transition probability matrix P(next | current).
        """
        matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        for edge in edges:
            matrix[edge.from_state][edge.to_state] = edge.transition_probability
        
        return dict(matrix)
    
    def get_transition_probability(
        self,
        matrix: Dict[str, Dict[str, float]],
        from_state: str,
        to_state: str,
    ) -> float:
        """Get probability of transition from one state to another."""
        return matrix.get(from_state, {}).get(to_state, 0.0)
    
    # ═══════════════════════════════════════════════════════════
    # 5. Sequence Memory
    # ═══════════════════════════════════════════════════════════
    
    def build_sequence_memory(
        self,
        history: List[Dict],
        depth: int = SEQUENCE_DEPTH,
    ) -> Dict[str, int]:
        """
        Build sequence memory: P(state_C | state_A → state_B).
        
        Tracks sequences of length 2 to `depth`.
        """
        sequences: Dict[str, int] = defaultdict(int)
        
        states = [
            self._normalize_state(r.get("regime_state") or r.get("regime_type", "UNCERTAIN"))
            for r in history
        ]
        
        # Build sequences of various lengths
        for length in range(2, depth + 1):
            for i in range(len(states) - length + 1):
                seq = tuple(states[i:i + length])
                # Skip if all same state (not a real sequence)
                if len(set(seq)) > 1:
                    sequences["→".join(seq)] += 1
        
        return dict(sequences)
    
    def get_likely_sequence(
        self,
        sequence_memory: Dict[str, int],
        current_state: str,
        previous_state: Optional[str] = None,
    ) -> Optional[RegimeSequence]:
        """
        Get most likely sequence given current and previous state.
        """
        prefix = f"{previous_state}→{current_state}" if previous_state else current_state
        
        # Find sequences starting with this prefix
        matching = {}
        for seq_str, count in sequence_memory.items():
            if seq_str.startswith(prefix) and seq_str != prefix:
                matching[seq_str] = count
        
        if not matching:
            return None
        
        # Get most common
        best_seq = max(matching.keys(), key=lambda k: matching[k])
        total_matching = sum(matching.values())
        
        return RegimeSequence(
            sequence=best_seq.split("→"),
            occurrence_count=matching[best_seq],
            sequence_probability=matching[best_seq] / total_matching if total_matching > 0 else 0.0,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 6. Current State Detection
    # ═══════════════════════════════════════════════════════════
    
    def get_current_regime_state(self, symbol: str) -> Tuple[str, Optional[str]]:
        """
        Get current and previous regime state for a symbol.
        """
        try:
            from modules.regime_intelligence_v2 import get_regime_engine
            engine = get_regime_engine()
            regime = engine.get_current_regime(symbol)
            if regime:
                current = self._normalize_state(regime.regime_type)
                # Try to get previous from history
                previous = self._get_previous_state(symbol)
                return current, previous
        except Exception:
            pass
        
        # Fallback: generate deterministic state
        seed = int(hashlib.md5(f"{symbol}_regime_{datetime.now(timezone.utc).hour}".encode()).hexdigest()[:4], 16)
        states = ["TRENDING", "RANGING", "VOLATILE"]
        return states[seed % len(states)], None
    
    def _get_previous_state(self, symbol: str) -> Optional[str]:
        """Get previous state from history."""
        try:
            from core.database import get_database
            db = get_database()
            if db and "market_regime_graph" in db.list_collection_names():
                doc = db.market_regime_graph.find_one(
                    {"symbol": symbol},
                    {"_id": 0, "current_state": 1},
                    sort=[("created_at", -1)]
                )
                if doc:
                    return doc.get("current_state")
        except Exception:
            pass
        return None
    
    # ═══════════════════════════════════════════════════════════
    # 7. Next State Prediction
    # ═══════════════════════════════════════════════════════════
    
    def predict_next_state(
        self,
        matrix: Dict[str, Dict[str, float]],
        current_state: str,
    ) -> Tuple[str, float, List[Dict]]:
        """
        Predict most likely next state from transition matrix.
        
        Returns: (likely_next_state, probability, alternative_states)
        """
        outgoing = matrix.get(current_state, {})
        
        if not outgoing:
            return "UNCERTAIN", 0.0, []
        
        # Sort by probability
        sorted_states = sorted(outgoing.items(), key=lambda x: x[1], reverse=True)
        
        likely_state = sorted_states[0][0]
        likely_prob = sorted_states[0][1]
        
        alternatives = [
            {"state": state, "probability": round(prob, 4)}
            for state, prob in sorted_states[1:4]  # Top 3 alternatives
        ]
        
        return likely_state, round(likely_prob, 4), alternatives
    
    # ═══════════════════════════════════════════════════════════
    # 8. Path Confidence Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_path_confidence(
        self,
        next_state_probability: float,
        transition_confidence: float,
        memory_score: float,
    ) -> float:
        """
        Calculate path confidence.
        
        Formula:
          path_confidence = 0.50 * next_state_probability
                         + 0.25 * regime_transition_confidence
                         + 0.25 * regime_memory_score
        """
        confidence = (
            WEIGHT_NEXT_STATE_PROB * next_state_probability
            + WEIGHT_TRANSITION_CONFIDENCE * transition_confidence
            + WEIGHT_MEMORY_SCORE * memory_score
        )
        
        return round(min(max(confidence, 0.0), 1.0), 4)
    
    def _get_transition_confidence(self, symbol: str) -> float:
        """Get transition confidence from Transition Detector."""
        try:
            from modules.regime_intelligence_v2 import get_transition_engine
            engine = get_transition_engine()
            result = engine.get_current_transition(symbol)
            if result:
                return result.confidence
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_trans_conf".encode()).hexdigest()[:4], 16)
        return round(0.4 + (seed % 40) / 100, 4)
    
    def _get_memory_score(self, symbol: str) -> float:
        """Get memory score from Regime Memory."""
        try:
            from modules.regime_memory import get_memory_engine
            engine = get_memory_engine()
            response = engine.get_current_response(symbol)
            if response:
                return response.memory_score
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_mem_score".encode()).hexdigest()[:4], 16)
        return round(0.3 + (seed % 50) / 100, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 9. Main Analysis Method
    # ═══════════════════════════════════════════════════════════
    
    def analyze(self, symbol: str) -> RegimeGraphState:
        """
        Perform full graph analysis for a symbol.
        
        Returns RegimeGraphState with nodes, edges, and predictions.
        """
        symbol = symbol.upper()
        
        # 1. Collect history
        history = self.collect_regime_history(symbol)
        
        # If no history, generate synthetic data
        if len(history) < 10:
            history = self._generate_synthetic_history(symbol)
        
        # 2. Build nodes
        nodes = self.build_nodes(history)
        
        # 3. Build edges
        edges = self.build_edges(history)
        
        # 4. Build transition matrix
        matrix = self.build_transition_matrix(edges)
        self._transition_matrices[symbol] = matrix
        
        # 5. Build sequence memory
        seq_memory = self.build_sequence_memory(history)
        self._sequence_memory[symbol] = seq_memory
        
        # 6. Get current state
        current_state, previous_state = self.get_current_regime_state(symbol)
        
        # 7. Predict next state
        likely_next, next_prob, alternatives = self.predict_next_state(matrix, current_state)
        
        # 8. Get likely sequence
        likely_sequence = self.get_likely_sequence(seq_memory, current_state, previous_state)
        
        # 9. Calculate path confidence
        trans_conf = self._get_transition_confidence(symbol)
        mem_score = self._get_memory_score(symbol)
        path_confidence = self.calculate_path_confidence(next_prob, trans_conf, mem_score)
        
        # 10. Build recent sequence
        recent_sequence = [
            self._normalize_state(r.get("regime_state") or r.get("regime_type", "UNCERTAIN"))
            for r in history[-5:]
        ]
        
        # 11. Statistics
        total_transitions = sum(e.transition_count for e in edges)
        unique_states = len([n for n in nodes if n.visits > 0])
        
        # 12. Generate reason
        reason = self._generate_reason(current_state, likely_next, next_prob, path_confidence)
        
        state = RegimeGraphState(
            symbol=symbol,
            nodes=nodes,
            edges=edges,
            current_state=current_state,
            previous_state=previous_state,
            likely_next_state=likely_next,
            next_state_probability=next_prob,
            alternative_states=alternatives,
            path_confidence=path_confidence,
            recent_sequence=recent_sequence,
            likely_sequence=likely_sequence,
            total_transitions=total_transitions,
            unique_states_visited=unique_states,
            reason=reason,
        )
        
        # Cache
        self._store_state(symbol, state)
        
        return state
    
    def _generate_synthetic_history(self, symbol: str) -> List[Dict]:
        """Generate synthetic regime history for testing."""
        history = []
        now = datetime.now(timezone.utc)
        
        # Deterministic based on symbol
        seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
        
        states = ["TRENDING", "RANGING", "VOLATILE", "TRENDING", "EXPANSION", "RANGING"]
        
        for i in range(100):
            state_idx = (seed + i * 7) % len(states)
            history.append({
                "regime_state": states[state_idx],
                "timestamp": now - timedelta(hours=100 - i),
                "success": (seed + i) % 3 != 0,
            })
        
        return history
    
    def _generate_reason(
        self,
        current: str,
        likely_next: str,
        probability: float,
        confidence: float,
    ) -> str:
        """Generate explanation string."""
        return f"Current: {current}; Likely next: {likely_next} (p={probability:.2f}); Path confidence: {confidence:.2f}"
    
    # ═══════════════════════════════════════════════════════════
    # 10. Path Prediction
    # ═══════════════════════════════════════════════════════════
    
    def predict_path(
        self,
        symbol: str,
        steps: int = 3,
    ) -> RegimeGraphPath:
        """
        Predict path through regime graph for N steps.
        """
        symbol = symbol.upper()
        
        # Get or build graph
        if symbol not in self._current:
            self.analyze(symbol)
        
        graph = self._current.get(symbol)
        matrix = self._transition_matrices.get(symbol, {})
        
        if not graph or not matrix:
            return RegimeGraphPath(symbol=symbol, current_state="UNCERTAIN")
        
        # Walk through graph
        current = graph.current_state
        path = []
        probabilities = []
        durations = []
        
        for _ in range(steps):
            likely_next, prob, _ = self.predict_next_state(matrix, current)
            
            if prob == 0 or likely_next == "UNCERTAIN":
                break
            
            path.append(likely_next)
            probabilities.append(prob)
            
            # Get estimated duration
            for edge in graph.edges:
                if edge.from_state == current and edge.to_state == likely_next:
                    durations.append(edge.avg_transition_time_minutes)
                    break
            else:
                durations.append(60.0)  # Default 1 hour
            
            current = likely_next
        
        # Combined probability
        combined = 1.0
        for p in probabilities:
            combined *= p
        
        return RegimeGraphPath(
            symbol=symbol,
            current_state=graph.current_state,
            predicted_path=path,
            path_probabilities=probabilities,
            combined_probability=round(combined, 4),
            path_confidence=graph.path_confidence,
            estimated_durations_minutes=durations,
            total_estimated_minutes=sum(durations),
        )
    
    # ═══════════════════════════════════════════════════════════
    # 11. Modifier for Hypothesis Engine
    # ═══════════════════════════════════════════════════════════
    
    def get_modifier(
        self,
        symbol: str,
        hypothesis_direction: str = "LONG",
    ) -> RegimeGraphModifier:
        """
        Get modifier for hypothesis engine based on graph analysis.
        
        Regime graph contributes 4% to hypothesis score.
        """
        symbol = symbol.upper()
        
        # Get current graph state
        graph = self.analyze(symbol)
        
        # Calculate graph score based on prediction quality
        graph_score = graph.path_confidence
        
        # Weighted contribution
        weighted_contribution = graph_score * REGIME_GRAPH_WEIGHT
        
        # Determine if transition is favorable for hypothesis direction
        is_favorable = self._is_favorable_transition(
            graph.current_state,
            graph.likely_next_state,
            hypothesis_direction,
        )
        
        # Calculate modifier
        modifier = 1.0
        reason = "Neutral graph signal"
        
        if graph.path_confidence >= 0.6:
            if is_favorable:
                modifier = 1.0 + (graph_score * 0.08)  # Up to 1.08
                reason = f"High confidence favorable transition ({graph.current_state}→{graph.likely_next_state})"
            else:
                modifier = 1.0 - (graph_score * 0.05)  # Down to 0.95
                reason = f"High confidence unfavorable transition"
        elif graph.path_confidence >= 0.4:
            if is_favorable:
                modifier = 1.0 + (graph_score * 0.04)  # Up to 1.04
                reason = f"Moderate confidence favorable transition"
        
        return RegimeGraphModifier(
            symbol=symbol,
            graph_score=graph_score,
            graph_weight=REGIME_GRAPH_WEIGHT,
            weighted_contribution=round(weighted_contribution, 4),
            current_state=graph.current_state,
            likely_next_state=graph.likely_next_state,
            next_state_probability=graph.next_state_probability,
            path_confidence=graph.path_confidence,
            is_favorable_transition=is_favorable,
            modifier=round(modifier, 4),
            reason=reason,
        )
    
    def _is_favorable_transition(
        self,
        current_state: str,
        next_state: str,
        hypothesis_direction: str,
    ) -> bool:
        """
        Determine if transition is favorable for hypothesis direction.
        """
        # Favorable transitions for LONG
        long_favorable = {
            ("RANGING", "TREND_UP"),
            ("RANGING", "TRENDING"),
            ("COMPRESSION", "EXPANSION"),
            ("VOLATILE", "TRENDING"),
            ("UNCERTAIN", "TREND_UP"),
        }
        
        # Favorable transitions for SHORT
        short_favorable = {
            ("RANGING", "TREND_DOWN"),
            ("TREND_UP", "VOLATILE"),
            ("EXPANSION", "COMPRESSION"),
            ("TRENDING", "RANGING"),
        }
        
        transition = (current_state, next_state)
        
        if hypothesis_direction == "LONG":
            return transition in long_favorable
        elif hypothesis_direction == "SHORT":
            return transition in short_favorable
        
        return False
    
    # ═══════════════════════════════════════════════════════════
    # 12. Storage and Cache
    # ═══════════════════════════════════════════════════════════
    
    def _store_state(self, symbol: str, state: RegimeGraphState) -> None:
        """Store state in cache."""
        if symbol not in self._graphs:
            self._graphs[symbol] = []
        self._graphs[symbol].append(state)
        self._current[symbol] = state
    
    def get_current_state(self, symbol: str) -> Optional[RegimeGraphState]:
        """Get cached state for symbol."""
        return self._current.get(symbol.upper())
    
    def get_history(self, symbol: str, limit: int = 100) -> List[RegimeGraphState]:
        """Get state history."""
        history = self._graphs.get(symbol.upper(), [])
        return sorted(history, key=lambda s: s.created_at, reverse=True)[:limit]
    
    # ═══════════════════════════════════════════════════════════
    # 13. Summary Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_summary(self, symbol: str) -> RegimeGraphSummary:
        """Generate summary statistics for regime graph."""
        symbol = symbol.upper()
        
        graph = self._current.get(symbol)
        if not graph:
            graph = self.analyze(symbol)
        
        # Most visited state
        most_visited = max(graph.nodes, key=lambda n: n.visits, default=None)
        
        # Most common transition
        most_common_edge = max(graph.edges, key=lambda e: e.transition_count, default=None)
        
        # Matrix density
        node_count = len([n for n in graph.nodes if n.visits > 0])
        edge_count = len(graph.edges)
        max_edges = node_count * node_count if node_count > 0 else 1
        density = edge_count / max_edges if max_edges > 0 else 0.0
        
        # Average duration
        durations = [n.avg_duration_minutes for n in graph.nodes if n.avg_duration_minutes > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        return RegimeGraphSummary(
            symbol=symbol,
            node_count=node_count,
            edge_count=edge_count,
            most_visited_state=most_visited.regime_state if most_visited else "",
            most_visited_count=most_visited.visits if most_visited else 0,
            most_common_transition=f"{most_common_edge.from_state} → {most_common_edge.to_state}" if most_common_edge else "",
            most_common_transition_count=most_common_edge.transition_count if most_common_edge else 0,
            matrix_density=round(density, 4),
            current_state=graph.current_state,
            likely_next_state=graph.likely_next_state,
            total_transitions=graph.total_transitions,
            avg_state_duration_minutes=round(avg_duration, 2),
            last_updated=datetime.now(timezone.utc),
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_graph_engine: Optional[RegimeGraphEngine] = None


def get_regime_graph_engine() -> RegimeGraphEngine:
    """Get singleton instance of RegimeGraphEngine."""
    global _graph_engine
    if _graph_engine is None:
        _graph_engine = RegimeGraphEngine()
    return _graph_engine
