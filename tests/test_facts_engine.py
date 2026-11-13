"""Comprehensive Unit Tests for FACTS Rubric, Trainer Engine, and Storage.

Run with: pytest tests/
"""

import os
import unittest
import pytest
from core.facts_rubric import (
    DimensionScore,
    FACTSAssessment,
    compare_assessments,
    RUBRIC_WEIGHTS
)
from core.ground_truth_trainer import (
    calculate_evaluator_alignment,
    grade_trainer_case
)
from core.storage import (
    init_db,
    save_evaluation,
    get_recent_evaluations
)


class TestFACTSRubric(unittest.TestCase):
    """Tests the mathematical weighting and composite score formula."""

    def test_perfect_scores_yield_100_percent(self):
        assessment = FACTSAssessment(
            factual_accuracy=DimensionScore(score=5),
            adherence=DimensionScore(score=5),
            completeness=DimensionScore(score=5),
            tone=DimensionScore(score=5),
            structure=DimensionScore(score=5)
        )
        self.assertEqual(assessment.calculate_composite_score(), 100.0)

    def test_minimum_scores_yield_20_percent(self):
        assessment = FACTSAssessment(
            factual_accuracy=DimensionScore(score=1),
            adherence=DimensionScore(score=1),
            completeness=DimensionScore(score=1),
            tone=DimensionScore(score=1),
            structure=DimensionScore(score=1)
        )
        self.assertEqual(assessment.calculate_composite_score(), 20.0)

    def test_weighted_composite_calculation(self):
        # Factual Accuracy (30%) is 5 (100%), others are 3 (60%)
        # Composite = (100 * 0.30) + (60 * 0.25) + (60 * 0.20) + (60 * 0.10) + (60 * 0.15)
        # = 30 + 15 + 12 + 6 + 9 = 72.0
        assessment = FACTSAssessment(
            factual_accuracy=DimensionScore(score=5),
            adherence=DimensionScore(score=3),
            completeness=DimensionScore(score=3),
            tone=DimensionScore(score=3),
            structure=DimensionScore(score=3)
        )
        self.assertAlmostEqual(assessment.calculate_composite_score(), 72.0, places=2)

    def test_compare_assessments_determines_winner(self):
        ass_a = FACTSAssessment(
            factual_accuracy=DimensionScore(score=5),
            adherence=DimensionScore(score=5),
            completeness=DimensionScore(score=5),
            tone=DimensionScore(score=5),
            structure=DimensionScore(score=5)
        )
        ass_b = FACTSAssessment(
            factual_accuracy=DimensionScore(score=2),
            adherence=DimensionScore(score=2),
            completeness=DimensionScore(score=2),
            tone=DimensionScore(score=2),
            structure=DimensionScore(score=2)
        )
        result = compare_assessments(ass_a, ass_b)
        self.assertEqual(result["score_a"], 100.0)
        self.assertEqual(result["score_b"], 40.0)
        self.assertEqual(result["recommended_winner"], "model_a")


class TestGroundTruthTrainer(unittest.TestCase):
    """Tests evaluator alignment grading against expert annotations."""

    def setUp(self):
        self.gold_standard = {
            "factual_accuracy": {"score": 5, "flaw_description": "Clean math", "is_trap": False},
            "adherence": {"score": 1, "flaw_description": "Violated negative constraint", "is_trap": True},
            "completeness": {"score": 5, "flaw_description": "Complete", "is_trap": False},
            "tone": {"score": 5, "flaw_description": "Neutral", "is_trap": False},
            "structure": {"score": 4, "flaw_description": "Minor formatting issue", "is_trap": False}
        }

    def test_perfect_alignment_gives_100_percent(self):
        user_assessment = FACTSAssessment(
            factual_accuracy=DimensionScore(score=5),
            adherence=DimensionScore(score=1),  # Caught the trap!
            completeness=DimensionScore(score=5),
            tone=DimensionScore(score=5),
            structure=DimensionScore(score=4)
        )
        result = calculate_evaluator_alignment(user_assessment, self.gold_standard)
        self.assertEqual(result["alignment_score"], 100.0)
        self.assertEqual(len(result["traps_caught"]), 1)
        self.assertEqual(len(result["critique_notes"]), 0)
        self.assertIn("Master Evaluator", result["evaluation_verdict"])

    def test_missed_trap_lowers_score_and_flags_critique(self):
        # User gave 5 to adherence, missing the trap!
        user_assessment = FACTSAssessment(
            factual_accuracy=DimensionScore(score=5),
            adherence=DimensionScore(score=5),  # Missed trap (expert was 1)
            completeness=DimensionScore(score=5),
            tone=DimensionScore(score=5),
            structure=DimensionScore(score=4)
        )
        result = calculate_evaluator_alignment(user_assessment, self.gold_standard)
        self.assertLess(result["alignment_score"], 80.0)
        self.assertEqual(len(result["traps_caught"]), 0)
        self.assertTrue(any("MISSED TRAP" in c for c in result["critique_notes"]))


class TestStorageLayer(unittest.TestCase):
    """Tests persistence in temporary test database."""

    def setUp(self):
        self.test_db = "/tmp/test_evaluations_arena.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        init_db(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_save_and_retrieve_evaluation(self):
        sample_payload = {
            "prompt": "Test Prompt",
            "model_a_name": "llama3:latest",
            "model_a_response": "Output A",
            "model_b_name": "gemini-1.5-flash",
            "model_b_response": "Output B",
            "score_a": 95.0,
            "score_b": 80.0,
            "winner": "model_a",
            "assessment_a": {"factual_accuracy": 5},
            "assessment_b": {"factual_accuracy": 4},
            "tags": ["unit-test"]
        }
        rec_id = save_evaluation(sample_payload, db_path=self.test_db)
        self.assertGreaterEqual(rec_id, 1)

        history = get_recent_evaluations(limit=5, db_path=self.test_db)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["model_a_name"], "llama3:latest")
        self.assertEqual(history[0]["winner"], "model_a")


if __name__ == "__main__":
    unittest.main()
