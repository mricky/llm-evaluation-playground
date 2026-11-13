"""Ground Truth Trainer & Evaluator Calibration Engine.

Compares human evaluation scores against hidden Gold Standard expert annotations
to calibrate precision, detect cognitive biases (e.g., length bias), and grade
evaluator competence.
"""

from typing import Dict, Any, List, Optional
from core.facts_rubric import FACTSAssessment, RUBRIC_WEIGHTS


def calculate_evaluator_alignment(
    user_assessment: FACTSAssessment,
    gold_standard: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compares user scores (1-5) against expert gold standard scores.
    Returns:
        alignment_score (0 - 100%)
        dimension_deltas
        critique_notes
        traps_caught
    """
    total_weighted_deviation = 0.0
    dimension_results = {}
    traps_caught = []
    critique_notes = []

    for dim, weight in RUBRIC_WEIGHTS.items():
        user_val = getattr(user_assessment, dim).score
        gold_val = gold_standard.get(dim, {}).get("score", 5)
        flaw_desc = gold_standard.get(dim, {}).get("flaw_description", "")
        is_trap = gold_standard.get(dim, {}).get("is_trap", False)

        delta = user_val - gold_val  # Positive means user was too lenient
        abs_delta = abs(delta)
        total_weighted_deviation += (abs_delta / 4.0) * weight * 100.0

        dimension_results[dim] = {
            "user_score": user_val,
            "gold_score": gold_val,
            "delta": delta,
            "flaw_description": flaw_desc,
            "is_trap": is_trap
        }

        # Check trap detection
        if is_trap:
            # If the expert gave a low score (e.g. <= 3) and user also gave <= 3
            if gold_val <= 3 and user_val <= 3:
                traps_caught.append(f"Caught critical trap in '{dim}': {flaw_desc}")
            elif gold_val <= 3 and user_val > 3:
                critique_notes.append(
                    f"MISSED TRAP in '{dim}': You gave {user_val}/5 but the model contained: {flaw_desc}"
                )
        else:
            if abs_delta >= 2:
                tendency = "too lenient" if delta > 0 else "too strict"
                critique_notes.append(
                    f"High calibration gap in '{dim}': You scored {user_val}/5 ({tendency}). Expert score is {gold_val}/5."
                )

    # Alignment percentage
    alignment_score = max(0.0, round(100.0 - total_weighted_deviation, 2))

    return {
        "alignment_score": alignment_score,
        "dimension_results": dimension_results,
        "traps_caught": traps_caught,
        "critique_notes": critique_notes,
        "evaluation_verdict": (
            "Master Evaluator (Elite Attention to Detail)" if alignment_score >= 85
            else "Competent Evaluator (Good, but missed subtle edge cases)" if alignment_score >= 70
            else "Needs Calibration (Overlooked critical compliance or factual traps)"
        )
    }


def grade_trainer_case(
    case_data: Dict[str, Any],
    user_assessment_a: FACTSAssessment,
    user_assessment_b: FACTSAssessment,
    user_winner: str
) -> Dict[str, Any]:
    """Grades an entire trainer benchmark case (Model A + Model B + Winner)."""
    gold_a = case_data.get("gold_standard_a", {})
    gold_b = case_data.get("gold_standard_b", {})
    expert_winner = case_data.get("expert_winner", "tie")

    align_a = calculate_evaluator_alignment(user_assessment_a, gold_a)
    align_b = calculate_evaluator_alignment(user_assessment_b, gold_b)

    overall_alignment = round((align_a["alignment_score"] + align_b["alignment_score"]) / 2.0, 2)
    winner_matched = (user_winner == expert_winner)

    return {
        "case_id": case_data.get("id"),
        "case_title": case_data.get("title"),
        "overall_alignment_score": overall_alignment,
        "winner_matched": winner_matched,
        "user_winner": user_winner,
        "expert_winner": expert_winner,
        "model_a_report": align_a,
        "model_b_report": align_b,
        "expert_explanation": case_data.get("expert_explanation", "")
    }
