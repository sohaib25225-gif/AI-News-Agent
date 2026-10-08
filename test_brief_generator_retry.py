"""
Test retry/backoff behavior in BriefGenerator._call_gemini_api.

Tests:
1. 503 → retry → eventual success (2nd attempt succeeds)
2. 503 → retry → eventual success (3rd attempt succeeds)
3. 503 → all 3 retries exhausted → clean None return
4. 400 → no retry, immediate None return
5. 401 → no retry, immediate None return
6. 403 → no retry, immediate None return
7. 404 → no retry, immediate None return
8. Verify maxOutputTokens is 4096 in payload
9. Immediate success (no retries)
10. Verify retry delays are [5, 15, 45]
"""

import json
import time
import unittest
from unittest.mock import patch, MagicMock, call

from agents.brief_generator import BriefGenerator


def make_response(status_code, json_body):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.text = json.dumps(json_body)
    return resp


def make_gemini_success(text="OK", finish_reason="STOP"):
    """Create a mock successful Gemini response."""
    return make_response(200, {
        "candidates": [{
            "content": {"parts": [{"text": text}], "role": "model"},
            "finishReason": finish_reason,
            "index": 0
        }],
        "usageMetadata": {"promptTokenCount": 5, "totalTokenCount": 10},
        "modelVersion": "gemini-3.6-flash",
    })


def make_gemini_503():
    """Create a mock 503 response."""
    return make_response(503, {
        "error": {
            "message": "This model is currently experiencing high demand.",
            "code": 503
        }
    })


class MockResponse:
    """Minimal mock that captures what was posted."""
    def __init__(self, status_code=200, json_body=None):
        self.status_code = status_code
        self._json_body = json_body or {}
        self.text = json.dumps(self._json_body)

    def json(self):
        return self._json_body


