import unittest
from unittest.mock import Mock, patch

import httpx

from gemini_ai import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_API_BASE_URL,
    GeminiAIConfig,
    GeminiAIError,
    SQLAnswer,
    load_gemini_config,
    translate_question,
)


class GeminiAIConfigTests(unittest.TestCase):
    def test_standard_gemini_secret_is_loaded(self):
        secrets = {"GEMINI_API_KEY": "test-key"}
        config = load_gemini_config(lambda name: secrets.get(name, ""))
        self.assertTrue(config.ready)
        self.assertEqual(config.api_key, "test-key")
        self.assertEqual(config.model, DEFAULT_GEMINI_MODEL)

    def test_google_api_key_alias_is_supported(self):
        secrets = {"GOOGLE_API_KEY": "test-key"}
        config = load_gemini_config(lambda name: secrets.get(name, ""))
        self.assertTrue(config.ready)

    def test_model_can_be_overridden(self):
        secrets = {
            "GEMINI_API_KEY": "test-key",
            "GEMINI_MODEL": "gemini-custom-model",
        }
        config = load_gemini_config(lambda name: secrets.get(name, ""))
        self.assertEqual(config.model, "gemini-custom-model")

    def test_old_slow_model_override_is_migrated(self):
        secrets = {
            "GEMINI_API_KEY": "test-key",
            "GEMINI_MODEL": "gemini-3.8-flash",
        }
        config = load_gemini_config(lambda name: secrets.get(name, ""))
        self.assertEqual(config.model, DEFAULT_GEMINI_MODEL)

    def test_missing_key_is_not_ready(self):
        config = load_gemini_config(lambda _name: "")
        self.assertFalse(config.configured)
        self.assertFalse(config.ready)


class GeminiAIRequestTests(unittest.TestCase):
    @patch("gemini_ai.httpx.post")
    def test_translation_uses_native_gemini_endpoint_and_model(self, post):
        parsed = SQLAnswer(
            sql="SELECT Vendor, SUM(Amount) AS Total FROM pcards GROUP BY Vendor",
            explanation="Totals by vendor.",
        )
        response = Mock()
        response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": parsed.model_dump_json()}]}}
            ]
        }
        post.return_value = response
        config = GeminiAIConfig(api_key="test-key", model="gemini-test-model")

        result = translate_question("Show totals by vendor", 2014, config)

        request = post.call_args
        self.assertEqual(
            request.args[0],
            f"{GEMINI_API_BASE_URL}/gemini-test-model:generateContent",
        )
        self.assertEqual(request.kwargs["headers"], {"x-goog-api-key": "test-key"})
        self.assertEqual(
            request.kwargs["json"]["generationConfig"]["responseMimeType"],
            "application/json",
        )
        self.assertEqual(request.kwargs["timeout"], 30.0)
        self.assertEqual(result, parsed)

    @patch("gemini_ai.httpx.post")
    def test_authentication_error_is_safe_and_actionable(self, post):
        request = httpx.Request("POST", GEMINI_API_BASE_URL)
        response = httpx.Response(401, request=request)
        post.side_effect = httpx.HTTPStatusError(
            "sensitive provider response", request=request, response=response
        )
        config = GeminiAIConfig(api_key="test-key")

        with self.assertRaisesRegex(GeminiAIError, "rejected the Gemini API key") as raised:
            translate_question("A custom question", 2014, config)
        self.assertNotIn("sensitive provider response", str(raised.exception))

    @patch("gemini_ai.httpx.post")
    def test_google_invalid_key_bad_request_is_actionable(self, post):
        request = httpx.Request("POST", GEMINI_API_BASE_URL)
        response = httpx.Response(400, request=request)
        post.side_effect = httpx.HTTPStatusError(
            "API_KEY_INVALID", request=request, response=response
        )

        with self.assertRaisesRegex(GeminiAIError, "rejected the Gemini API key"):
            translate_question(
                "A custom question", 2014, GeminiAIConfig(api_key="test-key")
            )

    @patch("gemini_ai.httpx.post")
    def test_timeout_is_actionable(self, post):
        post.side_effect = httpx.ReadTimeout("timed out")
        with self.assertRaisesRegex(GeminiAIError, "within 30 seconds"):
            translate_question(
                "A custom question", 2014, GeminiAIConfig(api_key="test-key")
            )

    def test_missing_key_is_rejected_before_request(self):
        with self.assertRaisesRegex(GeminiAIError, "GEMINI_API_KEY"):
            translate_question("A custom question", 2014, GeminiAIConfig())


if __name__ == "__main__":
    unittest.main()
