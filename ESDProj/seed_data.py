#!/usr/bin/env python3
"""
seed_data.py — Firestore seeder for ESD Rental Car Service
Run from ESDProj/ root: python seed_data.py
Requires: firebase-service-account.json at ESDProj/ root
Idempotent: skips documents that already exist
"""
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

VEHICLES = [
    {"plate_number": "SBA1234A", "make": "Toyota", "model": "Corolla", "vehicle_type": "sedan",
     "year": 2022, "status": "available", "location_lat": 1.3521, "location_lng": 103.8198, "branch_id": 1},
    {"plate_number": "SBB5678B", "make": "Honda", "model": "Civic", "vehicle_type": "sedan",
     "year": 2021, "status": "available", "location_lat": 1.3000, "location_lng": 103.8000, "branch_id": 1},
    {"plate_number": "SBC9012C", "make": "Toyota", "model": "Camry", "vehicle_type": "sedan",
     "year": 2023, "status": "available", "location_lat": 1.3644, "location_lng": 103.9915, "branch_id": 2},
    {"plate_number": "SBD3456D", "make": "Nissan", "model": "Altima", "vehicle_type": "sedan",
     "year": 2022, "status": "available", "location_lat": 1.2789, "location_lng": 103.8536, "branch_id": 2},
    {"plate_number": "SBE7890E", "make": "Toyota", "model": "RAV4", "vehicle_type": "suv",
     "year": 2022, "status": "available", "location_lat": 1.3521, "location_lng": 103.8198, "branch_id": 1},
    {"plate_number": "SBF1234F", "make": "Honda", "model": "CR-V", "vehicle_type": "suv",
     "year": 2023, "status": "available", "location_lat": 1.3000, "location_lng": 103.8000, "branch_id": 1},
    {"plate_number": "SBG5678G", "make": "Hyundai", "model": "Tucson", "vehicle_type": "suv",
     "year": 2021, "status": "available", "location_lat": 1.3644, "location_lng": 103.9915, "branch_id": 2},
    {"plate_number": "SBH9012H", "make": "Toyota", "model": "Hiace", "vehicle_type": "van",
     "year": 2022, "status": "available", "location_lat": 1.3521, "location_lng": 103.8198, "branch_id": 1},
    {"plate_number": "SBI3456I", "make": "Nissan", "model": "NV200", "vehicle_type": "van",
     "year": 2021, "status": "available", "location_lat": 1.2789, "location_lng": 103.8536, "branch_id": 2},
    {"plate_number": "SBJ7890J", "make": "Ford", "model": "Transit", "vehicle_type": "van",
     "year": 2023, "status": "available", "location_lat": 1.3000, "location_lng": 103.8000, "branch_id": 2},
]

DRIVERS = [
    {"uid": "test_driver_001", "name": "John Tan", "license_number": "S1234567A",
     "license_expiry": "2027-12-31", "email": "john.tan@example.com"},
    {"uid": "test_driver_002", "name": "Mary Lim", "license_number": "S7654321B",
     "license_expiry": "2026-06-30", "email": "mary.lim@example.com"},
    {"uid": "test_driver_003", "name": "Ahmad Bin Ali", "license_number": "S9876543C",
     "license_expiry": "2028-03-15", "email": "ahmad.ali@example.com"},
]


def seed_vehicles():
    print("--- Seeding vehicles ---")
    for v in VEHICLES:
        doc_ref = db.collection("vehicles").document(v["plate_number"])
        if not doc_ref.get().exists:
            doc_ref.set(v)
            print(f"  Seeded: {v['plate_number']} ({v['vehicle_type']})")
        else:
            print(f"  Skipped: {v['plate_number']} (already exists)")


def seed_drivers():
    print("--- Seeding drivers ---")
    for d in DRIVERS:
        doc_ref = db.collection("drivers").document(d["license_number"])
        if not doc_ref.get().exists:
            doc_ref.set(d)
            print(f"  Seeded: {d['license_number']} ({d['name']})")
        else:
            print(f"  Skipped: {d['license_number']} (already exists)")


if __name__ == "__main__":
    seed_vehicles()
    seed_drivers()
    print("Done.")
