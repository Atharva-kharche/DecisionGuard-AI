from fpdf import FPDF
from datetime import datetime

class PDFReport(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 15)
        self.cell(0, 10, "DecisionGuard AI", ln=True, align="L")
        self.set_font("helvetica", "I", 10)
        self.cell(0, 10, "Evidence-Based Decision Intelligence", ln=True, align="L")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 0, "C")

def safe_text(text: str) -> str:
    if not text:
        return ""
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def generate_pdf_report(decision: str, results: dict) -> bytes:
    pdf = PDFReport()
    pdf.add_page()
    
    # Title
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 15, "Decision Review Report", ln=True, align="C")
    pdf.ln(5)

    # Decision
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Decision:", ln=True)
    pdf.set_font("helvetica", "", 12)
    pdf.multi_cell(0, 10, safe_text(decision))
    pdf.ln(5)

    # Executive Summary
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Executive Summary:", ln=True)
    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 8, safe_text(results.get("executive_summary", "No summary provided.")))
    pdf.ln(5)

    # Overall Status & Risk Score
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Overall Status: {safe_text(results.get('overall_status', 'UNKNOWN'))}", ln=True)
    pdf.cell(0, 10, f"Risk Score: {results.get('risk_score', 'N/A')}/100", ln=True)
    pdf.ln(5)
    
    # Recommendation
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Overall Recommendation:", ln=True)
    pdf.set_font("helvetica", "I", 11)
    pdf.multi_cell(0, 8, safe_text(results.get("recommendation", "N/A")))
    pdf.ln(10)

    # Findings
    findings = results.get("findings", [])
    if findings:
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "Detailed Findings", ln=True)
        pdf.ln(5)

        for i, f in enumerate(findings, 1):
            pdf.set_font("helvetica", "B", 12)
            title = safe_text(f.get('title', 'Untitled'))
            severity = safe_text(f.get('severity', '')).upper()
            pdf.cell(0, 10, f"Finding {i}: {title} [{severity}]", ln=True)
            
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(0, 6, f"Description: {safe_text(f.get('description', ''))}")
            pdf.ln(2)
            
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 6, "Risk:", ln=True)
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(0, 6, safe_text(f.get("risk", "")))
            pdf.ln(2)
            
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 6, "Recommended Action:", ln=True)
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(0, 6, safe_text(f.get("recommended_action", "")))
            pdf.ln(2)
            
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 6, "Reasoning:", ln=True)
            pdf.set_font("helvetica", "I", 10)
            pdf.multi_cell(0, 6, safe_text(f.get("reasoning", "")))
            pdf.ln(2)
            
            p_ev = f.get('policy_evidence')
            v_ev = f.get('vendor_evidence')
            if p_ev:
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(0, 6, "Policy Evidence:", ln=True)
                pdf.set_font("helvetica", "", 9)
                pdf.multi_cell(0, 5, safe_text(p_ev))
            if v_ev:
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(0, 6, "Target Evidence:", ln=True)
                pdf.set_font("helvetica", "", 9)
                pdf.multi_cell(0, 5, safe_text(v_ev))
            
            pdf.ln(10)

    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 10, "Powered by NVIDIA Nemotron via Nebius Token Factory", ln=True, align="C")

    # Output to byte string
    return bytes(pdf.output())
