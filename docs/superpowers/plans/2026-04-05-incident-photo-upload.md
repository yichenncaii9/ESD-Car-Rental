# Incident Photo Upload (GPT-4o Vision) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to optionally attach a photo when reporting an incident; the image is passed to GPT-4o vision for more accurate severity classification, then discarded — only the severity string is persisted.

**Architecture:** Base64-encoded image flows from Vue frontend → Kong gateway → `report_issue` composite → `openai_wrapper` → OpenAI API. No image is stored anywhere. The `openai_wrapper` is upgraded from `gpt-3.5-turbo` (text-only) to `gpt-4o` (multimodal). The field is optional — omitting it degrades gracefully to text-only classification.

**Tech Stack:** Vue 3 (Composition API), Python Flask, OpenAI Python SDK (`openai` package already installed), `gpt-4o` model, base64 encoding (native browser FileReader API, no extra deps).

---

## File Map

| File | Change |
|------|--------|
| `wrappers/openai_wrapper/app.py` | Accept optional `image_base64`; upgrade model to `gpt-4o`; build vision message array |
| `wrappers/openai_wrapper/test_evaluate.py` | New — unit tests for the evaluate endpoint |
| `composite/report_issue/app.py` | Extract and forward `image_base64` to openai_wrapper call |
| `composite/report_issue/test_report_issue.py` | New — unit tests for image passthrough |
| `frontend/src/views/ReportIncidentView.vue` | Add optional file input, base64 conversion, thumbnail preview, include in payload |

---

## Task 1: Upgrade `openai_wrapper` to GPT-4o Vision

**Files:**
- Modify: `wrappers/openai_wrapper/app.py`
- Create: `wrappers/openai_wrapper/test_evaluate.py`

- [ ] **Step 1: Create the test file**

```python
# wrappers/openai_wrapper/test_evaluate.py
"""
Unit tests for openai_wrapper /api/openai/evaluate
OpenAI client is mocked so tests run without an API key.
"""
import sys, os, json, unittest
from unittest.mock import patch, MagicMock

# Add wrapper root to path so we can import app directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import app as wrapper_app


class TestEvaluateTextOnly(unittest.TestCase):
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
```

- [ ] **Step 2: Run the tests — expect failures**

```bash
cd /Applications/MAMP/htdocs/y2s2/ESD/ESDProj
python -m pytest wrappers/openai_wrapper/test_evaluate.py -v
```

Expected: 4–5 failures since `app.py` still uses gpt-3.5-turbo and text-only messages.

- [ ] **Step 3: Rewrite `openai_wrapper/app.py`**

Replace the entire file content:

```python
# wrappers/openai_wrapper/app.py — GPT-4o vision severity classification (Phase 5)
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

SYSTEM_PROMPT = (
    "You are a vehicle incident severity classifier for a car rental service. "
    "Given an incident description, location, and optional photo, classify the severity "
    "as exactly one of: low, medium, or high. "
    "low = minor cosmetic damage or inconvenience. "
    "medium = functional issue requiring service. "
    "high = safety hazard or major damage. "
    "Respond with only the single word: low, medium, or high."
)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/openai/evaluate", methods=["POST"])
def evaluate():
    """
    Classify incident severity using OpenAI GPT-4o (with optional vision).
    Mock fallback: if OpenAI fails, returns severity="medium".

    Request body:
      { description: str, address: str, image_base64?: str }
      image_base64 is a base64-encoded JPEG/PNG (no data-URI prefix needed;
      the wrapper adds the prefix automatically).

    Response:
      { status: "ok", severity: "low"|"medium"|"high", provider: "openai"|"fallback" }
    """
    body = request.get_json(silent=True) or {}
    description = body.get("description", "")
    address = body.get("address", "Unknown location")
    image_base64 = body.get("image_base64")  # optional

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        text_content = f"Location: {address}\nIncident: {description}"

        if image_base64:
            # Vision message: array with text part + image_url part
            user_content = [
                {"type": "text", "text": text_content},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                        "detail": "low",   # low = 65 tokens, sufficient for damage assessment
                    },
                },
            ]
        else:
            # Text-only message: plain string (backwards-compatible)
            user_content = text_content

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=10,
            temperature=0,
        )
        severity = response.choices[0].message.content.strip().lower()
        if severity not in ("low", "medium", "high"):
            severity = "medium"
        return jsonify({"status": "ok", "severity": severity, "provider": "openai"}), 200

    except Exception as e:
        print(f"[openai_wrapper] OpenAI API failed, using mock fallback: {e}")
        return jsonify({"status": "ok", "severity": "medium", "provider": "fallback"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6200)), debug=True)
```

- [ ] **Step 4: Run the tests — expect all pass**

```bash
python -m pytest wrappers/openai_wrapper/test_evaluate.py -v
```

