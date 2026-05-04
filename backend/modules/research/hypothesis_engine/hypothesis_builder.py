"""
PHASE 6.1 - Hypothesis Builder
==============================
Builds hypotheses from conditions and validates them.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid

from .hypothesis_types import (
    HypothesisDefinition, HypothesisCondition, ExpectedOutcome,
    HypothesisCategory, HypothesisStatus, ConditionOperator
)


class HypothesisBuilder:
    """
    Builder pattern for creating hypotheses
    """
    
    def __init__(self):
        self._hypothesis_id: Optional[str] = None
        self._name: Optional[str] = None
        self._description: str = ""
        self._category: Optional[HypothesisCategory] = None
        self._conditions: List[HypothesisCondition] = []
        self._expected_outcome: Optional[ExpectedOutcome] = None
        self._applicable_regimes: List[str] = ["TREND_UP", "TREND_DOWN", "RANGE"]
        self._applicable_timeframes: List[str] = ["1h", "4h", "1d"]
        self._applicable_symbols: List[str] = ["BTC", "ETH", "SOL"]
        self._tags: List[str] = []
        self._author: str = "system"
    
    def with_id(self, hypothesis_id: str) -> 'HypothesisBuilder':
        self._hypothesis_id = hypothesis_id
        return self
    
    def with_name(self, name: str) -> 'HypothesisBuilder':
        self._name = name
        return self
    
    def with_description(self, description: str) -> 'HypothesisBuilder':
        self._description = description
        return self
    
    def with_category(self, category: HypothesisCategory) -> 'HypothesisBuilder':
        self._category = category
        return self
    
    def add_condition(
        self,
        indicator: str,
        operator: ConditionOperator,
        value: Any,
        description: str = "",
        weight: float = 1.0
    ) -> 'HypothesisBuilder':
        """Add a condition to the hypothesis"""
        condition = HypothesisCondition(
            indicator=indicator,
            operator=operator,
            value=value,
            description=description,
            weight=weight
        )
        self._conditions.append(condition)
        return self
    
    def with_conditions(self, conditions: List[HypothesisCondition]) -> 'HypothesisBuilder':
        self._conditions = conditions
        return self
    
    def with_expected_outcome(
        self,
        direction: str,
        target_move_pct: float,
        time_horizon_candles: int,
        confidence: float = 0.5
    ) -> 'HypothesisBuilder':
        """Set expected outcome"""
        self._expected_outcome = ExpectedOutcome(
            direction=direction,
            target_move_pct=target_move_pct,
            time_horizon_candles=time_horizon_candles,
            confidence=confidence
        )
        return self
    
    def with_applicable_regimes(self, regimes: List[str]) -> 'HypothesisBuilder':
        self._applicable_regimes = regimes
        return self
    
    def with_applicable_timeframes(self, timeframes: List[str]) -> 'HypothesisBuilder':
        self._applicable_timeframes = timeframes
        return self
    
    def with_applicable_symbols(self, symbols: List[str]) -> 'HypothesisBuilder':
        self._applicable_symbols = symbols
        return self
    
    def with_tags(self, tags: List[str]) -> 'HypothesisBuilder':
        self._tags = tags
        return self
    
    def with_author(self, author: str) -> 'HypothesisBuilder':
        self._author = author
        return self
    
    def validate(self) -> List[str]:
        """Validate the hypothesis configuration"""
        errors = []
        
        if not self._name:
            errors.append("Name is required")
        
        if not self._category:
            errors.append("Category is required")
        
        if not self._conditions:
            errors.append("At least one condition is required")
        
        if not self._expected_outcome:
            errors.append("Expected outcome is required")
        
        if self._expected_outcome:
            if self._expected_outcome.direction not in ["LONG", "SHORT", "NEUTRAL"]:
                errors.append("Direction must be LONG, SHORT, or NEUTRAL")
            
            if self._expected_outcome.target_move_pct <= 0:
                errors.append("Target move must be positive")
            
            if self._expected_outcome.time_horizon_candles <= 0:
                errors.append("Time horizon must be positive")
        
        # Validate conditions
        for i, cond in enumerate(self._conditions):
            if not cond.indicator:
                errors.append(f"Condition {i+1}: indicator is required")
            if cond.weight <= 0:
                errors.append(f"Condition {i+1}: weight must be positive")
        
        return errors
    
    def build(self) -> HypothesisDefinition:
        """Build the hypothesis"""
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid hypothesis: {', '.join(errors)}")
        
        hypothesis_id = self._hypothesis_id or f"hyp_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        return HypothesisDefinition(
            hypothesis_id=hypothesis_id,
            name=self._name,
            description=self._description,
            category=self._category,
            condition_set=self._conditions,
            expected_outcome=self._expected_outcome,
            applicable_regimes=self._applicable_regimes,
            applicable_timeframes=self._applicable_timeframes,
            applicable_symbols=self._applicable_symbols,
            status=HypothesisStatus.DRAFT,
            author=self._author,
            created_at=now,
            updated_at=now,
            tags=self._tags
        )
    
    @staticmethod
    def from_dict(data: Dict) -> 'HypothesisBuilder':
        """Create builder from dictionary"""
        builder = HypothesisBuilder()
        
        if 'hypothesis_id' in data:
            builder.with_id(data['hypothesis_id'])
        
        if 'name' in data:
            builder.with_name(data['name'])
        
        if 'description' in data:
            builder.with_description(data['description'])
        
        if 'category' in data:
            category = data['category']
            if isinstance(category, str):
                category = HypothesisCategory(category)
            builder.with_category(category)
        
        if 'conditions' in data:
            for cond_data in data['conditions']:
                operator = cond_data.get('operator', 'GTE')
                if isinstance(operator, str):
                    operator = ConditionOperator(operator)
                
                builder.add_condition(
                    indicator=cond_data['indicator'],
                    operator=operator,
                    value=cond_data['value'],
                    description=cond_data.get('description', ''),
                    weight=cond_data.get('weight', 1.0)
                )
        
        if 'expected_outcome' in data:
            outcome = data['expected_outcome']
            builder.with_expected_outcome(
                direction=outcome['direction'],
                target_move_pct=outcome['target_move_pct'],
                time_horizon_candles=outcome['time_horizon_candles'],
                confidence=outcome.get('confidence', 0.5)
            )
        
        if 'applicable_regimes' in data:
            builder.with_applicable_regimes(data['applicable_regimes'])
        
        if 'applicable_timeframes' in data:
            builder.with_applicable_timeframes(data['applicable_timeframes'])
        
        if 'applicable_symbols' in data:
            builder.with_applicable_symbols(data['applicable_symbols'])
        
        if 'tags' in data:
            builder.with_tags(data['tags'])
        
        if 'author' in data:
            builder.with_author(data['author'])
        
        return builder


def create_hypothesis_from_template(
    template_id: str,
    name: str,
    modifications: Dict = None
) -> HypothesisDefinition:
    """
    Create hypothesis from a template with modifications
    """
    from .hypothesis_registry import get_hypothesis_registry
    
    registry = get_hypothesis_registry()
    template = registry.get(template_id)
    
    if not template:
        raise ValueError(f"Template not found: {template_id}")
    
    # Create builder from template
    builder = HypothesisBuilder()
    builder.with_name(name)
    builder.with_description(template.description)
    builder.with_category(template.category)
    builder.with_conditions(template.condition_set.copy())
    builder.with_expected_outcome(
        template.expected_outcome.direction,
        template.expected_outcome.target_move_pct,
        template.expected_outcome.time_horizon_candles,
        template.expected_outcome.confidence
    )
    builder.with_applicable_regimes(template.applicable_regimes.copy())
    builder.with_applicable_timeframes(template.applicable_timeframes.copy())
    builder.with_applicable_symbols(template.applicable_symbols.copy())
    builder.with_tags(template.tags.copy())
    
    # Apply modifications
    if modifications:
        if 'description' in modifications:
            builder.with_description(modifications['description'])
        if 'applicable_regimes' in modifications:
            builder.with_applicable_regimes(modifications['applicable_regimes'])
        if 'applicable_timeframes' in modifications:
            builder.with_applicable_timeframes(modifications['applicable_timeframes'])
        if 'tags' in modifications:
            builder.with_tags(modifications['tags'])
    
    return builder.build()
