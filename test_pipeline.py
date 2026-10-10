import sys
import os
import json

sys.path.insert(0, os.path.abspath('src'))
from dotenv import load_dotenv
load_dotenv()

try:
    from rag.engine import RAGEngine
    from services.nebius_client import NebiusClient
    from analysis.decision_engine import DecisionEngine
    
    print("Testing Pipeline...")
    rag = RAGEngine()
    
    policy_text = b"COMPANY POLICY: All employees must use multi-factor authentication (MFA). Passwords must be at least 12 characters. Security incidents must be reported within 24 hours. A VPN is required for remote access."
    vendor_text = b"VENDOR PROPOSAL: Users authenticate using username and password. Passwords require at least 8 characters. Security incidents are reviewed during monthly meetings."
    
    rag.ingest_bytes(policy_text, "Company_Policy.txt")
    rag.ingest_bytes(vendor_text, "Vendor_Proposal.txt")
    
    client = NebiusClient()
    engine = DecisionEngine(client)
    
    print("Running Decision Review (calling Nebius Token Factory)...")
    result = engine.run_review(rag.get_all_chunks(), "Should we approve this vendor?")
    
    print("=== REVIEW RESULT ===")
    print(json.dumps(result, indent=2))
    
    print("\nVerifying Gaps...")
    findings_str = json.dumps(result)
    assert "MFA" in findings_str or "multi-factor" in findings_str, "MFA gap not found!"
    assert "12" in findings_str and "8" in findings_str, "Password conflict not found!"
    assert "24 hours" in findings_str or "monthly" in findings_str, "Incident reporting gap not found!"
    
    print("ALL TESTS PASSED")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("TEST FAILED", e)
