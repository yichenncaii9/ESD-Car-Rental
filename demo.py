#!/usr/bin/env python3
"""
demo.py — ESD Car Rental full-flow demo
  1. Onboard  (Firebase sign-in)
  2. Book     (pick a vehicle, create booking)
  3. Report   (submit incident report)
  4. Cancel   (cancel the booking)

Run from ESDProj/ root:
    python demo.py
"""

import requests
import json
import time
from datetime import datetime, timedelta

# ── CONFIG ────────────────────────────────────────────────────────────────────
GATEWAY       = "http://localhost:8000"
FIREBASE_KEY  = "AIzaSyCbG3Y9nUDps1pmwJcU3Vgr4uPF6yJCO8c"
DEMO_EMAIL    = "testuser@email.com"
DEMO_PASSWORD = "Testuser0908"           # update if different

# ── HELPERS ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def banner(text):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")

def ok(label, value=""):
    print(f"  {GREEN}✓{RESET} {label}{f': {CYAN}{value}{RESET}' if value else ''}")

def info(label, value=""):
    print(f"  {YELLOW}→{RESET} {label}{f': {value}' if value else ''}")

def fail(label, detail=""):
    print(f"  {RED}✗ {label}{f': {detail}' if detail else ''}{RESET}")
    raise SystemExit(1)

def post(path, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{GATEWAY}{path}", json=payload, headers=headers, timeout=15)
    return r

def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{GATEWAY}{path}", headers=headers, timeout=10)
    return r


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — ONBOARD (Firebase sign-in)
# ══════════════════════════════════════════════════════════════════════════════
banner("STEP 1 — Onboarding (Firebase sign-in)")

info("Signing in", DEMO_EMAIL)
auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_KEY}"
auth_r = requests.post(auth_url, json={
    "email": DEMO_EMAIL,
    "password": DEMO_PASSWORD,
    "returnSecureToken": True
}, timeout=10)

if auth_r.status_code != 200:
    fail("Firebase sign-in failed", auth_r.text[:200])

auth_data = auth_r.json()
token    = auth_data["idToken"]
uid      = auth_data["localId"]
ok("Signed in", DEMO_EMAIL)
ok("UID", uid)
ok("Token", token[:40] + "…")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — BOOK A CAR
# ══════════════════════════════════════════════════════════════════════════════
banner("STEP 2 — Book a Car")

# Pick first available vehicle
info("Fetching available vehicles")
v_r = get("/api/vehicles")
if v_r.status_code != 200:
    fail("Could not fetch vehicles", v_r.text[:200])

vehicles = v_r.json().get("data", [])
available = [v for v in vehicles if v.get("status") == "available"]
if not available:
    fail("No available vehicles found")

vehicle = available[0]
vid = vehicle.get("id") or vehicle.get("plate_number")
ok("Vehicle selected", f"{vid} ({vehicle.get('vehicle_type','?')})")

# Pickup = 1 hour from now (future window so cancel is valid)
pickup_dt = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
hours     = 2

# Fetch price estimate
info("Fetching price estimate")
price_r = get(f"/api/pricing?vehicle_type={vehicle['vehicle_type']}&hours={hours}")
if price_r.status_code == 200:
    price = price_r.json().get("total_price", 50.00)
else:
    price = 50.00   # fallback
ok("Estimated price", f"SGD {price:.2f}")

# Create booking
info("Creating booking")
booking_r = post("/api/book-car", {
    "user_uid":                uid,
    "vehicle_id":              vid,
    "vehicle_type":            vehicle.get("vehicle_type", "sedan"),
    "pickup_datetime":         pickup_dt,
    "hours":                   hours,
    "total_price":             price,
    "stripe_payment_intent_id": "pi_demo_card_visa"
}, token=token)

if booking_r.status_code not in (200, 201):
    fail("Booking failed", booking_r.text[:300])

booking_data = booking_r.json()
booking_id = booking_data.get("booking_id") or booking_data.get("data", {}).get("booking_id")
ok("Booking created", booking_id)
ok("Pickup", pickup_dt)
ok("Duration", f"{hours} hrs")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — REPORT AN INCIDENT
# ══════════════════════════════════════════════════════════════════════════════
banner("STEP 3 — Report an Incident")

info("Submitting incident report")
report_r = post("/api/report-issue", {
    "user_uid":    uid,
    "booking_id":  booking_id,
    "vehicle_id":  vid,
    "description": "Noticed a deep scratch on the front bumper and a cracked side mirror upon pickup.",
    "lat":         1.35208,
    "lng":         103.81983
}, token=token)

if report_r.status_code not in (200, 201):
    fail("Report failed", report_r.text[:300])

report_data = report_r.json()
report_id  = report_data.get("report_id")
severity   = report_data.get("severity", "pending")
ok("Report submitted", report_id)
ok("Severity assessed", severity)
ok("AI diagnosis + SMS notification queued for service team")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — CANCEL THE BOOKING
# ══════════════════════════════════════════════════════════════════════════════
banner("STEP 4 — Cancel Booking")

info("Cancelling booking", booking_id)
cancel_r = post("/api/cancel-booking", {
    "booking_id": booking_id
}, token=token)

if cancel_r.status_code not in (200, 201):
    fail("Cancellation failed", cancel_r.text[:300])

cancel_data  = cancel_r.json()
refund_amt   = cancel_data.get("refund_amount", "?")
refund_status = cancel_data.get("refund_status", "processed")
ok("Booking cancelled", booking_id)
ok("Refund amount", f"SGD {refund_amt}")
ok("Refund status", refund_status)


# ══════════════════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════════════════
banner("DEMO COMPLETE")
print(f"""
  {BOLD}Summary{RESET}
  {'─'*40}
  User      {CYAN}{DEMO_EMAIL}{RESET}
  UID       {uid}
  Vehicle   {vid} ({vehicle.get('vehicle_type','?')})
  Booking   {booking_id}
  Report    {report_id}  (severity: {severity})
  Status    {GREEN}cancelled + refund processed{RESET}
""")
