#!/usr/bin/env python3
"""
clear_ghost_bookings.py — mark all confirmed bookings for seeded test accounts as cancelled.

Run from ESDProj/ root:
    python clear_ghost_bookings.py

Requires: firebase-service-account.json at ESDProj/ root
"""
import firebase_admin
from firebase_admin import credentials, firestore

GHOST_UIDS = [
    "SMWcTzar1aYxmcnnOe7DJqGwO6A2",  # Test Driver A
    "ep3tVNPcFcZEkybfzQadOL7Yczk2",  # Test Driver B
]

cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

for uid in GHOST_UIDS:
    docs = list(
        db.collection("bookings")
        .where("user_uid", "==", uid)
        .where("status", "==", "confirmed")
        .stream()
    )
    if not docs:
        print(f"[{uid[:8]}…] No confirmed bookings found.")
        continue
    for doc in docs:
        doc.reference.update({"status": "cancelled"})
        data = doc.to_dict()
        print(f"[{uid[:8]}…] Cancelled booking {doc.id} (pickup: {data.get('pickup_datetime')})")

print("Done.")
