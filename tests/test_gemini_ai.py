import unittest
from unittest.mock import Mock, patch

from gemini_ai import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_OPENAI_BASE_URL,
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

    def test_missing_key_is_not_ready(self):
        config = load_gemini_config(lambda _name: "")
        self.assertFalse(config.configured)
        self.assertFalse(config.ready)


class GeminiAIRequestTests(unittest.TestCase):
    @patch("gemini_ai.OpenAI")
    def test_translation_uses_gemini_endpoint_and_model(self, openai_class):
        parsed = SQLAnswer(
            sql="SELECT Vendor, SUM(Amount) AS Total FROM pcards GROUP BY Vendor",
            explanation="Totals by vendor.",
        )
        client = Mock()
        client.beta.chat.completions.parse.return_value = Mock(
            choices=[Mock(message=Mock(parsed=parsed))]
        )
        openai_class.return_value = client
        config = GeminiAIConfig(api_key="test-key", model="gemini-test-model")

        result = translate_question("Show totals by vendor", 2014, config)

        openai_class.assert_called_once_with(
            api_key="test-key",
            base_url=GEMINI_OPENAI_BASE_URL,
        )
        request = client.beta.chat.completions.parse.call_args.kwargs
        self.assertEqual(request["model"], "gemini-test-model")
        self.assertEqual(request["response_format"], SQLAnswer)
        self.assertEqual(result, parsed)

    @patch("gemini_ai.OpenAI")
    def test_authentication_error_is_safe_and_actionable(self, openai_class):
        error = RuntimeError("sensitive provider response")
        error.status_code = 401
        client = Mock()
        client.beta.chat.completions.parse.side_effect = error
        openai_class.return_value = client
        config = GeminiAIConfig(api_key="test-key")

        with self.assertRaisesRegex(GeminiAIError, "rejected the Gemini API key") as raised:
            translate_question("A custom question", 2014, config)
        self.assertNotIn("sensitive provider response", str(raised.exception))

    def test_missing_key_is_rejected_before_request(self):
        with self.assertRaisesRegex(GeminiAIError, "GEMINI_API_KEY"):
            translate_question("A custom question", 2014, GeminiAIConfig())


if __name__ == "__main__":
    unittest.main()
