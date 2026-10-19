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

## ☁️ Deployment on Streamlit Community Cloud

DecisionGuard AI is pre-configured for seamless deployment on [Streamlit Community Cloud](https://streamlit.io/cloud).

### Step-by-Step Deployment Guide

1. **Push your code to GitHub:**
   Ensure your latest code is pushed to your GitHub repository (e.g., `main` branch).
   *(Note: `.env`, `decisionguard.db`, and `.streamlit/secrets.toml` are gitignored and will not be pushed to GitHub.)*

2. **Create New App on Streamlit Cloud:**
   - Log in to [share.streamlit.io](https://share.streamlit.io).
   - Click **"New app"**.
   - Select your repository: `Atharva-kharche/DecisionGuard-AI`.
   - Select the branch: `main`.
   - Set the **Main file path** to:
     ```text
     src/app/streamlit_app.py
     ```
     *(Important: Do not leave as default `streamlit_app.py`; the entry point is located inside `src/app/`)*.

3. **Configure Secrets:**
   - Click **"Advanced settings..."** before deploying (or navigate to **Settings → Secrets** from the app dashboard).
   - Enter your Nebius Token Factory API key in TOML format:
     ```toml
     NEBIUS_API_KEY = "your_actual_nebius_api_key_here"
     ```
   - *(Optional)* If using external vector search with Pinecone, you can also define:
     ```toml
     PINECONE_API_KEY = "your_pinecone_api_key_here"
     PINECONE_INDEX_NAME = "decisionguard"
     ```

4. **Deploy:**
   - Click **"Deploy!"**.
   - Streamlit Community Cloud will automatically install dependencies from `requirements.txt` and launch the app.

### ⚠️ Cloud Storage & Ephemeral Lifecycle Notice

- **Ephemeral Filesystem:** Streamlit Community Cloud runs in containerized environments with an ephemeral disk. The local SQLite database (`decisionguard.db`) and uploaded document sessions exist for the container's active lifecycle and will reset when the app restarts, goes to sleep, or is redeployed.
- **In-Memory Document Handling:** Uploaded evidence files (PDF, DOCX, TXT, MD) and exported PDF reports are processed directly in-memory via byte streams and are never stored on disk, ensuring maximum security and zero local footprint.
- **Persistent Production Storage:** For multi-user or permanent review history across cloud restarts, an external managed database (e.g., Supabase, PostgreSQL) and external vector store (Pinecone) should be connected.

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
