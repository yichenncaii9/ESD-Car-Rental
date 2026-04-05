#!/usr/bin/env python3
"""
clear_empty_diagnosis_reports.py — delete all reports in Firestore that have no diagnosis.

A report is considered empty if the 'diagnosis' field is missing, None, or blank ("").

Run from ESDProj/ root:
    python clear_empty_diagnosis_reports.py

Requires: firebase-service-account.json at ESDProj/ root
"""
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

docs = list(db.collection("reports").stream())
deleted = 0

for doc in docs:
    data = doc.to_dict()
    diagnosis = data.get("diagnosis")
    if not diagnosis or (isinstance(diagnosis, str) and not diagnosis.strip()):
        print(f"  Deleting report {doc.id}  (vehicle={data.get('vehicle_id', '?')}, status={data.get('status', '?')})")
        doc.reference.delete()
        deleted += 1

print(f"\nDone. Deleted {deleted} report(s) with empty diagnosis (out of {len(docs)} total).")
