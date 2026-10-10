import sys
import os
import json
sys.path.insert(0, os.path.abspath('src'))
from utils.db import init_db, save_review, get_all_reviews, get_review

def test_db():
    print("Testing DB...")
    init_db()
    results = {
        "overall_status": "PASS",
        "risk_score": 15,
        "executive_summary": "Test",
        "recommendation": "None",
        "findings": []
    }
    
    save_review("test-id-1", "Should we do X?", results)
    
    all_rev = get_all_reviews()
    assert len(all_rev) > 0, "No reviews found"
    
    found = False
    for r in all_rev:
        if r["id"] == "test-id-1":
            found = True
            assert r["decision_question"] == "Should we do X?"
            assert r["risk_score"] == 15
            
    assert found, "Test review not saved"
    print("DB tests passed!")

if __name__ == "__main__":
    test_db()
