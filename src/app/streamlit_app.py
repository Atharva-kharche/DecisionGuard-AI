"""
DecisionGuard AI — Phase 4 Streamlit Application
=========================================
Evidence-Based Decision Intelligence
"""

import sys
import os
import time
import uuid

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.abspath(os.path.join(_CURRENT_DIR, ".."))
_ROOT_DIR = os.path.abspath(os.path.join(_SRC_DIR, ".."))
for _p in (_SRC_DIR, _ROOT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
import json
from utils.config import Config
from services.nebius_client import NebiusClient
from models.prompts import DECISIONGUARD_SYSTEM_PROMPT, CONTEXT_INJECTION_TEMPLATE
from rag.engine import RAGEngine
from analysis.decision_engine import DecisionEngine
from utils.pdf_generator import generate_pdf_report
from utils.db import init_db, save_review, get_all_reviews, get_review

# Initialize Database
init_db()

# ───────────────────────────────────────────────────────────────────
#  Page configuration & Custom CSS
# ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DecisionGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #f0f6fc;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
    }

    .glass-card {
        background: linear-gradient(145deg, #1c2128, #161b22);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transition: border-color 0.3s ease;
    }
    .glass-card:hover {
        border-color: #58a6ff;
    }

    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 12px;
    }
    .badge-critical { background: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.4); }
    .badge-high { background: rgba(210, 153, 34, 0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.4); }
    .badge-medium { background: rgba(227, 179, 65, 0.15); color: #e3b341; border: 1px solid rgba(227,179,65,0.4); }
    .badge-low { background: rgba(88, 166, 255, 0.15); color: #58a6ff; border: 1px solid rgba(88,166,255,0.4); }
    .badge-pass { background: rgba(46, 160, 67, 0.15); color: #3fb950; border: 1px solid rgba(46,160,67,0.4); }
    .badge-unknown { background: rgba(139, 148, 158, 0.15); color: #8b949e; border: 1px solid rgba(139,148,158,0.4); }

    .risk-bar-container {
        width: 100%;
        height: 12px;
        background-color: #21262d;
        border-radius: 6px;
        overflow: hidden;
        margin: 15px 0;
    }
    .risk-bar-fill {
        height: 100%;
        transition: width 1s ease-in-out;
    }

    .evidence-quote {
        border-left: 3px solid #58a6ff;
        padding-left: 15px;
        margin: 10px 0;
        color: #8b949e;
        font-family: 'Consolas', monospace;
        font-size: 0.9em;
        background: rgba(88, 166, 255, 0.05);
        padding: 10px;
        border-radius: 0 6px 6px 0;
    }

    .text-subtle {
        color: #8b949e;
        font-size: 0.9rem;
    }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(180deg, #2ea043, #238636);
        color: #ffffff;
        border: 1px solid rgba(240, 246, 252, 0.1);
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(180deg, #3fb950, #2ea043);
        border-color: rgba(240, 246, 252, 0.2);
    }
    
    .status-dot {
        height: 8px; width: 8px; background-color: #3fb950;
        border-radius: 50%; display: inline-block; margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────────
#  Initialization & State
# ───────────────────────────────────────────────────────────────────
config_errors = Config.validate()
if config_errors:
    st.error("⚠️ Configuration Required")
    for err in config_errors:
        st.warning(err)
    st.stop()

@st.cache_resource
def get_nebius_client() -> NebiusClient:
    return NebiusClient()

@st.cache_resource
def get_rag_engine() -> RAGEngine:
    return RAGEngine()

client = get_nebius_client()
rag = get_rag_engine()
decision_engine = DecisionEngine(client)

if "active_view" not in st.session_state:
    st.session_state.active_view = "Dashboard"
if "review_results" not in st.session_state:
    st.session_state.review_results = None
if "decision_question" not in st.session_state:
    st.session_state.decision_question = ""
if "review_step" not in st.session_state:
    st.session_state.review_step = 1

def set_view(view_name):
    st.session_state.active_view = view_name
    if view_name == "New Review":
        st.session_state.review_step = 1
        st.session_state.review_results = None

def get_risk_color(score):
    if score >= 75: return "#f85149" # Critical/High
    if score >= 40: return "#d29922" # Medium
    return "#3fb950" # Low

# ───────────────────────────────────────────────────────────────────
#  Sidebar Navigation
# ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='margin-bottom: 0;'>🛡️ DecisionGuard</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8b949e; font-size: 0.8rem; margin-top: 0;'>Evidence-Based Decision Intelligence</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.button("➕ New Review", on_click=set_view, args=("New Review",), use_container_width=True, type="primary")
    st.button("📊 Dashboard", on_click=set_view, args=("Dashboard",), use_container_width=True)
    st.button("⚖️ Saved Reviews", on_click=set_view, args=("Reviews",), use_container_width=True)
    st.button("📁 Evidence Library", on_click=set_view, args=("Evidence Library",), use_container_width=True)
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("### System Status")
    
    if "api_status" not in st.session_state:
        # Check health only once to avoid freezing the UI on every rerun
        try:
            is_ok = client.health_check()
            st.session_state.api_status = "Online" if is_ok else "Offline"
        except Exception:
            st.session_state.api_status = "Offline"
            
    if st.session_state.api_status == "Online":
        st.markdown("<div class='status-dot'></div> <span>Nemotron Online</span>", unsafe_allow_html=True)
        st.markdown("<div class='status-dot'></div> <span>Token Factory Connected</span>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='status-dot' style='background-color: #f85149;'></div> <span style='color: #f85149;'>Nemotron Offline</span>", unsafe_allow_html=True)
        if st.button("Retry Connection"):
            del st.session_state.api_status
            st.rerun()
            
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption("Powered by<br>**NVIDIA Nemotron**<br>via Nebius Token Factory", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────────
#  Views
# ───────────────────────────────────────────────────────────────────
view = st.session_state.active_view

if view == "Dashboard":
    st.markdown("<h1>Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='text-subtle'>Turn scattered documents into evidence-backed decisions.</p>", unsafe_allow_html=True)
    
    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        st.button("Start New Review", on_click=set_view, args=("New Review",), type="primary", use_container_width=True)
    with col2:
        if st.button("Interactive Demo", use_container_width=True):
            # Load Demo Mode
            with st.spinner("Loading demo evidence..."):
                rag.clear()
                demo_policy = b"SECURITY POLICY: All employees must use multi-factor authentication (MFA) for remote access. Passwords must be at least 14 characters. Incident reporting must happen within 24 hours."
                demo_vendor = b"VENDOR PROPOSAL: The system supports username and password authentication. Passwords are 8 characters minimum. We do not support MFA currently. Incidents are reviewed monthly."
                rag.ingest_bytes(demo_policy, "Company_Security_Policy.txt")
                rag.ingest_bytes(demo_vendor, "Vendor_Security_Proposal.txt")
                st.session_state.decision_question = "Should we approve this vendor for production access?"
                st.session_state.review_step = 3 # jump to analysis
                st.session_state.active_view = "New Review"
                st.rerun()

    st.markdown("### Recent Saved Reviews")
    recent_reviews = get_all_reviews()
    if recent_reviews:
        for r in recent_reviews[:5]:
            score = r.get("risk_score", 0)
            color = get_risk_color(score)
            st.markdown(f"""
            <div class="glass-card" style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin:0;">{r.get('decision_question', 'Decision Review')}</h4>
                        <p class="text-subtle" style="margin:0;">Date: {r.get('timestamp')[:10]} | Risk Score: <span style="color:{color}; font-weight:bold;">{score}/100</span></p>
                    </div>
                    <div style="text-align: right;">
                        <span class="badge" style="background: {color}20; color: {color}; border: 1px solid {color}40;">{r.get('overall_status', 'COMPLETED')}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Open Review", key=f"open_{r['id']}"):
                st.session_state.review_results = r['results']
                st.session_state.decision_question = r['decision_question']
                set_view("Results")
                st.rerun()
    else:
        st.markdown("""
        <div class="glass-card" style="text-align: center; padding: 40px;">
            <h3 style="color: #8b949e;">No decision reviews yet.</h3>
            <p style="color: #8b949e; margin-bottom: 20px;">Upload documents and evaluate a decision to see your results here.</p>
        </div>
        """, unsafe_allow_html=True)


elif view == "New Review":
    st.markdown("<h1>New Decision Review</h1>", unsafe_allow_html=True)
    
    # Progress indicator
    step = st.session_state.review_step
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; margin-bottom: 30px; font-weight: bold; color: #8b949e;">
        <span style="color: {'#58a6ff' if step >= 1 else '#8b949e'};">1. Evidence</span>
        <span>→</span>
        <span style="color: {'#58a6ff' if step >= 2 else '#8b949e'};">2. Decision</span>
        <span>→</span>
        <span style="color: {'#58a6ff' if step >= 3 else '#8b949e'};">3. Analysis</span>
        <span>→</span>
        <span style="color: {'#58a6ff' if step >= 4 else '#8b949e'};">4. Results</span>
    </div>
    """, unsafe_allow_html=True)
    
    if step == 1:
        st.markdown("""
        <div class="glass-card">
            <h3>Step 1: Upload Evidence</h3>
            <p class="text-subtle">DecisionGuard evaluates your decision against real documents. <br><b>Best results:</b> Include at least one requirements document (e.g., Policy, Contract Template) and one target document (e.g., Proposal, Assessment).</p>
        </div>
        """, unsafe_allow_html=True)
        
        colA, colB = st.columns([3, 1])
        with colA:
            st.info("Supported formats: PDF, DOCX, TXT, MD. Max limit: 200MB per file.")
            uploaded_files = st.file_uploader("Upload Evidence", accept_multiple_files=True, label_visibility="collapsed")
            
            # Sync uploaded files with RAG engine
            if uploaded_files is not None:
                active_names = [f.name for f in uploaded_files]
                current_docs = rag.document_names
                
                # If a file was removed or it's a completely new set, we clear and re-ingest active ones
                if set(active_names) != set(current_docs):
                    rag.clear()
                    for f in uploaded_files:
                        f.seek(0)
                        rag.ingest_bytes(f.read(), f.name)
        with colB:
            if st.button("Clear All Uploads", use_container_width=True):
                rag.clear()
                st.rerun()
                
        if rag.is_ready:
            st.markdown("### Uploaded Documents")
            for doc in rag.document_names:
                role = "Policy/Requirement" if any(x in doc.lower() for x in ['policy', 'req', 'standard']) else "Target Document"
                st.markdown(f"""
                <div class="glass-card" style="padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between;">
                    <div>
                        <strong>📄 {doc}</strong><br>
                        <span class="text-subtle">Status: Ready</span>
                    </div>
                    <div>
                        <span class="badge badge-medium" style="margin:0;">Assumed Role: {role}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Continue to Decision", type="primary"):
                st.session_state.review_step = 2
                st.rerun()

    elif step == 2:
        st.markdown("""
        <div class="glass-card">
            <h3>Step 2: Define Decision</h3>
            <p class="text-subtle">What decision are you evaluating?</p>
        </div>
        """, unsafe_allow_html=True)
        
        template = st.selectbox("Decision Template", [
            "Custom",
            "Vendor Security Approval: Should we approve this vendor for production access?",
            "Contract Compliance Review: Does this contract meet all our compliance requirements?",
            "Policy Compliance Audit: Is the project fully compliant with our internal policies?"
        ])
        
        default_val = st.session_state.decision_question
        if template != "Custom" and not default_val:
            default_val = template.split(": ")[1]
            
        dq = st.text_area("Decision Question", value=default_val, placeholder="e.g. Should we approve this vendor for production access?")
        
        st.info("The system will extract all requirements from your documents, cross-reference them against the target documents, identify gaps or missing information, calculate a risk score, and generate a recommendation.")
        
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Back"):
                st.session_state.review_step = 1
                st.rerun()
        with col2:
            if st.button("Analyze Decision", type="primary"):
                if not dq:
                    st.error("Please enter a decision question.")
                else:
                    st.session_state.decision_question = dq
                    st.session_state.review_step = 3
                    st.rerun()

    elif step == 3:
        st.markdown("### Analyzing Decision...")
        st.info("Extracting requirements, cross-referencing documents, and assessing risk using NVIDIA Nemotron...")
        
        with st.spinner("Connecting to Nebius Token Factory..."):
            try:
                results = decision_engine.run_review(rag.get_all_chunks(), st.session_state.decision_question)
                st.session_state.review_results = results
                
                # Save to persistent storage
                review_id = str(uuid.uuid4())
                save_review(review_id, st.session_state.decision_question, results)
                
                st.success("✓ Analysis Complete!")
                st.session_state.review_step = 4
                set_view("Results")
                st.rerun()
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                if st.button("Retry"):
                    st.session_state.review_step = 2
                    st.rerun()


elif view == "Results":
    res = st.session_state.review_results
    if not res:
        st.warning("No review results found. Start a new review.")
        st.button("Start Review", on_click=set_view, args=("New Review",))
    else:
        st.markdown(f"<p class='text-subtle' style='margin-bottom:0;'>DECISION REVIEW</p>", unsafe_allow_html=True)
        st.markdown(f"<h2>{res.get('decision', st.session_state.decision_question)}</h2>", unsafe_allow_html=True)
        st.caption("⚠️ **Disclaimer:** This AI-generated analysis is for informational purposes only and does not constitute formal legal, compliance, or security certification.")
        st.divider()

        score = res.get("risk_score", 0)
        color = get_risk_color(score)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center;">
                <h3 style="color: {color};">DETERMINISTIC RISK SCORE: {score}/100</h3>
                <div class="risk-bar-container">
                    <div class="risk-bar-fill" style="width: {score}%; background-color: {color};"></div>
                </div>
                <p><strong>Recommendation:</strong> {res.get('recommendation', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="glass-card">
                <h3>Executive Summary</h3>
                <p>{res.get('executive_summary', '')}</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            findings = res.get('findings', [])
            crit = len([f for f in findings if f.get('severity', '').lower() == 'critical'])
            high = len([f for f in findings if f.get('severity', '').lower() == 'high'])
            med = len([f for f in findings if f.get('severity', '').lower() == 'medium'])
            passed = len([f for f in findings if f.get('type', '').lower() == 'pass'])
            
            st.markdown(f"""
            <div class="glass-card">
                <h4>Findings Summary</h4>
                <table style="width: 100%; text-align: left; margin-top: 15px;">
                    <tr style="color: #f85149;"><th>Critical</th><td style="text-align:right; font-weight:bold;">{crit}</td></tr>
                    <tr style="color: #d29922;"><th>High</th><td style="text-align:right; font-weight:bold;">{high}</td></tr>
                    <tr style="color: #e3b341;"><th>Medium</th><td style="text-align:right; font-weight:bold;">{med}</td></tr>
                    <tr style="color: #3fb950;"><th>Passed</th><td style="text-align:right; font-weight:bold;">{passed}</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("ℹ️ How is the Risk Score calculated?"):
                st.markdown("The score is deterministically generated based on exact findings. Base scale: Critical (+25), High (+15), Medium (+5), Low (+1). Capped at 100.")
            
            # PDF Report Export
            pdf_bytes = generate_pdf_report(res.get('decision', st.session_state.decision_question), res)
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_bytes,
                file_name="DecisionGuard_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        st.markdown("### Interactive Findings")
        
        # Search & Filter
        scol1, scol2 = st.columns([3, 1])
        with scol1:
            search_query = st.text_input("Search findings...", placeholder="e.g. authentication, VPN", label_visibility="collapsed")
        with scol2:
            filter_type = st.selectbox("Filter", ["All Risks", "Critical & High", "Passed", "Missing Info"], label_visibility="collapsed")
        
        display_findings = []
        for f in findings:
            sev = f.get('severity', '').lower()
            typ = f.get('type', '').lower()
            title = f.get('title', '').lower()
            desc = f.get('description', '').lower()
            
            # Text search filter
            if search_query and search_query.lower() not in title and search_query.lower() not in desc:
                continue
                
            # Dropdown filter
            if filter_type == "All Risks" and typ not in ["pass", "none"]:
                display_findings.append(f)
            elif filter_type == "Critical & High" and sev in ["critical", "high"]:
                display_findings.append(f)
            elif filter_type == "Passed" and typ == "pass":
                display_findings.append(f)
            elif filter_type == "Missing Info" and typ in ["missing", "unknown"]:
                display_findings.append(f)
                
        if not display_findings:
            st.info("No findings match the current filters.")
                
        for f in display_findings:
            sev = f.get('severity', 'low').lower()
            typ = f.get('type', 'gap').lower()
            
            badge_class = f"badge-{sev}"
            if typ == 'pass': badge_class = "badge-pass"
            elif typ in ['missing', 'unknown']: badge_class = "badge-unknown"
            
            st.markdown(f"""
            <div class="glass-card" style="padding-bottom: 10px;">
                <span class="badge {badge_class}">{sev.upper()} | {typ.upper()}</span>
                <h4 style="margin-top: 5px;">{f.get('title', 'Finding')}</h4>
                <p>{f.get('description', '')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("View Evidence & Analysis"):
                st.markdown(f"**Risk:** {f.get('risk', '')}")
                st.markdown(f"**Reasoning:** {f.get('reasoning', '')}")
                st.markdown(f"**Recommended Action:** {f.get('recommended_action', '')}")
                
                # Side-by-side Evidence Comparison
                ecol1, ecol2 = st.columns(2)
                with ecol1:
                    if f.get('policy_evidence'):
                        st.markdown("**Policy Requirement:**")
                        st.markdown(f"<div class='evidence-quote'>{f.get('policy_evidence')}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("**Policy Requirement:**")
                        st.markdown(f"<div class='evidence-quote' style='color:#8b949e; font-style:italic;'>Not specified or missing</div>", unsafe_allow_html=True)
                with ecol2:
                    if f.get('vendor_evidence'):
                        st.markdown("**Target Evidence:**")
                        st.markdown(f"<div class='evidence-quote'>{f.get('vendor_evidence')}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("**Target Evidence:**")
                        st.markdown(f"<div class='evidence-quote' style='color:#8b949e; font-style:italic;'>No evidence found in target documents</div>", unsafe_allow_html=True)
                
                sources = f.get('source_documents', [])
                if sources:
                    st.caption(f"Sources: {', '.join(sources)} | Confidence: {f.get('confidence', 0)}%")
                else:
                    st.caption(f"Confidence: {f.get('confidence', 0)}%")
                    
        st.divider()
        st.markdown("### Remediation Checklist")
        st.markdown("<p class='text-subtle'>Actionable steps to resolve findings.</p>", unsafe_allow_html=True)
        checklist = [f.get("recommended_action") for f in findings if f.get("type") not in ["pass"] and f.get("recommended_action")]
        if checklist:
            for item in checklist:
                st.checkbox(item, key=f"chk_{uuid.uuid4().hex[:8]}")
        else:
            st.info("No required actions identified.")
                
        st.divider()
        st.markdown("### Ask DecisionGuard")
        st.markdown("<p class='text-subtle'>Ask questions about this decision and its evidence. The AI Assistant has access to the full document context.</p>", unsafe_allow_html=True)
        query = st.text_input("Question", placeholder="Why is this high risk?", label_visibility="collapsed")
        if st.button("Ask AI Assistant"):
            if not query:
                st.warning("Please enter a question.")
            else:
                with st.spinner("Querying Nemotron..."):
                    retrieved = rag.retrieve(query, top_k=3)
                    context_text = ""
                    for item in retrieved:
                        context_text += f"Document: {item['metadata'].get('source')} \n{item['content']}\n\n"
                    
                    injected = CONTEXT_INJECTION_TEMPLATE.format(context=context_text)
                    ans = client.chat([
                        {"role": "system", "content": DECISIONGUARD_SYSTEM_PROMPT},
                        {"role": "user", "content": injected + f"\n\nQuestion: {query}"}
                    ])
                    st.markdown("#### Answer")
                    st.info(ans)
                    st.markdown("**Sources:**")
                    for item in retrieved:
                        st.caption(f"📄 {item['metadata'].get('source')}")

elif view == "Reviews":
    st.markdown("<h1>Historical Reviews</h1>", unsafe_allow_html=True)
    all_rev = get_all_reviews()
    if all_rev:
        for r in all_rev:
            score = r.get("risk_score", 0)
            color = get_risk_color(score)
            st.markdown(f"""
            <div class="glass-card" style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin:0;">{r.get('decision_question', 'Decision Review')}</h4>
                        <p class="text-subtle" style="margin:0;">Date: {r.get('timestamp')} | Risk Score: <span style="color:{color}; font-weight:bold;">{score}/100</span></p>
                    </div>
                    <div style="text-align: right;">
                        <span class="badge" style="background: {color}20; color: {color}; border: 1px solid {color}40; margin-bottom: 5px;">{r.get('overall_status', 'COMPLETED')}</span><br>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Open Review", key=f"open_hist_{r['id']}"):
                st.session_state.review_results = r['results']
                st.session_state.decision_question = r['decision_question']
                set_view("Results")
                st.rerun()
    else:
        st.markdown("<p class='text-subtle'>No reviews recorded yet.</p>", unsafe_allow_html=True)

elif view == "Evidence Library":
    st.markdown("<h1>Evidence Explorer</h1>", unsafe_allow_html=True)
    if rag.is_ready:
        for doc in rag.document_names:
            st.markdown(f"""
            <div class="glass-card" style="padding: 15px; margin-bottom: 10px;">
                <strong>📄 {doc}</strong>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<p class='text-subtle'>No documents uploaded yet.</p>", unsafe_allow_html=True)
