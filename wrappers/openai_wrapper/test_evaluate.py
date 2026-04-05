# wrappers/openai_wrapper/test_evaluate.py
"""
Unit tests for openai_wrapper /api/openai/evaluate
OpenAI client is mocked so tests run without an API key.
"""
import sys, os, unittest
from unittest.mock import patch, MagicMock

# Add wrapper root to path so we can import app directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import app as wrapper_app


class TestEvaluate(unittest.TestCase):
    def setUp(self):
        wrapper_app.app.config["TESTING"] = True
        self.client = wrapper_app.app.test_client()

    def _mock_openai(self, severity_word):
        """Return a mock OpenAI client whose completions.create returns severity_word."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = severity_word
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
        return mock_client

    def test_text_only_returns_severity(self):
        with patch("app.OpenAI", return_value=self._mock_openai("high")):
            res = self.client.post(
                "/api/openai/evaluate",
                json={"description": "Engine fire", "address": "Orchard Rd"}
            )
        data = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["severity"], "high")
        self.assertEqual(data["provider"], "openai")

    def test_image_base64_included_in_message(self):
        """When image_base64 is provided, the messages content must be a list containing image_url."""
        captured = {}

        def fake_create(**kwargs):
            captured["messages"] = kwargs["messages"]
            mock_choice = MagicMock()
            mock_choice.message.content = "medium"
            return MagicMock(choices=[mock_choice])

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = fake_create

        with patch("app.OpenAI", return_value=mock_client):
            res = self.client.post(
                "/api/openai/evaluate",
                json={
                    "description": "Scratch on bumper",
                    "address": "Bishan",
                    "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                }
            )
        self.assertEqual(res.status_code, 200)
        user_content = captured["messages"][1]["content"]
        self.assertIsInstance(user_content, list)
        types = [part["type"] for part in user_content]
        self.assertIn("image_url", types)
        self.assertIn("text", types)
        image_part = next(p for p in user_content if p["type"] == "image_url")
        self.assertTrue(image_part["image_url"]["url"].startswith("data:image/"))
        self.assertIn(";base64,", image_part["image_url"]["url"])

    def test_invalid_severity_defaults_to_medium(self):
        with patch("app.OpenAI", return_value=self._mock_openai("UNKNOWN_WORD")):
            res = self.client.post(
                "/api/openai/evaluate",
                json={"description": "Something happened", "address": "Tampines"}
            )
        self.assertEqual(res.get_json()["severity"], "medium")

    def test_openai_failure_returns_fallback(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        with patch("app.OpenAI", return_value=mock_client):
            res = self.client.post(
                "/api/openai/evaluate",
                json={"description": "Flat tyre", "address": "Jurong"}
            )
        data = res.get_json()
        self.assertEqual(data["severity"], "medium")
        self.assertEqual(data["provider"], "fallback")

    def test_missing_image_base64_uses_text_only_message(self):
        """No image_base64 in request → user content must be a plain string (not a list)."""
        captured = {}

        def fake_create(**kwargs):
            captured["messages"] = kwargs["messages"]
            mock_choice = MagicMock()
            mock_choice.message.content = "low"
            return MagicMock(choices=[mock_choice])

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = fake_create

        with patch("app.OpenAI", return_value=mock_client):
            self.client.post(
                "/api/openai/evaluate",
                json={"description": "Minor scratch", "address": "Clementi"}
            )
        user_content = captured["messages"][1]["content"]
        self.assertIsInstance(user_content, str)


if __name__ == "__main__":
    unittest.main()
