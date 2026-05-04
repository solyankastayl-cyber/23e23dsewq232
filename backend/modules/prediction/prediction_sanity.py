"""
Prediction Sanity Checks

Validates predictions before saving.
Prevents unrealistic or garbage predictions.
"""

from typing import Dict, Tuple, List, Optional


class PredictionSanityChecker:
    """
    Validates prediction output.
    
    Checks:
    - Target price within reasonable range
    - Confidence not too high
    - Direction flip detection
    - Move size limits
    """
    
    # Limits
    MAX_MOVE_NORMAL = 0.15    # 15% max for normal volatility
    MAX_MOVE_HIGH_VOL = 0.25  # 25% max for high volatility
    MAX_CONFIDENCE = 0.90     # Cap confidence at 90%
    MIN_CONFIDENCE = 0.20     # Floor confidence at 20%
    
    def check(self, prediction: Dict) -> Tuple[Dict, List[str]]:
        """
        Run all sanity checks on prediction.
        
        Args:
            prediction: Prediction output dict
        
        Returns:
            (sanitized_prediction, list_of_warnings)
        """
        warnings = []
        
        # Clone to avoid mutation
        result = self._deep_copy(prediction)
        
        # Check 1: Target price limits
        result, target_warnings = self._check_target_limits(result)
        warnings.extend(target_warnings)
        
        # Check 2: Confidence limits
        result, conf_warnings = self._check_confidence_limits(result)
        warnings.extend(conf_warnings)
        
        # Check 3: Scenario consistency
        result, scenario_warnings = self._check_scenario_consistency(result)
        warnings.extend(scenario_warnings)
        
        # Check 4: Direction-target alignment
        result, align_warnings = self._check_direction_alignment(result)
        warnings.extend(align_warnings)
        
        return result, warnings
    
    def _check_target_limits(self, prediction: Dict) -> Tuple[Dict, List[str]]:
        """Ensure target prices are within limits."""
        warnings = []
        
        current_price = prediction.get("current_price", 0)
        if current_price == 0:
            return prediction, ["Missing current price"]
        
        # Get volatility to determine max move
        confidence = prediction.get("confidence", {})
        volatility_adj = confidence.get("factors", {}).get("volatility_adj", 0.9)
        is_high_vol = volatility_adj < 0.85  # High vol if adjustment was significant
        
        max_move = self.MAX_MOVE_HIGH_VOL if is_high_vol else self.MAX_MOVE_NORMAL
        
        # Check each scenario
        for name, scenario in prediction.get("scenarios", {}).items():
            target = scenario.get("target_price", current_price)
            move = abs(target - current_price) / current_price
            
            if move > max_move:
                # Clamp to max
                direction = 1 if target > current_price else -1
                new_target = current_price * (1 + max_move * direction)
                scenario["target_price"] = round(new_target, 2)
                scenario["expected_return"] = (new_target - current_price) / current_price
                warnings.append(f"Scenario '{name}' target clamped from {move:.1%} to {max_move:.1%}")
        
        return prediction, warnings
    
    def _check_confidence_limits(self, prediction: Dict) -> Tuple[Dict, List[str]]:
        """Ensure confidence within limits."""
        warnings = []
        
        conf = prediction.get("confidence", {})
        value = conf.get("value", 0.5)
        
        if value > self.MAX_CONFIDENCE:
            conf["value"] = self.MAX_CONFIDENCE
            conf["label"] = "HIGH"
            warnings.append(f"Confidence capped from {value:.0%} to {self.MAX_CONFIDENCE:.0%}")
        
        if value < self.MIN_CONFIDENCE:
            conf["value"] = self.MIN_CONFIDENCE
            conf["label"] = "LOW"
            warnings.append(f"Confidence floored from {value:.0%} to {self.MIN_CONFIDENCE:.0%}")
        
        return prediction, warnings
    
    def _check_scenario_consistency(self, prediction: Dict) -> Tuple[Dict, List[str]]:
        """Ensure scenarios are logically consistent."""
        warnings = []
        
        scenarios = prediction.get("scenarios", {})
        current_price = prediction.get("current_price", 0)
        
        if not scenarios or current_price == 0:
            return prediction, warnings
        
        bull = scenarios.get("bull", {})
        bear = scenarios.get("bear", {})
        base = scenarios.get("base", {})
        
        bull_target = bull.get("target_price", current_price)
        bear_target = bear.get("target_price", current_price)
        base_target = base.get("target_price", current_price)
        
        # Bull should be highest, bear should be lowest
        if bull_target < base_target:
            bull["target_price"] = base_target * 1.02
            warnings.append("Fixed: bull target was below base")
        
        if bear_target > base_target:
            bear["target_price"] = base_target * 0.98
            warnings.append("Fixed: bear target was above base")
        
        if bull_target < bear_target:
            # Swap them
            bull["target_price"], bear["target_price"] = bear_target, bull_target
            warnings.append("Fixed: bull/bear targets were inverted")
        
        # Probabilities should sum to ~1
        total_prob = sum(s.get("probability", 0) for s in scenarios.values())
        if abs(total_prob - 1.0) > 0.01:
            # Normalize
            for name, s in scenarios.items():
                s["probability"] = s.get("probability", 0.33) / total_prob if total_prob > 0 else 0.33
            warnings.append(f"Normalized probabilities (was {total_prob:.2f})")
        
        return prediction, warnings
    
    def _check_direction_alignment(self, prediction: Dict) -> Tuple[Dict, List[str]]:
        """Ensure direction matches base scenario movement."""
        warnings = []
        
        direction = prediction.get("direction", {}).get("label", "neutral")
        current_price = prediction.get("current_price", 0)
        base_target = prediction.get("scenarios", {}).get("base", {}).get("target_price", current_price)
        
        if current_price == 0:
            return prediction, warnings
        
        implied_direction = "neutral"
        move = (base_target - current_price) / current_price
        
        if move > 0.01:
            implied_direction = "bullish"
        elif move < -0.01:
            implied_direction = "bearish"
        
        if direction != implied_direction and direction != "neutral":
            warnings.append(f"Direction mismatch: {direction} but base target implies {implied_direction}")
            # Don't auto-fix, just warn
        
        return prediction, warnings
    
    def _deep_copy(self, d: Dict) -> Dict:
        """Simple deep copy without importing copy module."""
        if isinstance(d, dict):
            return {k: self._deep_copy(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self._deep_copy(x) for x in d]
        else:
            return d


# Singleton
_checker: Optional[PredictionSanityChecker] = None


def get_sanity_checker() -> PredictionSanityChecker:
    """Get singleton checker instance."""
    global _checker
    if _checker is None:
        _checker = PredictionSanityChecker()
    return _checker


def sanity_check_prediction(prediction: Dict) -> Tuple[Dict, List[str]]:
    """Convenience function to run sanity checks."""
    return get_sanity_checker().check(prediction)
