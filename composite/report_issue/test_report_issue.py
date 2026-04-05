# composite/report_issue/test_report_issue.py
"""
Unit tests for report_issue composite — image_base64 passthrough.
All downstream HTTP calls (booking, maps, openai, report_service) are mocked.
"""
import sys, os, unittest
from unittest.mock import patch, MagicMock

# Patch firebase_admin before importing app
firebase_mock = MagicMock()
sys.modules["firebase_admin"] = firebase_mock
sys.modules["firebase_admin.credentials"] = MagicMock()
sys.modules["firebase_admin.firestore"] = MagicMock()
sys.modules["pika"] = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import importlib
import app as report_app
importlib.reload(report_app)


def _mock_requests(booking_ok=True, maps_ok=True, openai_severity="medium",
                   report_id="R001", captured_openai=None):
    """Return a mock for `requests` module with all downstream calls stubbed."""

    def get(url, **kwargs):
        r = MagicMock()
        r.status_code = 200 if booking_ok else 404
        r.json.return_value = {"booking_id": "B1"}
        return r

    def post(url, json=None, **kwargs):
        r = MagicMock()
        if "geocode" in url:
            r.status_code = 200 if maps_ok else 500
            r.json.return_value = {"address": "Test St, Singapore"}
        elif "evaluate" in url:
            if captured_openai is not None:
                captured_openai["payload"] = json
            r.status_code = 200
            r.json.return_value = {"severity": openai_severity, "provider": "openai"}
        elif "/api/reports" in url:
            r.status_code = 201
            r.json.return_value = {"report_id": report_id}
        return r

    def put(url, **kwargs):
        r = MagicMock()
        r.status_code = 200
        return r

    mock = MagicMock()
    mock.get.side_effect = get
    mock.post.side_effect = post
    mock.put.side_effect = put
    return mock


class TestReportIssueImagePassthrough(unittest.TestCase):
    def setUp(self):
        report_app.app.config["TESTING"] = True
        self.client = report_app.app.test_client()

    def test_image_base64_forwarded_to_openai_wrapper(self):
        """image_base64 present in request → forwarded verbatim to openai_wrapper."""
        captured = {}
        mock_req = _mock_requests(captured_openai=captured)
        with patch("app.requests", mock_req):
            res = self.client.post("/api/report-issue", json={
                "booking_id": "B1",
                "vehicle_id": "V1",
                "user_uid": "U1",
                "lat": 1.3,
                "lng": 103.8,
                "description": "Scratched door",
                "image_base64": "AAABBBCCC==",
            })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(captured["payload"]["image_base64"], "AAABBBCCC==")

    def test_no_image_base64_still_submits(self):
        """image_base64 absent → request succeeds; openai_wrapper receives no image_base64 key."""
        captured = {}
        mock_req = _mock_requests(captured_openai=captured)
        with patch("app.requests", mock_req):
            res = self.client.post("/api/report-issue", json={
                "booking_id": "B1",
                "vehicle_id": "V1",
                "user_uid": "U1",
                "lat": 1.3,
                "lng": 103.8,
                "description": "Flat tyre",
            })
        self.assertEqual(res.status_code, 200)
        self.assertIn("payload", captured, "openai_wrapper was not called")
        self.assertNotIn("image_base64", captured["payload"])

    def test_response_contains_severity(self):
        mock_req = _mock_requests(openai_severity="high")
        with patch("app.requests", mock_req):
            res = self.client.post("/api/report-issue", json={
                "booking_id": "B1",
                "vehicle_id": "V1",
                "user_uid": "U1",
                "lat": 1.3,
                "lng": 103.8,
                "description": "Engine fire",
                "image_base64": "abc123",
            })
        data = res.get_json()
        self.assertEqual(data["severity"], "high")
        self.assertEqual(data["status"], "submitted")


if __name__ == "__main__":
    unittest.main()