Expected output:
```
PASSED test_text_only_returns_severity
PASSED test_image_base64_included_in_message
PASSED test_invalid_severity_defaults_to_medium
PASSED test_openai_failure_returns_fallback
PASSED test_missing_image_base64_uses_text_only_message
5 passed in <1s
```

- [ ] **Step 5: Commit**

```bash
git add wrappers/openai_wrapper/app.py wrappers/openai_wrapper/test_evaluate.py
git commit -m "feat(openai_wrapper): upgrade to gpt-4o vision, accept optional image_base64"
```

---

## Task 2: Pass `image_base64` Through `report_issue` Composite

**Files:**
- Modify: `composite/report_issue/app.py:59-98` (the `/api/report-issue` route)
- Create: `composite/report_issue/test_report_issue.py`

- [ ] **Step 1: Create the test file**

```python
# composite/report_issue/test_report_issue.py
"""
Unit tests for report_issue composite — image_base64 passthrough.
All downstream HTTP calls (booking, maps, openai, report_service) are mocked.
"""
import sys, os, json, unittest
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
        self.assertNotIn("image_base64", captured.get("payload", {}))

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
```

- [ ] **Step 2: Run the tests — expect failures**

```bash
python -m pytest composite/report_issue/test_report_issue.py -v
```

Expected: `test_image_base64_forwarded_to_openai_wrapper` fails because the composite doesn't yet pass `image_base64`.

- [ ] **Step 3: Edit `composite/report_issue/app.py`**

In the `/api/report-issue` route, add extraction of `image_base64` after `description`:

```python
# After: description = body.get("description", "")
image_base64 = body.get("image_base64")  # optional; forwarded to openai_wrapper for vision
```

In Phase A Step 3, update the openai_wrapper call to include it:

```python
    # Phase A Step 3: Classify severity via OpenAI (COMP-08)
    openai_payload = {"description": description, "address": address}
    if image_base64:
        openai_payload["image_base64"] = image_base64
    r = requests.post(f"http://{OPENAI_HOST}/api/openai/evaluate",
                      json=openai_payload, timeout=15)
```

- [ ] **Step 4: Run the tests — expect all pass**

```bash
python -m pytest composite/report_issue/test_report_issue.py -v
```

Expected:
```
PASSED test_image_base64_forwarded_to_openai_wrapper
PASSED test_no_image_base64_still_submits
PASSED test_response_contains_severity
3 passed in <1s
```

- [ ] **Step 5: Commit**

```bash
git add composite/report_issue/app.py composite/report_issue/test_report_issue.py
git commit -m "feat(report_issue): forward optional image_base64 to openai_wrapper"
```

---

## Task 3: Frontend — Optional Photo Input with Preview

**Files:**
- Modify: `frontend/src/views/ReportIncidentView.vue`

- [ ] **Step 1: Add `imageBase64` ref and file-handling function to `<script setup>`**

After `const description = ref('')` (line 107), add:

```js
const imageBase64 = ref('')        // empty string = no image attached
const imagePreviewUrl = ref('')    // object URL for thumbnail display

function onPhotoSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return

  // Revoke previous object URL to avoid memory leaks
  if (imagePreviewUrl.value) URL.revokeObjectURL(imagePreviewUrl.value)
  imagePreviewUrl.value = URL.createObjectURL(file)

  const reader = new FileReader()
  reader.onload = (e) => {
    // Strip the data-URI prefix (e.g. "data:image/jpeg;base64,") — wrapper adds it
    const dataUrl = e.target.result
    imageBase64.value = dataUrl.split(',')[1] ?? ''
  }
  reader.readAsDataURL(file)
}

function removePhoto() {
  imageBase64.value = ''
  if (imagePreviewUrl.value) URL.revokeObjectURL(imagePreviewUrl.value)
  imagePreviewUrl.value = ''
}
```

- [ ] **Step 2: Add `image_base64` to the submission payload**

In `submitReport()`, update the `payload` object (around line 210):

```js
  const payload = {
    user_uid:    uid,
    booking_id:  bookingId.value,
    vehicle_id:  vehicleId.value,
    description: description.value,
    lat:         incidentLocation.value.lat,
    lng:         incidentLocation.value.lng,
    ...(imageBase64.value ? { image_base64: imageBase64.value } : {}),
  }
```

- [ ] **Step 3: Add the photo upload UI block to `<template>`**

Insert after the description `<div class="form-group">` block (after `</div>` closing the textarea group, before the error/result paragraphs):

```html
      <!-- Optional photo upload -->
      <div class="form-group photo-group">
        <label>Incident Photo <span class="optional-badge">optional</span></label>
        <p class="field-hint">Attach a photo so AI can visually assess damage severity.</p>

        <label class="photo-upload-btn" :class="{ 'has-photo': imagePreviewUrl }">
          <input
            type="file"
            accept="image/*"
            style="display:none"
            :disabled="submitting"
            @change="onPhotoSelected"
          />
          <span v-if="!imagePreviewUrl">+ Attach Photo</span>
          <span v-else>Change Photo</span>
        </label>

        <div v-if="imagePreviewUrl" class="photo-preview-wrap">
          <img :src="imagePreviewUrl" class="photo-preview-thumb" alt="Incident photo preview" />
          <button type="button" class="remove-photo-btn" :disabled="submitting" @click="removePhoto">
            Remove
          </button>
        </div>
      </div>
```

