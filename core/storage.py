"""SQLite Storage & Persistence Layer.

Stores evaluation histories, benchmark test logs, and trainer calibration records.
Zero external database required.
"""

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "evaluations.db")


def init_db(db_path: str = DB_PATH):
    """Initializes SQLite tables if they do not exist."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Evaluations table (Freeform Arena)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                prompt TEXT NOT NULL,
                model_a_name TEXT NOT NULL,
                model_a_response TEXT NOT NULL,
                model_b_name TEXT NOT NULL,
                model_b_response TEXT NOT NULL,
                score_a REAL NOT NULL,
                score_b REAL NOT NULL,
                winner TEXT NOT NULL,
                assessment_a_json TEXT NOT NULL,
                assessment_b_json TEXT NOT NULL,
                tags TEXT
            )
        """)

        # Trainer Attempts table (Calibration mode)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trainer_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                case_id TEXT NOT NULL,
                case_title TEXT NOT NULL,
                alignment_score REAL NOT NULL,
                winner_matched INTEGER NOT NULL,
                user_winner TEXT NOT NULL,
                expert_winner TEXT NOT NULL,
                critique_notes_json TEXT NOT NULL
            )
        """)
        conn.commit()


def save_evaluation(data: Dict[str, Any], db_path: str = DB_PATH) -> int:
    """Saves a completed Arena evaluation."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evaluations (
                created_at, prompt, model_a_name, model_a_response,
                model_b_name, model_b_response, score_a, score_b,
                winner, assessment_a_json, assessment_b_json, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            data["prompt"],
            data["model_a_name"],
            data["model_a_response"],
            data["model_b_name"],
            data["model_b_response"],
            data["score_a"],
            data["score_b"],
            data["winner"],
            json.dumps(data["assessment_a"]),
            json.dumps(data["assessment_b"]),
            json.dumps(data.get("tags", []))
        ))
        conn.commit()
        return cursor.lastrowid


def save_trainer_attempt(report: Dict[str, Any], db_path: str = DB_PATH) -> int:
    """Saves an Evaluator Trainer attempt."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trainer_attempts (
                created_at, case_id, case_title, alignment_score,
                winner_matched, user_winner, expert_winner, critique_notes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            report["case_id"],
            report["case_title"],
            report["overall_alignment_score"],
            1 if report["winner_matched"] else 0,
            report["user_winner"],
            report["expert_winner"],
            json.dumps(
                report["model_a_report"]["critique_notes"] +
                report["model_b_report"]["critique_notes"]
            )
        ))
        conn.commit()
        return cursor.lastrowid


def get_recent_evaluations(limit: int = 10, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Fetches recent evaluations."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, created_at, prompt, model_a_name, model_b_name,
                   score_a, score_b, winner
            FROM evaluations ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

