"""
Offline Resilience & Error Handling Test Suite for DecisionGuard AI.

Validates:
1. Missing credentials handling
2. Transient error retries (429 RateLimit, 503 ServerError, APITimeout)
3. Permanent error fast-fail (401 Auth, 400 BadRequest)
4. API key scrubbing from error messages
5. Malformed LLM response fallback
6. Document processing edge cases (empty, corrupted, encrypted)
7. Multi-user session isolation
8. Database failure resilience
9. PDF generator null/invalid input resilience
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath('src'))

from openai import (
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
    BadRequestError,
    InternalServerError,
)

from utils.config import Config
from services.nebius_client import NebiusClient
from analysis.decision_engine import DecisionEngine
from rag.engine import RAGEngine
from rag.loaders import extract_text_from_bytes
from utils.db import init_db, save_review, get_all_reviews, get_review
from utils.pdf_generator import generate_pdf_report


from langchain_core.embeddings import Embeddings


class MockEmbeddings(Embeddings):
    """Mock embeddings implementation compatible with LangChain vector stores."""
    def embed_documents(self, texts):
        return [[0.1] * 384 for _ in texts]

    def embed_query(self, text):
        return [0.1] * 384


class TestDecisionGuardResilience(unittest.TestCase):

    def setUp(self):
        # Speed up retry backoff in tests
        NebiusClient.INITIAL_RETRY_DELAY = 0.001

    # ── 1. Credentials Validation ──────────────────────────────────

    def test_missing_credentials_validation(self):
        with patch.dict(os.environ, {"NEBIUS_API_KEY": ""}, clear=True):
            self.assertFalse(Config.is_nebius_configured())
            errors = Config.validate()
            self.assertGreater(len(errors), 0)
            self.assertIn("NEBIUS_API_KEY is not set", errors[0])

            # Client instantiation without key must raise ValueError
            with self.assertRaises(ValueError) as ctx:
                NebiusClient()
            self.assertIn("NEBIUS_API_KEY is not set", str(ctx.exception))

    # ── 2. Transient Retries & Backoff ─────────────────────────────

    def test_api_rate_limit_retry_success(self):
        """Verify 429 RateLimitError triggers retries and succeeds if resolved."""
        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success after rate limit"))]

        mock_err_response = MagicMock(status_code=429, headers={})
        rate_err = RateLimitError("Rate limit exceeded", response=mock_err_response, body=None)

        # Fail twice with 429, then succeed on 3rd attempt
        mock_openai.chat.completions.create.side_effect = [rate_err, rate_err, mock_response]

        client = NebiusClient(client=mock_openai)
        reply = client.chat([{"role": "user", "content": "Hi"}])

        self.assertEqual(reply, "Success after rate limit")
        self.assertEqual(mock_openai.chat.completions.create.call_count, 3)

    def test_api_rate_limit_exhausted(self):
        """Verify 429 raises clear error when bounded retries are exhausted."""
        mock_openai = MagicMock()
        mock_err_response = MagicMock(status_code=429, headers={})
        rate_err = RateLimitError("Rate limit exceeded", response=mock_err_response, body=None)
        mock_openai.chat.completions.create.side_effect = rate_err

        client = NebiusClient(client=mock_openai)
        with self.assertRaises(RuntimeError) as ctx:
            client.chat([{"role": "user", "content": "Hi"}])
        self.assertIn("rate limit exceeded", str(ctx.exception).lower())
        self.assertEqual(mock_openai.chat.completions.create.call_count, 3)

    def test_api_timeout_retry(self):
        """Verify APITimeoutError triggers retries."""
        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success after timeout"))]
        timeout_err = APITimeoutError(request=MagicMock())

        mock_openai.chat.completions.create.side_effect = [timeout_err, mock_response]

        client = NebiusClient(client=mock_openai)
        reply = client.chat([{"role": "user", "content": "Hi"}])

        self.assertEqual(reply, "Success after timeout")
        self.assertEqual(mock_openai.chat.completions.create.call_count, 2)

    def test_api_server_error_retry(self):
        """Verify 503 InternalServerError triggers retries."""
        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success after 503"))]
        mock_err_resp = MagicMock(status_code=503, headers={})
        server_err = InternalServerError("Service unavailable", response=mock_err_resp, body=None)

        mock_openai.chat.completions.create.side_effect = [server_err, mock_response]

        client = NebiusClient(client=mock_openai)
        reply = client.chat([{"role": "user", "content": "Hi"}])

        self.assertEqual(reply, "Success after 503")
        self.assertEqual(mock_openai.chat.completions.create.call_count, 2)

    # ── 3. Permanent Error Fast-Fail ────────────────────────────────

    def test_authentication_error_fails_fast(self):
        """Verify 401 AuthenticationError does NOT retry and fails immediately."""
        mock_openai = MagicMock()
        mock_err_resp = MagicMock(status_code=401, headers={})
        auth_err = AuthenticationError("Invalid key", response=mock_err_resp, body=None)
        mock_openai.chat.completions.create.side_effect = auth_err

        client = NebiusClient(client=mock_openai)
        with self.assertRaises(RuntimeError) as ctx:
            client.chat([{"role": "user", "content": "Hi"}])

        self.assertIn("Authentication failed", str(ctx.exception))
        # Must fail immediately on attempt 1 without retry
        self.assertEqual(mock_openai.chat.completions.create.call_count, 1)

    def test_bad_request_fails_fast(self):
        """Verify 400 BadRequestError does not retry."""
        mock_openai = MagicMock()
        mock_err_resp = MagicMock(status_code=400, headers={})
        bad_req = BadRequestError("Invalid model parameter", response=mock_err_resp, body=None)
        mock_openai.chat.completions.create.side_effect = bad_req

        client = NebiusClient(client=mock_openai)
        with self.assertRaises(RuntimeError) as ctx:
            client.chat([{"role": "user", "content": "Hi"}])

        self.assertIn("rejected", str(ctx.exception))
        self.assertEqual(mock_openai.chat.completions.create.call_count, 1)

    # ── 4. Secret Sanitization ─────────────────────────────────────

    def test_secret_sanitization(self):
        fake_key = "secret_nebius_key_xyz_12345"
        with patch.dict(os.environ, {"NEBIUS_API_KEY": fake_key}):
            raw_error = f"Error calling api with key {fake_key} and Bearer token123456"
            sanitized = NebiusClient._sanitize_error(raw_error)
            self.assertNotIn(fake_key, sanitized)
            self.assertIn("[REDACTED_API_KEY]", sanitized)
            self.assertIn("Bearer [REDACTED]", sanitized)

    # ── 5. Malformed JSON Fallback ──────────────────────────────────

    def test_malformed_json_fallback_in_decision_engine(self):
        mock_client = MagicMock()
        mock_client.chat.return_value = "This is not JSON at all!"

        engine = DecisionEngine(mock_client)
        dummy_chunks = [{"content": "Policy text", "metadata": {"source": "p.txt"}}]
        
        result = engine.run_review(dummy_chunks, "Should we proceed?")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("overall_status"), "NEEDS ATTENTION")
        self.assertIn("findings", result)
        self.assertEqual(result.get("risk_score"), 0)

    def test_non_dict_json_fallback_in_decision_engine(self):
        mock_client = MagicMock()
        mock_client.chat.return_value = ["item1", "item2"] # not a dict

        engine = DecisionEngine(mock_client)
        dummy_chunks = [{"content": "Policy text", "metadata": {"source": "p.txt"}}]
        
        result = engine.run_review(dummy_chunks, "Should we proceed?")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("overall_status"), "NEEDS ATTENTION")

    # ── 6. Document Processing Edge Cases ──────────────────────────

    def test_empty_document_handling(self):
        with self.assertRaises(ValueError) as ctx:
            extract_text_from_bytes(b"", "empty.txt")
        self.assertIn("empty", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            extract_text_from_bytes(b"   \n\t  ", "blank.txt")
        self.assertIn("empty", str(ctx.exception).lower())

    def test_corrupted_docx_handling(self):
        with self.assertRaises(ValueError) as ctx:
            extract_text_from_bytes(b"corrupted zip bytes", "corrupted.docx")
        self.assertIn("corrupted", str(ctx.exception).lower())

    def test_unsupported_file_extension(self):
        with self.assertRaises(ValueError) as ctx:
            extract_text_from_bytes(b"some content", "data.xyz")
        self.assertIn("unsupported", str(ctx.exception).lower())

    # ── 7. Session Isolation ────────────────────────────────────────

    def test_session_isolation(self):
        """Verify that two RAGEngine instances with shared embeddings stay strictly isolated."""
        mock_embeddings = MockEmbeddings()

        session_a = RAGEngine(embeddings=mock_embeddings)
        session_b = RAGEngine(embeddings=mock_embeddings)

        # Ingest doc into Session A
        session_a.ingest_bytes(b"Session A secret document content", "SessionA_Policy.txt")
        self.assertEqual(session_a.document_count, 1)
        self.assertEqual(session_b.document_count, 0)
        self.assertIn("SessionA_Policy.txt", session_a.document_names)
        self.assertNotIn("SessionA_Policy.txt", session_b.document_names)

        # Ingest doc into Session B
        session_b.ingest_bytes(b"Session B vendor proposal content", "SessionB_Vendor.txt")
        self.assertEqual(session_b.document_count, 1)
        self.assertEqual(session_a.document_count, 1)

        # Vector stores and FAISS indexes must be independent objects
        self.assertIsNot(session_a.store, session_b.store)
        self.assertIsNot(session_a.store.local_faiss, session_b.store.local_faiss)
        self.assertIsNot(session_a.store.local_faiss.index, session_b.store.local_faiss.index)

        # Verify chunk isolation prior to clearing
        chunks_a = session_a.get_all_chunks()
        chunks_b = session_b.get_all_chunks()
        self.assertEqual(len(chunks_a), 1)
        self.assertEqual(len(chunks_b), 1)
        self.assertEqual(chunks_a[0]["metadata"]["source"], "SessionA_Policy.txt")
        self.assertEqual(chunks_b[0]["metadata"]["source"], "SessionB_Vendor.txt")

        # Query Session B returns Session B's document
        results_b = session_b.retrieve("vendor")
        self.assertGreater(len(results_b), 0)
        self.assertEqual(results_b[0]["metadata"]["source"], "SessionB_Vendor.txt")

        # Clearing Session A must NOT affect Session B's index, chunks, or queries
        session_a.clear()
        self.assertEqual(session_a.document_count, 0)
        self.assertEqual(len(session_a.get_all_chunks()), 0)
        self.assertEqual(session_a.retrieve("vendor"), [])

        self.assertEqual(session_b.document_count, 1)
        self.assertEqual(len(session_b.get_all_chunks()), 1)
        self.assertIn("SessionB_Vendor.txt", session_b.document_names)
        results_b_after = session_b.retrieve("vendor")
        self.assertGreater(len(results_b_after), 0)
        self.assertEqual(results_b_after[0]["metadata"]["source"], "SessionB_Vendor.txt")

    # ── 8. Database Resilience ──────────────────────────────────────

    def test_database_graceful_failures(self):
        # Database operations should not crash on invalid paths
        with patch('utils.db.DB_PATH', '/invalid/read_only_path/nonexistent.db'):
            # init_db must not raise
            init_db()
            # get_all_reviews must return empty list
            revs = get_all_reviews()
            self.assertEqual(revs, [])
            # get_review must return None
            rev = get_review("nonexistent-id")
            self.assertIsNone(rev)

    # ── 9. PDF Generation Resilience ────────────────────────────────

    def test_pdf_generation_resilience(self):
        # Normal report
        results = {
            "overall_status": "PASS",
            "risk_score": 10,
            "executive_summary": "All systems go. Unicode test: — “ ” •",
            "recommendation": "Approve.",
            "findings": [
                {
                    "title": "Finding 1",
                    "severity": "low",
                    "description": "Desc with special chars: € £",
                    "risk": "Minimal",
                    "recommended_action": "None",
                    "reasoning": "Reason",
                    "policy_evidence": "Policy quote",
                    "vendor_evidence": "Vendor quote"
                }
            ]
        }
        pdf_bytes = generate_pdf_report("Should we approve?", results)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 100)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Null / empty results must not crash
        empty_pdf = generate_pdf_report(None, None)
        self.assertIsInstance(empty_pdf, bytes)
        self.assertTrue(empty_pdf.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
