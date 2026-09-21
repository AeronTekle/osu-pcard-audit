import unittest
from unittest.mock import Mock, patch

from microsoft_ai import (
    MicrosoftAIConfig,
    MicrosoftAIError,
    SQLAnswer,
    load_microsoft_config,
    translate_question,
)


class MicrosoftAIConfigTests(unittest.TestCase):
    def test_standard_azure_secrets_are_loaded(self):
        secrets = {
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/",
            "AZURE_OPENAI_DEPLOYMENT": "audit-model",
        }
        config = load_microsoft_config(lambda name: secrets.get(name, ""))
        self.assertTrue(config.ready)
        self.assertEqual(
            config.base_url(),
            "https://example.openai.azure.com/openai/v1/",
        )

    def test_copilot_aliases_are_supported(self):
        secrets = {
            "MICROSOFT_COPILOT_API_KEY": "test-key",
            "MICROSOFT_COPILOT_ENDPOINT": "https://example.openai.azure.com/openai/v1",
            "MICROSOFT_COPILOT_DEPLOYMENT": "audit-model",
        }
        config = load_microsoft_config(lambda name: secrets.get(name, ""))
        self.assertTrue(config.ready)
        self.assertEqual(config.deployment, "audit-model")

    def test_existing_key_name_can_be_migrated_to_microsoft(self):
        secrets = {
            "OPENAI_API_KEY": "microsoft-key-stored-under-the-old-name",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "audit-model",
        }
        config = load_microsoft_config(lambda name: secrets.get(name, ""))
        self.assertTrue(config.ready)
        self.assertEqual(config.api_key, "microsoft-key-stored-under-the-old-name")

    def test_incomplete_configuration_lists_missing_values(self):
        config = MicrosoftAIConfig(api_key="test-key")
        self.assertFalse(config.ready)
        self.assertEqual(
            config.missing,
            ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"),
        )
        with self.assertRaisesRegex(MicrosoftAIError, "incomplete"):
            config.base_url()

    def test_non_https_endpoint_is_rejected(self):
        config = MicrosoftAIConfig(
            api_key="test-key",
            endpoint="http://example.openai.azure.com",
            deployment="audit-model",
        )
        with self.assertRaisesRegex(MicrosoftAIError, "HTTPS"):
            config.base_url()


class MicrosoftAIRequestTests(unittest.TestCase):
    @patch("microsoft_ai.OpenAI")
    def test_translation_uses_microsoft_endpoint_and_deployment(self, openai_class):
        parsed = SQLAnswer(
            sql="SELECT Vendor, SUM(Amount) AS Total FROM pcards GROUP BY Vendor",
            explanation="Totals by vendor.",
        )
        client = Mock()
        client.responses.parse.return_value = Mock(output_parsed=parsed)
        openai_class.return_value = client
        config = MicrosoftAIConfig(
            api_key="test-key",
            endpoint="https://example.openai.azure.com",
            deployment="audit-deployment",
        )

        result = translate_question("Show totals by vendor", 2014, config)

        openai_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://example.openai.azure.com/openai/v1/",
        )
        self.assertEqual(
            client.responses.parse.call_args.kwargs["model"],
            "audit-deployment",
        )
        self.assertEqual(result, parsed)

    @patch("microsoft_ai.OpenAI")
    def test_authentication_error_is_safe_and_actionable(self, openai_class):
        error = RuntimeError("sensitive provider response")
        error.status_code = 401
        client = Mock()
        client.responses.parse.side_effect = error
        openai_class.return_value = client
        config = MicrosoftAIConfig(
            api_key="test-key",
            endpoint="https://example.openai.azure.com",
            deployment="audit-deployment",
        )

        with self.assertRaisesRegex(MicrosoftAIError, "rejected the credentials") as raised:
            translate_question("A custom question", 2014, config)
        self.assertNotIn("sensitive provider response", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
