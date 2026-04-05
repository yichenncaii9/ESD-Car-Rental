#!/usr/bin/env python3
"""
clear_all_reports.py — delete ALL reports in Firestore.

Run from ESDProj/ root:
    python clear_all_reports.py

Requires: firebase-service-account.json at ESDProj/ root
"""
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

docs = list(db.collection("reports").stream())
for doc in docs:
    print(f"  Deleting {doc.id}")
    doc.reference.delete()

print(f"\nDone. Deleted {len(docs)} report(s).")
