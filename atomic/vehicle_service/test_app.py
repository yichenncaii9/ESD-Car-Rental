"""
Tests for vehicle_service/app.py — Phase 3 TDD
Tests verify the three Firestore-backed routes work correctly.
Firestore is mocked so tests run without real credentials.
"""
import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

# Patch firebase_admin before importing app so init block doesn't fail
firebase_mock = MagicMock()
credentials_mock = MagicMock()
firestore_mock = MagicMock()

sys.modules["firebase_admin"] = firebase_mock
sys.modules["firebase_admin.credentials"] = credentials_mock
sys.modules["firebase_admin.firestore"] = firestore_mock

import importlib
import atomic.vehicle_service.app as vehicle_app
importlib.reload(vehicle_app)


def make_doc(plate, extra=None):
    """Build a mock Firestore DocumentSnapshot."""
    doc = MagicMock()
    doc.id = plate
    data = {
        "plate_number": plate,
        "make": "Toyota",
        "model": "Corolla",
        "vehicle_type": "sedan",
        "year": 2022,
        "status": "available",
        "location_lat": 1.3521,
        "location_lng": 103.8198,
        "branch_id": "branch_01",
    }
    if extra:
        data.update(extra)
    doc.to_dict.return_value = data
    doc.exists = True
    return doc


class TestGetVehicles(unittest.TestCase):
    def setUp(self):
        self.client = vehicle_app.app.test_client()

    def test_returns_list_of_vehicles(self):
        """GET /api/vehicles returns {"status":"ok","data":[...]} with 10 items."""
        docs = [make_doc(f"SBA000{i}A") for i in range(10)]
        with patch.object(vehicle_app, "db") as mock_db:
            mock_db.collection.return_value.stream.return_value = docs
            resp = self.client.get("/api/vehicles")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "ok")
        self.assertIsInstance(body["data"], list)
        self.assertEqual(len(body["data"]), 10)

    def test_each_item_has_id_field(self):
        """Each vehicle in the list has an 'id' field equal to doc.id."""
        doc = make_doc("SBA1234A")
        with patch.object(vehicle_app, "db") as mock_db:
            mock_db.collection.return_value.stream.return_value = [doc]
            resp = self.client.get("/api/vehicles")
        body = json.loads(resp.data)
        self.assertIn("id", body["data"][0])
        self.assertEqual(body["data"][0]["id"], "SBA1234A")

    def test_db_none_returns_500(self):
        """GET /api/vehicles returns 500 when db is None."""
        with patch.object(vehicle_app, "db", None):
            resp = self.client.get("/api/vehicles")
        self.assertEqual(resp.status_code, 500)

    def test_uses_vehicles_collection(self):
        """GET /api/vehicles queries the 'vehicles' collection."""
        with patch.object(vehicle_app, "db") as mock_db:
            mock_db.collection.return_value.stream.return_value = []
            self.client.get("/api/vehicles")
            mock_db.collection.assert_called_once_with("vehicles")


class TestGetVehicle(unittest.TestCase):
    def setUp(self):
        self.client = vehicle_app.app.test_client()

    def test_returns_vehicle_for_valid_id(self):
        """GET /api/vehicles/SBA1234A returns 200 with vehicle data."""
        doc = make_doc("SBA1234A")
        with patch.object(vehicle_app, "db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value = doc
            resp = self.client.get("/api/vehicles/SBA1234A")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["data"]["plate_number"], "SBA1234A")

    def test_returns_404_for_unknown_id(self):
        """GET /api/vehicles/UNKNOWN returns 404."""
        doc = MagicMock()
        doc.exists = False
        with patch.object(vehicle_app, "db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value = doc
            resp = self.client.get("/api/vehicles/UNKNOWN")
        self.assertEqual(resp.status_code, 404)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "error")
        self.assertIn("not found", body["message"].lower())

    def test_db_none_returns_500(self):
        """GET /api/vehicles/<id> returns 500 when db is None."""
        with patch.object(vehicle_app, "db", None):
            resp = self.client.get("/api/vehicles/SBA1234A")
        self.assertEqual(resp.status_code, 500)


class TestUpdateVehicleStatus(unittest.TestCase):
    def setUp(self):
        self.client = vehicle_app.app.test_client()

    def test_updates_status_successfully(self):
        """PUT /api/vehicles/SBA1234A/status with valid body returns 200 ok."""
        doc = make_doc("SBA1234A")
        with patch.object(vehicle_app, "db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value = doc
            resp = self.client.put(
                "/api/vehicles/SBA1234A/status",
                data=json.dumps({"status": "booked"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "ok")
        self.assertIn("updated", body["message"].lower())

    def test_returns_400_when_status_missing(self):
        """PUT /api/vehicles/SBA1234A/status with no body returns 400."""
        with patch.object(vehicle_app, "db") as mock_db:
            resp = self.client.put(
                "/api/vehicles/SBA1234A/status",
                data=json.dumps({}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "error")

    def test_returns_400_when_no_body(self):
        """PUT /api/vehicles/SBA1234A/status with completely empty body returns 400."""
        with patch.object(vehicle_app, "db") as mock_db:
            resp = self.client.put("/api/vehicles/SBA1234A/status")
        self.assertEqual(resp.status_code, 400)

    def test_returns_404_when_vehicle_not_found(self):
        """PUT /api/vehicles/UNKNOWN/status returns 404."""
        doc = MagicMock()
        doc.exists = False
        with patch.object(vehicle_app, "db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value = doc
            resp = self.client.put(
                "/api/vehicles/UNKNOWN/status",
                data=json.dumps({"status": "booked"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 404)

    def test_db_none_returns_500(self):
        """PUT /api/vehicles/<id>/status returns 500 when db is None."""
        with patch.object(vehicle_app, "db", None):
            resp = self.client.put(
                "/api/vehicles/SBA1234A/status",
                data=json.dumps({"status": "booked"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 500)

    def test_calls_update_on_doc_ref(self):
        """PUT /api/vehicles/<id>/status calls doc_ref.update() with new status."""
        doc = make_doc("SBA1234A")
        with patch.object(vehicle_app, "db") as mock_db:
            doc_ref = mock_db.collection.return_value.document.return_value
            doc_ref.get.return_value = doc
            self.client.put(
                "/api/vehicles/SBA1234A/status",
                data=json.dumps({"status": "available"}),
                content_type="application/json",
            )
            doc_ref.update.assert_called_once_with({"status": "available"})


if __name__ == "__main__":
    unittest.main()
