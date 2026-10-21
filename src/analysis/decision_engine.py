"""
Decision Analysis Engine for DecisionGuard AI.

This module orchestrates the cross-document review process,
calling the Nebius client with the extracted text to detect gaps,
conflicts, and risks.
"""

from typing import List, Dict, Any
import json
import uuid
from services.nebius_client import NebiusClient

# The prompt used to extract structured decision findings.
DECISION_REVIEW_SYSTEM_PROMPT = """\
You are DecisionGuard AI, an evidence-based decision review intelligence.
Your task is to analyze the provided evidence from multiple documents to evaluate a specific DECISION.
You must extract key requirements (e.g. from policies or specifications) and cross-reference them
against other documents (e.g. vendor proposals, reports) to detect GAPS, CONFLICTS, 
MISSING REQUIREMENTS, and assess RISKS.

Output valid JSON ONLY matching this exact schema:
{
  "decision": "The decision question being evaluated",
  "overall_status": "PASS | PARTIAL | FAIL | NEEDS ATTENTION",
  "executive_summary": "A 2-3 sentence executive summary of the review.",
  "recommendation": "Actionable overall recommendation.",
  "findings": [
    {
      "id": "unique string ID (generate one)",
      "type": "gap" | "conflict" | "missing" | "pass" | "unknown",
      "severity": "critical" | "high" | "medium" | "low" | "none",
      "title": "Short descriptive title (e.g., 'Missing MFA Requirement')",
      "description": "Detailed description of the finding.",
      "policy_evidence": "Exact quote from policy/requirement doc if applicable, else null",
      "vendor_evidence": "Exact quote from vendor/proposal doc if applicable, else null",
      "source_documents": ["List of filenames referenced"],
      "reasoning": "Why this is an issue and how it relates to the decision. Be specific.",
      "risk": "What is the business/security risk of this finding.",
      "recommended_action": "Actionable recommendation to resolve the issue.",
      "confidence": <integer between 0 and 100>
    }
  ]
}

CRITICAL RULES:
0. Do NOT output a thinking process, scratchpad, or any conversational text before the JSON. Your very first character MUST be '{'.
1. Evaluate the specific decision provided by the user.
2. Every finding MUST cite exact evidence from the provided context. Do not invent evidence. Never invent page numbers or quotations.
3. Silence does not automatically mean non-compliant. Distinguish between explicitly non-compliant (conflict/gap), missing or incomplete documentation (missing), and unable to determine (unknown).
4. If a document lacks necessary information, label it 'missing' or 'unknown', not explicitly 'gap' unless the policy strictly forbids omission.
5. Ensure the output is syntactically valid JSON. Do not include markdown code blocks, just the JSON.
"""

class DecisionEngine:
    def __init__(self, nebius_client: NebiusClient):
        self.client = nebius_client

    def run_review(self, all_chunks: List[Dict[str, Any]], decision_question: str) -> dict:
        """Run a comprehensive decision review on all uploaded evidence chunks.
        
        Args:
            all_chunks: List of chunk dictionaries containing 'content' and 'metadata'.
            decision_question: The decision the user is trying to make.
            
        Returns:
            A parsed JSON dictionary containing the structured review.
        """
        if not all_chunks:
            raise ValueError("No evidence provided for decision review.")

        # Construct the context payload
        context_text = f"=== DECISION TO EVALUATE ===\n{decision_question}\n\n"
        context_text += "=== PROVIDED EVIDENCE ===\n\n"
        for i, chunk in enumerate(all_chunks):
            source = chunk["metadata"].get("source", "Unknown")
            idx = chunk["metadata"].get("chunk_index", 0)
            text = chunk["content"]
            context_text += f"[Document: {source} | Chunk: {idx}]\n{text}\n\n"

        context_text += "=== END OF EVIDENCE ===\n"
        context_text += "Please analyze the evidence above and produce the structured JSON review for the decision."

        messages = [
            {"role": "system", "content": DECISION_REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": context_text}
        ]

        # Call the LLM enforcing JSON mode
        try:
            result = self.client.chat(messages, max_tokens=8192, json_mode=True)
            if not isinstance(result, dict):
                raise ValueError(f"Model returned unexpected response type: {type(result).__name__}")
            
            # Ensure findings have IDs if LLM missed it
            raw_findings = result.get("findings", [])
            if not isinstance(raw_findings, list):
                raw_findings = []
                
            valid_findings = []
            for f in raw_findings:
                if isinstance(f, dict):
                    if "id" not in f or not f["id"]:
                        f["id"] = str(uuid.uuid4())
                    valid_findings.append(f)
            result["findings"] = valid_findings
            
            # Phase 6: Deterministic risk scoring
            # Critical=25, High=15, Medium=5, Low=1
            score = 0
            for f in result["findings"]:
                sev = f.get("severity", "").lower()
                typ = f.get("type", "").lower()
                if typ == "pass":
                    continue
                if sev == "critical":
                    score += 25
                elif sev == "high":
                    score += 15
                elif sev == "medium":
                    score += 5
                elif sev == "low":
                    score += 1
            
            result["risk_score"] = min(100, score)
            
            return result
        except (json.JSONDecodeError, ValueError) as e:
            # Handle malformed JSON safely
            return {
                "decision": decision_question,
                "overall_status": "NEEDS ATTENTION",
                "risk_score": 0,
                "executive_summary": "Analysis failed to produce a valid structured response.",
                "recommendation": "Please try running the analysis again or reviewing the documents manually.",
                "findings": []
            }
        except Exception as e:
            # Fallback or pass error to UI to handle
            raise e
