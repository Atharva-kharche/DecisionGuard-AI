import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "decisionguard.db")

def init_db():
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

def save_review(review_id: str, decision_question: str, results: Dict[str, Any]):
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
    conn.close()

def get_all_reviews() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, decision_question, risk_score, overall_status, results_json FROM reviews ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    
    reviews = []
    for row in rows:
        reviews.append({
            "id": row[0],
            "timestamp": row[1],
            "decision_question": row[2],
            "risk_score": row[3],
            "overall_status": row[4],
            "results": json.loads(row[5])
        })
    return reviews

def get_review(review_id: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT results_json FROM reviews WHERE id = ?", (review_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None
