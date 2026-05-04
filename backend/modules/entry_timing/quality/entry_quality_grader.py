"""
PHASE 4.4 — Entry Quality Grader

Grades entry quality score into A/B/C/D/F.
"""

from typing import Dict


class EntryQualityGrader:
    """Grades entry quality score."""
    
    def grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 0.85:
            return "A"
        if score >= 0.70:
            return "B"
        if score >= 0.55:
            return "C"
        if score >= 0.40:
            return "D"
        return "F"
    
    def grade_with_description(self, score: float) -> Dict:
        """Get grade with description."""
        grade = self.grade(score)
        
        descriptions = {
            "A": "Excellent entry quality - optimal timing",
            "B": "Good entry quality - minor concerns",
            "C": "Average entry quality - consider size reduction",
            "D": "Poor entry quality - significant concerns",
            "F": "Very poor entry quality - consider skip"
        }
        
        recommendations = {
            "A": "Full position recommended",
            "B": "Standard position size",
            "C": "Consider 75% position size",
            "D": "Consider 50% position size or skip",
            "F": "Recommend skip or minimal position"
        }
        
        return {
            "grade": grade,
            "score": round(score, 3),
            "description": descriptions[grade],
            "recommendation": recommendations[grade]
        }
