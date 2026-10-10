# DecisionGuard AI

**Evidence-Based Decision Intelligence**

DecisionGuard AI transforms scattered organizational documents—policies, contracts, vendor proposals, and technical requirements—into structured, auditable decision intelligence. It cross-references source materials, detects gaps and contradictions, and produces an actionable, deterministic risk score powered by NVIDIA Nemotron and Nebius Token Factory.

---

## 🎯 Key Features

1. **Guided Decision Workflow:** A seamless 4-step wizard (Evidence -> Decision -> Analysis -> Results).
2. **Interactive Evidence Panels:** Expandable finding cards that juxtapose explicit policy requirements against the target document's text.
3. **Deterministic Risk Scoring:** A transparent calculation mapping the severity of AI-detected findings to an objective 0-100 score, avoiding opaque LLM hallucinated scores.
4. **Persistent Review History:** All completed analyses are saved locally using SQLite, enabling retrospective audits across browser sessions.
5. **PDF Report Export:** Instantly generate professional, executive-ready PDF summaries of the decision review.
6. **Ask DecisionGuard:** An integrated conversational agent capable of answering follow-up questions strictly grounded in the ingested evidence.
7. **Interactive Demo:** A one-click onboarding experience pre-loaded with realistic security policies and vendor proposals. To run the demo, click "Interactive Demo" on the main Dashboard.

## 🏗️ Architecture & Data Flow

1. **Ingestion & Processing:** Documents (PDF, DOCX, TXT, MD) are chunked via Langchain and embedded into an in-memory or vector store.
2. **Context Assembly:** Relevant textual chunks are assembled based on the user's defined decision question.
3. **Nemotron Inference:** The context is securely dispatched to NVIDIA Nemotron (via Nebius Token Factory), enforcing a strict structural JSON schema.
4. **Evaluation & Presentation:** The Streamlit frontend parses findings, calculates risk deterministically, persists data to SQLite, and renders the dynamic dashboard.

## 📋 Prerequisites

- Python 3.9+
- Nebius Token Factory API Key (`NEBIUS_API_KEY`)

## 🛠️ Installation (Windows)

1. **Clone the repository:**
   ```powershell
   git clone <repository_url>
   cd DecisionGuard-AI
   ```

2. **Set up a virtual environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Copy the sample environment file and insert your key.
   ```powershell
   cp .env.example .env
   # Edit .env and set NEBIUS_API_KEY="..."
   ```
   *(Note: The `.env` file and `decisionguard.db` database are excluded from version control for security.)*

## 🚀 Running the Application

Start the interactive Streamlit dashboard:

```powershell
python -m streamlit run src/app/streamlit_app.py
```
*The application will automatically open in your default browser at `http://localhost:8501`.*

## 🧪 Running Tests

A comprehensive test suite is included to validate RAG ingestion, deterministic scoring, and LLM output parsing.

Run the pipeline integration test (requires API key):
```powershell
python test_pipeline.py
```

Run the SQLite persistence test:
```powershell
python test_db.py
```

## 🔒 Security & Privacy Considerations

- **Keys are protected:** The `.env` config is gitignored. The system never logs or exposes API keys in the UI.
- **Data Persistence:** Evidence documents are temporarily loaded into memory during active sessions. Only the structured JSON findings (and exact evidence quotes) are saved long-term in the local SQLite database.
- **Model Grounding:** The engine is explicitly prompted to categorize "missing" information rather than inventing non-compliance, and never hallucinates page numbers or source names.

## ⏳ Current Limitations

- **Context Window:** Exceeding the maximum token limit of the LLM with massive, non-targeted documents will result in truncation or API failures. Pre-filtering massive PDFs is recommended.
- **Cloud Vector Store:** Currently optimized for local/in-memory inference; large-scale deployments should activate Pinecone/FAISS persistence.
- **OCR:** Scanned images within PDFs currently require external OCR before ingestion.

---
*Powered by NVIDIA Nemotron & Nebius Token Factory.*