class TestBriefGeneratorRetry(unittest.TestCase):
    """Tests for retry/backoff behavior in _call_gemini_api."""

    def setUp(self):
        self.generator = BriefGenerator()

    # ----------------------------------------------------------------
    # Test 1: 503 → 2nd attempt succeeds
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    @patch("agents.brief_generator.time.sleep")
    def test_503_retry_then_success(self, mock_sleep, mock_post):
        """After one 503, second attempt succeeds."""
        mock_post.side_effect = [
            make_gemini_503(),
            make_gemini_success(text='{"executive_summary":"test"}'),
        ]

        result = self.generator._call_gemini_api("test prompt")

        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(result, '{"executive_summary":"test"}')
        # Should have slept once (before retry)
        self.assertEqual(mock_sleep.call_count, 1)
        mock_sleep.assert_called_with(5)

    # ----------------------------------------------------------------
    # Test 2: 503 × 2 → 3rd attempt succeeds
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    @patch("agents.brief_generator.time.sleep")
    def test_503_twice_then_success(self, mock_sleep, mock_post):
        """After two 503s, third attempt succeeds."""
        mock_post.side_effect = [
            make_gemini_503(),
            make_gemini_503(),
            make_gemini_success(text="success on third"),
        ]

        result = self.generator._call_gemini_api("test prompt")

        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(result, "success on third")
        # Should have slept twice (5s, 15s)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_has_calls([call(5), call(15)])

    # ----------------------------------------------------------------
    # Test 3: 503 × 4 (initial + 3 retries) → all exhausted → clean failure
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    @patch("agents.brief_generator.time.sleep")
    def test_503_all_retries_exhausted(self, mock_sleep, mock_post):
        """After 3 retries all returning 503, return None cleanly."""
        mock_post.side_effect = [
            make_gemini_503(),
            make_gemini_503(),
            make_gemini_503(),
            make_gemini_503(),
        ]

        result = self.generator._call_gemini_api("test prompt")

        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 4)  # 1 initial + 3 retries
        # Should have slept 3 times (5, 15, 45)
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_has_calls([call(5), call(15), call(45)])

    # ----------------------------------------------------------------
    # Test 4: 400 → no retry
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    @patch("agents.brief_generator.time.sleep")
    def test_400_no_retry(self, mock_sleep, mock_post):
        """HTTP 400 returns immediately without retry."""
        mock_post.return_value = make_response(400, {
            "error": {"message": "Bad Request"}
        })

        result = self.generator._call_gemini_api("test prompt")

        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()

    # ----------------------------------------------------------------
    # Test 5: 401 → no retry
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    @patch("agents.brief_generator.time.sleep")
    def test_401_no_retry(self, mock_sleep, mock_post):
        """HTTP 401 returns immediately without retry."""
        mock_post.return_value = make_response(401, {
            "error": {"message": "API key not valid"}
        })

        result = self.generator._call_gemini_api("test prompt")

        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()

    # ----------------------------------------------------------------
    # Test 6: 403 → no retry
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    @patch("agents.brief_generator.time.sleep")
    def test_403_no_retry(self, mock_sleep, mock_post):
        """HTTP 403 returns immediately without retry."""
        mock_post.return_value = make_response(403, {
            "error": {"message": "Permission denied"}
        })

        result = self.generator._call_gemini_api("test prompt")

        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()

    # ----------------------------------------------------------------
    # Test 7: 404 → no retry
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    @patch("agents.brief_generator.time.sleep")
    def test_404_no_retry(self, mock_sleep, mock_post):
        """HTTP 404 returns immediately without retry."""
        mock_post.return_value = make_response(404, {
            "error": {"message": "Model not found"}
        })

        result = self.generator._call_gemini_api("test prompt")

        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()

    # ----------------------------------------------------------------
    # Test 8: Verify maxOutputTokens is 4096
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    def test_max_output_tokens_is_4096(self, mock_post):
        """The payload must use maxOutputTokens: 4096."""
        mock_post.return_value = make_gemini_success()

        self.generator._call_gemini_api("test prompt")

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        self.assertEqual(
            payload["generationConfig"]["maxOutputTokens"],
            4096,
            f"Expected maxOutputTokens=4096, got {payload['generationConfig']['maxOutputTokens']}"
        )

    # ----------------------------------------------------------------
    # Test 9: Immediate success (no retries)
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    @patch("agents.brief_generator.time.sleep")
    def test_immediate_success(self, mock_sleep, mock_post):
        """Successful first attempt calls API once, no sleep."""
        mock_post.return_value = make_gemini_success(text="immediate")

        result = self.generator._call_gemini_api("test prompt")

        self.assertEqual(result, "immediate")
        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()

    # ----------------------------------------------------------------
    # Test 10: Verify other generationConfig values unchanged
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    def test_generation_config_unchanged(self, mock_post):
        """temperature, topK, topP must remain at original values."""
        mock_post.return_value = make_gemini_success()

        self.generator._call_gemini_api("test prompt")

        config = mock_post.call_args.kwargs["json"]["generationConfig"]
        self.assertEqual(config["temperature"], 0.3)
        self.assertEqual(config["topK"], 40)
        self.assertEqual(config["topP"], 0.95)

    # ----------------------------------------------------------------
    # Test 11: 503 on retry 2, succeed on retry 3 — verify all 3 delays
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    @patch("agents.brief_generator.time.sleep")
    def test_all_three_delays_used(self, mock_sleep, mock_post):
        """Verify the three delays are exactly 5, 15, 45 seconds."""
        mock_post.side_effect = [
            make_gemini_503(),
            make_gemini_503(),
            make_gemini_503(),
            make_gemini_success(text="finally"),
        ]

        result = self.generator._call_gemini_api("test prompt")

        self.assertEqual(result, "finally")
        self.assertEqual(mock_sleep.call_count, 3)
        # Verify exact delay sequence
        calls = mock_sleep.call_args_list
        self.assertEqual(calls[0], call(5))
        self.assertEqual(calls[1], call(15))
        self.assertEqual(calls[2], call(45))

    # ----------------------------------------------------------------
    # Test 12: Verify model ID and endpoint unchanged
    # ----------------------------------------------------------------
    @patch("agents.brief_generator.requests.post")
    def test_model_and_endpoint_unchanged(self, mock_post):
        """The model ID and endpoint must not have changed."""
        mock_post.return_value = make_gemini_success()

        self.generator._call_gemini_api("test prompt")

        url = mock_post.call_args.args[0]
        self.assertIn("gemini-3.6-flash", url)
        self.assertIn("generativelanguage.googleapis.com", url)
        self.assertIn("generateContent", url)


if __name__ == "__main__":
    unittest.main()
