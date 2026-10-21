import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "decisionguard.db"))

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                timestamp DATETIME,
                decision_question TEXT,
                risk_score INTEGER,
                overall_status TEXT,
                results_json TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as exc:
        # Non-fatal: log warning so app can continue running even on restricted filesystems
        print(f"Warning: Database initialization failed: {exc}")

def save_review(review_id: str, decision_question: str, results: Dict[str, Any]):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO reviews (id, timestamp, decision_question, risk_score, overall_status, results_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            review_id,
            datetime.now().isoformat(),
            decision_question,
            results.get("risk_score", 0),
            results.get("overall_status", "UNKNOWN"),
            json.dumps(results)
        ))
        conn.commit()
    finally:
        if conn:
            conn.close()

def get_all_reviews() -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, decision_question, risk_score, overall_status, results_json FROM reviews ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        
        reviews = []
        for row in rows:
            try:
                parsed_results = json.loads(row[5])
            except Exception:
                parsed_results = {}
            reviews.append({
                "id": row[0],
                "timestamp": row[1],
                "decision_question": row[2],
                "risk_score": row[3],
                "overall_status": row[4],
                "results": parsed_results
            })
        return reviews
    except Exception as exc:
        print(f"Warning: Failed to fetch reviews: {exc}")
        return []
    finally:
        if conn:
            conn.close()

def get_review(review_id: str) -> Dict[str, Any] | None:
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT results_json FROM reviews WHERE id = ?", (review_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
    except Exception as exc:
        print(f"Warning: Failed to fetch review {review_id}: {exc}")
        return None
    finally:
        if conn:
            conn.close()