- [ ] **Step 4: Add scoped CSS for the photo upload UI**

Append inside the `<style scoped>` block:

```css
.photo-group { margin-top: 4px; }

.field-hint {
  font-size: 12px;
  color: var(--c-muted);
  margin: 2px 0 10px;
  line-height: 1.5;
}

.optional-badge {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--c-muted);
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 4px;
  padding: 1px 6px;
  margin-left: 6px;
  vertical-align: middle;
}

.photo-upload-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 18px;
  border: 1.5px dashed var(--c-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--c-accent);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: var(--c-bg);
}
.photo-upload-btn:hover { border-color: var(--c-accent); background: var(--c-surface); }
.photo-upload-btn.has-photo { border-style: solid; border-color: var(--c-accent); }

.photo-preview-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

.photo-preview-thumb {
  width: 80px;
  height: 60px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border);
}

.remove-photo-btn {
  font-size: 12px;
  color: #ef4444;
  background: none;
  border: 1px solid #fca5a5;
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  cursor: pointer;
  transition: background 0.15s;
}
.remove-photo-btn:hover { background: #fef2f2; }
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ReportIncidentView.vue
git commit -m "feat(frontend): add optional photo upload to incident report form"
```

---

## Task 4: UX Validation (Manual Checklist)

> This task defines how the final UX is validated. Run these checks with the app deployed via `docker compose up`. Open the app in a browser and navigate to **Report Incident** (`/report-incident`).

**Pre-condition:** Docker is running, Kong gateway is up, the user is logged in with an active booking (so booking/vehicle fields are auto-filled).

- [ ] **VAL-1 — No photo, baseline behaviour unchanged**
  1. Fill in description only. Submit.
  2. Expected: submission succeeds, result card shows `Report ID`, `Severity`, `Status: submitted`.
  3. Check `docker logs openai_wrapper` — confirms `gpt-4o` model was used, no image in payload.

- [ ] **VAL-2 — Attach photo, see preview**
  1. Click **+ Attach Photo**.
  2. Select a JPEG or PNG from your filesystem.
  3. Expected: thumbnail appears below the button (80×60 px crop), button text changes to **Change Photo**.

- [ ] **VAL-3 — Remove photo**
  1. With a photo attached, click **Remove**.
  2. Expected: thumbnail disappears, button reverts to **+ Attach Photo**, `imageBase64` is cleared (submit without photo proceeds as VAL-1).

- [ ] **VAL-4 — Submit with photo**
  1. Attach a photo of a car scratch (or any image).
  2. Fill description: "Scratch on front bumper."
  3. Submit.
  4. Expected: result card appears with `severity` value. 
  5. Check `docker logs openai_wrapper` — log line shows request received with non-empty `image_base64` key and model `gpt-4o`.

- [ ] **VAL-5 — Severity changes with photo context**
  1. Submit text-only: "Something happened." → note severity (likely `medium` / `low`).
  2. Re-submit same description + attach a photo of visible heavy damage.
  3. Expected: severity may differ (e.g. `high`) because GPT-4o now has visual context.
  *(Note: result is non-deterministic. The goal is confirming the image is actually reaching the model, not a specific outcome.)*

- [ ] **VAL-6 — Non-image file is blocked**
  1. Click **+ Attach Photo**, try to select a `.pdf` or `.txt` file.
  2. Expected: OS file picker only shows image files (`accept="image/*"`). Non-image files are greyed out or unselectable.

- [ ] **VAL-7 — Large image does not break submission**
  1. Attach a large photo (~3–5 MB JPEG).
  2. Submit.
  3. Expected: submission completes without timeout error. (Kong `client_max_body_size=0` permits unlimited body.)

- [ ] **VAL-8 — Form disables during submission**
  1. Click Submit while already submitting (rapid double-click).
  2. Expected: submit button shows `Submitting...` and is disabled; photo file input is also disabled during submission.

---

## Self-Review Checklist (author use only)

| # | Check | Status |
|---|-------|--------|
| 1 | All spec requirements covered (upgrade model, base64 flow, optional field, frontend preview) | ✅ |
| 2 | No TBD / TODO / placeholder steps | ✅ |
| 3 | `image_base64` field name consistent across all 3 tasks | ✅ |
| 4 | `openai_payload` variable name used in Task 2 doesn't conflict with any existing variable in `report_issue/app.py` | ✅ |
| 5 | `imageBase64` / `imagePreviewUrl` refs added before `submitReport` which references them | ✅ |
| 6 | VAL tests cover: no-photo baseline, photo preview, remove, submit with photo, large file, disabled state | ✅ |
