"""FACTS Rubric Evaluation Core Module.

Implements the 5-pillar evaluation framework:
- F: Factual Accuracy (30%)
- A: Adherence to Constraints (25%)
- C: Completeness (20%)
- T: Tone & Persona (10%)
- S: Structure & Formatting (15%)
"""

from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator


RUBRIC_WEIGHTS = {
    "factual_accuracy": 0.30,
    "adherence": 0.25,
    "completeness": 0.20,
    "tone": 0.10,
    "structure": 0.15,
}


class DimensionScore(BaseModel):
    """Individual score (1 to 5) with optional rationale."""
    score: int = Field(..., ge=1, le=5, description="Score from 1 (unacceptable) to 5 (flawless)")
    notes: Optional[str] = Field(default="", description="Specific flaw or justification")


class FACTSAssessment(BaseModel):
    """Complete FACTS assessment for a single model response."""
    factual_accuracy: DimensionScore
    adherence: DimensionScore
    completeness: DimensionScore
    tone: DimensionScore
    structure: DimensionScore
    general_notes: Optional[str] = ""

    def calculate_composite_score(self) -> float:
        """Calculates normalized composite score out of 100."""
        # Convert 1-5 scale to 20-100% scale
        # 1 -> 20, 2 -> 40, 3 -> 60, 4 -> 80, 5 -> 100
        total = (
            (self.factual_accuracy.score * 20.0) * RUBRIC_WEIGHTS["factual_accuracy"] +
            (self.adherence.score * 20.0) * RUBRIC_WEIGHTS["adherence"] +
            (self.completeness.score * 20.0) * RUBRIC_WEIGHTS["completeness"] +
            (self.tone.score * 20.0) * RUBRIC_WEIGHTS["tone"] +
            (self.structure.score * 20.0) * RUBRIC_WEIGHTS["structure"]
        )
        return round(total, 2)


class EvaluationSubmission(BaseModel):
    """User-submitted comparison evaluation between two models."""
    prompt: str
    model_a_name: str
    model_a_response: str
    model_b_name: str
    model_b_response: str
    assessment_a: FACTSAssessment
    assessment_b: FACTSAssessment
    winner: Literal["model_a", "model_b", "tie"]
    tags: Optional[list[str]] = []


def compare_assessments(
    assessment_a: FACTSAssessment,
    assessment_b: FACTSAssessment
) -> Dict[str, Any]:
    """Compares two assessments and computes delta and recommended winner."""
    score_a = assessment_a.calculate_composite_score()
    score_b = assessment_b.calculate_composite_score()
    
    delta = round(score_a - score_b, 2)
    if delta > 2.0:
        recommended = "model_a"
    elif delta < -2.0:
        recommended = "model_b"
    else:
        recommended = "tie"
        
    return {
        "score_a": score_a,
        "score_b": score_b,
        "delta": delta,
        "recommended_winner": recommended,
        "breakdown_a": {
            k: getattr(assessment_a, k).score for k in RUBRIC_WEIGHTS.keys()
        },
        "breakdown_b": {
            k: getattr(assessment_b, k).score for k in RUBRIC_WEIGHTS.keys()
        }
    }
