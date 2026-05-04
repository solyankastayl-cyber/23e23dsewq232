"""
PHASE 2.9.4 — Edge Classifier

Classifies edge strength for each asset/cluster/regime:
- strong_edge: WR > 0.6, PF > 1.5, stable
- weak_edge: WR > 0.5, or PF > 1.2
- unstable_edge: has edge but high variance
- no_edge: WR < 0.45 or PF < 1.0

Answers: "Where does edge exist and how strong is it?"
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class EdgeClass(Enum):
    """Edge classification levels."""
    STRONG = "strong"
    WEAK = "weak"
    UNSTABLE = "unstable"
    NO_EDGE = "no_edge"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class EdgeClassification:
    """Edge classification result."""
    edge_class: EdgeClass
    confidence: float  # 0-1 how confident in classification
    win_rate: float
    profit_factor: float
    stability: float
    sample_size: int
    reasons: List[str]


class EdgeClassifier:
    """
    Classifies edge strength based on performance metrics.
    
    Thresholds (configurable):
    - strong: WR >= 0.6, PF >= 1.5, stability >= 0.6
    - weak: WR >= 0.5, PF >= 1.2
    - unstable: has positive expectancy but stability < 0.4
    - no_edge: below all thresholds
    """
    
    def __init__(
        self,
        strong_wr: float = 0.6,
        strong_pf: float = 1.5,
        weak_wr: float = 0.5,
        weak_pf: float = 1.2,
        stability_threshold: float = 0.4,
        min_samples: int = 30
    ):
        self.strong_wr = strong_wr
        self.strong_pf = strong_pf
        self.weak_wr = weak_wr
        self.weak_pf = weak_pf
        self.stability_threshold = stability_threshold
        self.min_samples = min_samples
    
    def classify(self, stats: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Classify edge for each key in stats.
        
        Args:
            stats: {key: {win_rate, profit_factor, stability_score, trades, ...}}
        
        Returns:
            {key: {edge_class, confidence, reasons, ...}}
        """
        result = {}
        
        for key, s in stats.items():
            classification = self._classify_single(s)
            
            result[key] = {
                "edge_class": classification.edge_class.value,
                "confidence": round(classification.confidence, 4),
                "win_rate": round(classification.win_rate, 4),
                "profit_factor": classification.profit_factor,
                "stability": round(classification.stability, 4),
                "sample_size": classification.sample_size,
                "reasons": classification.reasons,
                "recommendation": self._get_recommendation(classification)
            }
        
        return result
    
    def _classify_single(self, stats: Dict) -> EdgeClassification:
        """Classify edge for single stats dict."""
        wr = stats.get("win_rate", 0)
        pf = stats.get("profit_factor", 0)
        if isinstance(pf, str) and pf == "inf":
            pf = 10.0  # Cap infinity
        stability = stats.get("stability_score", 0.5)
        trades = stats.get("trades", 0)
        
        reasons = []
        
        # Check sample size
        if trades < self.min_samples:
            return EdgeClassification(
                edge_class=EdgeClass.INSUFFICIENT_DATA,
                confidence=0.3,
                win_rate=wr,
                profit_factor=pf,
                stability=stability,
                sample_size=trades,
                reasons=[f"Only {trades} trades, need {self.min_samples}"]
            )
        
        # Strong Edge
        if wr >= self.strong_wr and pf >= self.strong_pf and stability >= self.stability_threshold:
            reasons = [
                f"Win rate {wr:.1%} >= {self.strong_wr:.0%}",
                f"Profit factor {pf:.2f} >= {self.strong_pf}",
                f"Stability {stability:.2f} >= {self.stability_threshold}"
            ]
            confidence = min(0.95, 0.7 + (trades / 500) * 0.25)
            return EdgeClassification(
                edge_class=EdgeClass.STRONG,
                confidence=confidence,
                win_rate=wr,
                profit_factor=pf,
                stability=stability,
                sample_size=trades,
                reasons=reasons
            )
        
        # Check for instability first
        has_positive_expectancy = wr > 0.5 or pf > 1.0
        if has_positive_expectancy and stability < self.stability_threshold:
            reasons = [
                f"Positive expectancy but unstable",
                f"Stability {stability:.2f} < {self.stability_threshold}",
                f"Win rate: {wr:.1%}, PF: {pf:.2f}"
            ]
            return EdgeClassification(
                edge_class=EdgeClass.UNSTABLE,
                confidence=0.6,
                win_rate=wr,
                profit_factor=pf,
                stability=stability,
                sample_size=trades,
                reasons=reasons
            )
        
        # Weak Edge
        if wr >= self.weak_wr or pf >= self.weak_pf:
            reasons = []
            if wr >= self.weak_wr:
                reasons.append(f"Win rate {wr:.1%} >= {self.weak_wr:.0%}")
            if pf >= self.weak_pf:
                reasons.append(f"Profit factor {pf:.2f} >= {self.weak_pf}")
            if wr < self.strong_wr:
                reasons.append(f"Win rate {wr:.1%} below strong threshold")
            
            confidence = 0.5 + (trades / 300) * 0.2
            return EdgeClassification(
                edge_class=EdgeClass.WEAK,
                confidence=min(0.8, confidence),
                win_rate=wr,
                profit_factor=pf,
                stability=stability,
                sample_size=trades,
                reasons=reasons
            )
        
        # No Edge
        reasons = []
        if wr < self.weak_wr:
            reasons.append(f"Win rate {wr:.1%} below {self.weak_wr:.0%}")
        if pf < self.weak_pf:
            reasons.append(f"Profit factor {pf:.2f} below {self.weak_pf}")
        
        confidence = 0.6 + (trades / 200) * 0.3
        return EdgeClassification(
            edge_class=EdgeClass.NO_EDGE,
            confidence=min(0.9, confidence),
            win_rate=wr,
            profit_factor=pf,
            stability=stability,
            sample_size=trades,
            reasons=reasons
        )
    
    def _get_recommendation(self, classification: EdgeClassification) -> str:
        """Get recommendation based on classification."""
        recommendations = {
            EdgeClass.STRONG: "Keep active, consider increasing allocation",
            EdgeClass.WEAK: "Monitor closely, maintain current allocation",
            EdgeClass.UNSTABLE: "Reduce risk, tighten filters, or disable temporarily",
            EdgeClass.NO_EDGE: "Disable or re-evaluate strategy",
            EdgeClass.INSUFFICIENT_DATA: "Gather more data before decision"
        }
        return recommendations.get(classification.edge_class, "Review manually")
    
    def get_by_class(self, classifications: Dict[str, Dict], edge_class: str) -> List[str]:
        """Get all keys with specific edge class."""
        return [k for k, v in classifications.items() if v.get("edge_class") == edge_class]
    
    def get_actionable(self, classifications: Dict[str, Dict]) -> Dict[str, List[str]]:
        """Get actionable groups."""
        return {
            "strong": self.get_by_class(classifications, "strong"),
            "weak": self.get_by_class(classifications, "weak"),
            "unstable": self.get_by_class(classifications, "unstable"),
            "no_edge": self.get_by_class(classifications, "no_edge"),
            "insufficient_data": self.get_by_class(classifications, "insufficient_data")
        }
    
    def summary(self, classifications: Dict[str, Dict]) -> Dict:
        """Generate summary of edge classifications."""
        groups = self.get_actionable(classifications)
        total = len(classifications)
        
        return {
            "total_analyzed": total,
            "strong_edge_count": len(groups["strong"]),
            "weak_edge_count": len(groups["weak"]),
            "unstable_count": len(groups["unstable"]),
            "no_edge_count": len(groups["no_edge"]),
            "insufficient_data_count": len(groups["insufficient_data"]),
            "edge_ratio": round((len(groups["strong"]) + len(groups["weak"])) / total, 4) if total > 0 else 0,
            "strong_edge_ratio": round(len(groups["strong"]) / total, 4) if total > 0 else 0,
            "actionable_disables": groups["no_edge"],
            "actionable_reduce_risk": groups["unstable"]
        }
