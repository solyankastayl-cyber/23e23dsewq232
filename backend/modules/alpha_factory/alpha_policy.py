"""
AF2 - Alpha Policy Layer
========================
Defines rules for when alpha actions auto-apply vs require manual approval.

Key concepts:
- Confidence thresholds per action type
- Cooldown periods between auto-applies
- Rate limits per time window
- High-risk gates (always manual for dangerous actions)
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PolicyRule:
    """Single policy rule for an action type"""
    action_type: str
    min_confidence: float
    cooldown_seconds: int
    max_per_window: int
    window_seconds: int
    require_manual: bool       # Force manual regardless of confidence
    min_sample_size: int       # Minimum trades before allowing auto-apply
    
    def to_dict(self):
        return asdict(self)


@dataclass
class PolicyState:
    """Tracks policy execution state"""
    last_auto_apply: Dict[str, str] = field(default_factory=dict)
    apply_counts: Dict[str, List[str]] = field(default_factory=dict)
    total_auto_applied: int = 0
    total_manual_queued: int = 0
    total_blocked: int = 0
    
    def to_dict(self):
        return {
            "last_auto_apply": self.last_auto_apply,
            "apply_counts_summary": {k: len(v) for k, v in self.apply_counts.items()},
            "total_auto_applied": self.total_auto_applied,
            "total_manual_queued": self.total_manual_queued,
            "total_blocked": self.total_blocked,
        }


# Default rules per action type
DEFAULT_RULES: Dict[str, PolicyRule] = {
    "DISABLE_SYMBOL": PolicyRule(
        action_type="DISABLE_SYMBOL",
        min_confidence=0.90,
        cooldown_seconds=3600,       # 1 hour
        max_per_window=2,
        window_seconds=14400,        # 4 hours
        require_manual=False,
        min_sample_size=10,
    ),
    "REDUCE_RISK": PolicyRule(
        action_type="REDUCE_RISK",
        min_confidence=0.70,
        cooldown_seconds=1800,       # 30 min
        max_per_window=4,
        window_seconds=14400,
        require_manual=False,
        min_sample_size=8,
    ),
    "INCREASE_ALLOCATION": PolicyRule(
        action_type="INCREASE_ALLOCATION",
        min_confidence=0.80,
        cooldown_seconds=3600,
        max_per_window=2,
        window_seconds=14400,
        require_manual=False,
        min_sample_size=12,
    ),
    "UPGRADE_ENTRY_MODE": PolicyRule(
        action_type="UPGRADE_ENTRY_MODE",
        min_confidence=0.75,
        cooldown_seconds=7200,       # 2 hours
        max_per_window=2,
        window_seconds=28800,        # 8 hours
        require_manual=True,         # Always manual
        min_sample_size=10,
    ),
    "DOWNGRADE_ENTRY_MODE": PolicyRule(
        action_type="DOWNGRADE_ENTRY_MODE",
        min_confidence=0.80,
        cooldown_seconds=3600,
        max_per_window=2,
        window_seconds=14400,
        require_manual=False,
        min_sample_size=10,
    ),
    "INCREASE_THRESHOLD": PolicyRule(
        action_type="INCREASE_THRESHOLD",
        min_confidence=0.65,
        cooldown_seconds=1800,
        max_per_window=4,
        window_seconds=14400,
        require_manual=False,
        min_sample_size=8,
    ),
}


class AlphaPolicy:
    """
    Policy engine determining auto-apply vs manual for each alpha action.
    
    Flow:
    1. Alpha Factory generates actions with confidence
    2. Policy evaluates each action against rules
    3. Returns verdict: AUTO_APPLY / MANUAL / BLOCKED
    """
    
    def __init__(self):
        self.rules: Dict[str, PolicyRule] = dict(DEFAULT_RULES)
        self.state = PolicyState()
        self.enabled = True
    
    def evaluate(self, action: Dict[str, Any], alpha_mode: str) -> Dict[str, Any]:
        """
        Evaluate a single action against policy rules.
        
        Returns:
            {
                "verdict": "AUTO_APPLY" | "MANUAL" | "BLOCKED",
                "reason": str,
                "rule_applied": str,
                "action": dict
            }
        """
        action_type = action.get("action", "KEEP")
        
        # KEEP actions pass through
        if action_type == "KEEP":
            return {
                "verdict": "PASS",
                "reason": "keep_action_no_change",
                "rule_applied": "none",
                "action": action,
            }
        
        # Alpha OFF = block everything
        if alpha_mode == "OFF":
            self.state.total_blocked += 1
            return {
                "verdict": "BLOCKED",
                "reason": "alpha_mode_off",
                "rule_applied": "global",
                "action": action,
            }
        
        # Alpha MANUAL = everything goes to manual queue
        if alpha_mode == "MANUAL":
            self.state.total_manual_queued += 1
            return {
                "verdict": "MANUAL",
                "reason": "alpha_mode_manual",
                "rule_applied": "global",
                "action": action,
            }
        
        # Alpha AUTO = evaluate against policy rules
        if alpha_mode == "AUTO":
            return self._evaluate_auto(action)
        
        # Unknown mode = manual
        return {
            "verdict": "MANUAL",
            "reason": "unknown_alpha_mode",
            "rule_applied": "fallback",
            "action": action,
        }
    
    def _evaluate_auto(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate action in AUTO mode against specific rules"""
        action_type = action.get("action", "")
        confidence = float(action.get("confidence", 0.0))
        sample_size = int(action.get("sample_size", 0))
        scope_key = action.get("scope_key", "")
        
        rule = self.rules.get(action_type)
        
        # No rule = manual
        if not rule:
            self.state.total_manual_queued += 1
            return {
                "verdict": "MANUAL",
                "reason": f"no_policy_rule_for_{action_type}",
                "rule_applied": "default_manual",
                "action": action,
            }
        
        # Always-manual actions
        if rule.require_manual:
            self.state.total_manual_queued += 1
            return {
                "verdict": "MANUAL",
                "reason": "rule_requires_manual_approval",
                "rule_applied": action_type,
                "action": action,
            }
        
        # Sample size check
        if sample_size < rule.min_sample_size:
            self.state.total_manual_queued += 1
            return {
                "verdict": "MANUAL",
                "reason": f"sample_size_{sample_size}_below_min_{rule.min_sample_size}",
                "rule_applied": action_type,
                "action": action,
            }
        
        # Confidence check
        if confidence < rule.min_confidence:
            self.state.total_manual_queued += 1
            return {
                "verdict": "MANUAL",
                "reason": f"confidence_{confidence:.2f}_below_threshold_{rule.min_confidence}",
                "rule_applied": action_type,
                "action": action,
            }
        
        # Cooldown check
        cooldown_key = f"{action_type}:{scope_key}"
        if not self._check_cooldown(cooldown_key, rule.cooldown_seconds):
            self.state.total_manual_queued += 1
            return {
                "verdict": "MANUAL",
                "reason": "cooldown_active",
                "rule_applied": action_type,
                "action": action,
            }
        
        # Rate limit check
        if not self._check_rate_limit(action_type, rule.max_per_window, rule.window_seconds):
            self.state.total_manual_queued += 1
            return {
                "verdict": "MANUAL",
                "reason": "rate_limit_exceeded",
                "rule_applied": action_type,
                "action": action,
            }
        
        # All checks passed → AUTO_APPLY
        self._record_auto_apply(cooldown_key, action_type)
        self.state.total_auto_applied += 1
        
        return {
            "verdict": "AUTO_APPLY",
            "reason": f"confidence_{confidence:.2f}_meets_threshold_{rule.min_confidence}",
            "rule_applied": action_type,
            "action": action,
        }
    
    def _check_cooldown(self, key: str, cooldown_seconds: int) -> bool:
        """Check if cooldown has elapsed"""
        last = self.state.last_auto_apply.get(key)
        if not last:
            return True
        
        last_time = datetime.fromisoformat(last)
        elapsed = (utc_now() - last_time).total_seconds()
        return elapsed >= cooldown_seconds
    
    def _check_rate_limit(self, action_type: str, max_count: int, window_seconds: int) -> bool:
        """Check rate limit within time window"""
        timestamps = self.state.apply_counts.get(action_type, [])
        cutoff = utc_now() - timedelta(seconds=window_seconds)
        
        # Clean old entries
        recent = [t for t in timestamps if datetime.fromisoformat(t) > cutoff]
        self.state.apply_counts[action_type] = recent
        
        return len(recent) < max_count
    
    def _record_auto_apply(self, cooldown_key: str, action_type: str):
        """Record that an auto-apply happened"""
        now_str = utc_now().isoformat()
        self.state.last_auto_apply[cooldown_key] = now_str
        
        if action_type not in self.state.apply_counts:
            self.state.apply_counts[action_type] = []
        self.state.apply_counts[action_type].append(now_str)
    
    def evaluate_batch(self, actions: List[Dict[str, Any]], alpha_mode: str) -> Dict[str, Any]:
        """
        Evaluate a batch of actions.
        
        Returns categorized results:
        {
            "auto_apply": [...],
            "manual": [...],
            "blocked": [...],
            "passed": [...],  # KEEP actions
            "summary": {...}
        }
        """
        results = {
            "auto_apply": [],
            "manual": [],
            "blocked": [],
            "passed": [],
        }
        
        for action in actions:
            evaluation = self.evaluate(action, alpha_mode)
            verdict = evaluation["verdict"]
            
            if verdict == "AUTO_APPLY":
                results["auto_apply"].append(evaluation)
            elif verdict == "MANUAL":
                results["manual"].append(evaluation)
            elif verdict == "BLOCKED":
                results["blocked"].append(evaluation)
            elif verdict == "PASS":
                results["passed"].append(evaluation)
        
        results["summary"] = {
            "auto_apply_count": len(results["auto_apply"]),
            "manual_count": len(results["manual"]),
            "blocked_count": len(results["blocked"]),
            "passed_count": len(results["passed"]),
            "total": len(actions),
        }
        
        return results
    
    # === Rule Management ===
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all policy rules"""
        return [r.to_dict() for r in self.rules.values()]
    
    def get_rule(self, action_type: str) -> Optional[Dict[str, Any]]:
        """Get rule for specific action type"""
        rule = self.rules.get(action_type)
        return rule.to_dict() if rule else None
    
    def update_rule(self, action_type: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a policy rule"""
        if action_type not in self.rules:
            raise ValueError(f"Unknown action type: {action_type}")
        
        rule = self.rules[action_type]
        
        if "min_confidence" in updates:
            rule.min_confidence = float(updates["min_confidence"])
        if "cooldown_seconds" in updates:
            rule.cooldown_seconds = int(updates["cooldown_seconds"])
        if "max_per_window" in updates:
            rule.max_per_window = int(updates["max_per_window"])
        if "window_seconds" in updates:
            rule.window_seconds = int(updates["window_seconds"])
        if "require_manual" in updates:
            rule.require_manual = bool(updates["require_manual"])
        if "min_sample_size" in updates:
            rule.min_sample_size = int(updates["min_sample_size"])
        
        return rule.to_dict()
    
    def reset_rules(self):
        """Reset rules to defaults"""
        self.rules = dict(DEFAULT_RULES)
    
    def get_state(self) -> Dict[str, Any]:
        """Get policy execution state"""
        return {
            "enabled": self.enabled,
            "rules_count": len(self.rules),
            "state": self.state.to_dict(),
        }
    
    def reset_state(self):
        """Reset execution state (not rules)"""
        self.state = PolicyState()
