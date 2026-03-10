import unittest

from fastapi.testclient import TestClient

from app.web.app import create_app


class WebShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_homepage_renders_core_review_links(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("OpenClaw", response.text)
        self.assertIn("/privacy", response.text)
        self.assertIn("/oauth/etsy/callback", response.text)

    def test_health_route_returns_json_status(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["app"], "openclaw-web")
        self.assertIn(payload["status"], {"ok", "degraded"})
        self.assertIn("db_exists", payload)

    def test_oauth_callback_page_echoes_provider_state(self) -> None:
        response = self.client.get("/oauth/tiktok/callback?code=test-code&state=review-state")

        self.assertEqual(response.status_code, 200)
        self.assertIn("TikTok", response.text)
        self.assertIn("review-state", response.text)
        self.assertIn("yes", response.text)

    def test_review_page_loads_without_database(self) -> None:
        response = self.client.get("/review")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Reviewer Overview", response.text)
        self.assertIn("CLI pipeline", response.text)


if __name__ == "__main__":
    unittest.main()
