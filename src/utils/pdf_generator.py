from fpdf import FPDF
from datetime import datetime
from typing import Any

class PDFReport(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 15)
        self.cell(0, 10, "DecisionGuard AI", new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_font("helvetica", "I", 10)
        self.cell(0, 10, "Evidence-Based Decision Intelligence", new_x="LMARGIN", new_y="NEXT", align="L")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")

def safe_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def generate_pdf_report(decision: str, results: dict) -> bytes:
    results = results if isinstance(results, dict) else {}
    pdf = PDFReport()
    pdf.add_page()
    
    # Title
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 15, "Decision Review Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Decision
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Decision:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 12)
    pdf.multi_cell(0, 10, safe_text(decision or "No decision specified"))
    pdf.ln(5)

    # Executive Summary
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Executive Summary:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 8, safe_text(results.get("executive_summary", "No summary provided.")))
    pdf.ln(5)

    # Overall Status & Risk Score
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Overall Status: {safe_text(results.get('overall_status', 'UNKNOWN'))}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"Risk Score: {results.get('risk_score', 'N/A')}/100", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Recommendation
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Overall Recommendation:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "I", 11)
    pdf.multi_cell(0, 8, safe_text(results.get("recommendation", "N/A")))
    pdf.ln(10)

    # Findings
    raw_findings = results.get("findings", [])
    findings = [f for f in raw_findings if isinstance(f, dict)] if isinstance(raw_findings, list) else []
    if findings:
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "Detailed Findings", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        for i, f in enumerate(findings, 1):
            pdf.set_font("helvetica", "B", 12)
            title = safe_text(f.get('title', 'Untitled'))
            severity = safe_text(f.get('severity', '')).upper()
            pdf.cell(0, 10, f"Finding {i}: {title} [{severity}]", new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(0, 6, f"Description: {safe_text(f.get('description', ''))}")
            pdf.ln(2)
            
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 6, "Risk:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(0, 6, safe_text(f.get("risk", "")))
            pdf.ln(2)
            
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 6, "Recommended Action:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(0, 6, safe_text(f.get("recommended_action", "")))
            pdf.ln(2)
            
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 6, "Reasoning:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "I", 10)
            pdf.multi_cell(0, 6, safe_text(f.get("reasoning", "")))
            pdf.ln(2)
            
            p_ev = f.get('policy_evidence')
            v_ev = f.get('vendor_evidence')
            if p_ev:
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(0, 6, "Policy Evidence:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("helvetica", "", 9)
                pdf.multi_cell(0, 5, safe_text(p_ev))
            if v_ev:
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(0, 6, "Target Evidence:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("helvetica", "", 9)
                pdf.multi_cell(0, 5, safe_text(v_ev))
            
            pdf.ln(10)

    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 10, "Powered by NVIDIA Nemotron via Nebius Token Factory", new_x="LMARGIN", new_y="NEXT", align="C")

    # Output to byte string
    return bytes(pdf.output())
