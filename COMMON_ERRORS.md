# Common Errors & Fixes

Reference for recurring issues in this project.

---

## 1. Kong 502 Bad Gateway after rebuilding containers

**Symptom:** All routes through `:8000` return 502. `docker-compose logs kong` shows `connect() failed (111: Connection refused) while connecting to upstream` with a stale IP.

**Cause:** Kong caches upstream DNS at startup. Rebuilding containers assigns new internal IPs; Kong still points to the old ones.

**Fix:**
```bash
docker-compose up --build -d && docker-compose restart kong
```

---

## 2. Frontend Docker build fails — `npm run build` exit code 1 (Mac/Windows compatibility)

**Symptom:** Teammate on a different OS gets build failure in the frontend Docker stage.

**Known causes & fixes:**

### 2a. `package-lock.json` platform mismatch
`npm ci` is strict about lockfile integrity. If `package-lock.json` was committed from a different OS/Node version it can fail.

**Fix:** Delete and regenerate before committing:
```bash
cd frontend && rm package-lock.json && npm install
```

### 2b. Gitignored component referenced by Vite (current project)
`DebugReportPanel.vue` is gitignored. Vite resolves dynamic imports at build time — even with `.catch()` — unless marked with `/* @vite-ignore */`. Teammates without the file get a build error.

**Fix:** Already applied. The import in `ReportIncidentView.vue` uses a split string so Rollup cannot statically resolve it at build time:
```js
import(/* @vite-ignore */ '../components/Debug' + 'ReportPanel.vue').catch(() => ({ render: () => null }))
```
Note: `/* @vite-ignore */` alone is insufficient — it suppresses Vite's warning but Rollup still resolves the path. The string split defeats static analysis entirely.

### 2c. Line endings (CRLF vs LF)
Windows commits CRLF line endings into shell scripts or `.env` files, breaking execution inside Linux containers.

**Fix:** Add to `.gitattributes`:
```
*.sh text eol=lf
.env* text eol=lf
```
Or convert manually: `sed -i 's/\r//' script.sh`

---

## 3. Pricing service error during booking (502 from `/api/book-car`)

**Symptom:** Book car flow fails at pricing step with "Pricing service error".

**Cause:** `composite_book_car` calls pricing via Kong (`PRICING_SERVICE_HOST: kong:8000`). The pricing Kong route had a JWT plugin — internal service calls carry no browser token, so Kong returned 401.

**Fix:** JWT plugin removed from the pricing route in `kong.yml`. Pricing is public read-only data and is called service-to-service only.

---

## 4. Firebase JWT 401 — `Invalid signature`

**Symptom:** All authenticated Kong routes return 401 with "Invalid signature".

**Cause:** Firebase rotates RS256 signing keys every ~7 days. Kong's `kong.yml` has the old public key hardcoded.

**Fix:**
1. Fetch current keys: `curl https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com`
2. Match the `kid` in your token header (use jwt.io to decode)
3. Update the matching `rsa_public_key` block in `kong.yml`
4. `docker-compose restart kong`

See `MEMORY.md` → `project_firebase_key_rotation.md` for the full procedure.

---

## 5. `/api/bookings/user/{uid}/active` returns 404

**Symptom:** CancelBookingView and ReportIncidentView fail to auto-fill booking fields.

**Cause:** The route exists in `booking_service/app.py` but the running container was built before it was added.

**Fix:** Rebuild the service:
```bash
docker-compose up --build -d booking_service && docker-compose restart kong
```

---

## 6. `ai_evaluation` is null on reports

**Symptom:** Reports in Firestore have `severity` set but `ai_evaluation: null`.

**Cause:** `composite/report_issue/app.py` was only passing `{"severity": ...}` to `PUT /api/reports/{id}/evaluation`, discarding the full OpenAI response.

**Fix:** Already applied. The composite now passes `{"severity": ..., "ai_evaluation": {severity, provider, status}}`.

---

## 7. RabbitMQ management UI unreachable from browser debug panel

**Symptom:** Debug panel shows `Failed to fetch` when trying to load queue stats.

**Cause:** Browser CORS blocks cross-origin requests to `localhost:15672`.

**Fix:** Open the management UI directly: [http://localhost:15672/#/queues](http://localhost:15672/#/queues) (guest / guest)

---

## 8. Kong JWT 401 — `No credentials found for given 'kid'`

**Symptom:** Authenticated routes (cancel-booking, report-issue, etc.) return 401 with `"No credentials found for given 'kid'"`. Other routes may work fine.

**Cause:** Firebase rotates RS256 keys every ~7 days. A new `kid` is now being issued that does not appear in `kong.yml`'s `jwt_secrets` list at all. This is different from error #4 ("Invalid signature") — there the kid exists but the key content is wrong; here the kid is entirely missing.

**How to diagnose:** Decode a fresh Firebase token at jwt.io and check the `kid` in the header. Compare against the `key:` fields in `kong.yml` consumers section.

**Fix:**
```bash
curl -s https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com \
  | python3 -c "
import sys, json, subprocess
keys = json.load(sys.stdin)
for kid, cert in keys.items():
    print(f'=== kid: {kid} ===')
    result = subprocess.run(['openssl', 'x509', '-pubkey', '-noout'],
        input=cert.encode(), capture_output=True)
    print(result.stdout.decode())
"
```
Add any kid not already in `kong.yml` consumers → `jwt_secrets`, then `docker-compose restart kong`.

See `MEMORY.md` → `project_firebase_key_rotation.md` for the full procedure.

---

## 9. Internal Docker HTTP calls return 400 — `Host '...' is not trusted`

**Symptom:** A worker or service making an internal HTTP call (e.g. `requests.post("http://websocket_server:6100/notify", ...)`) silently gets a 400 back. No exception is raised in Python (requests doesn't raise on 4xx). The receiving service logs nothing, and the calling service logs nothing — the failure is invisible.

**Cause:** Werkzeug 3.1's `host_is_trusted()` validates the `Host` header against the regex `[a-z0-9.-]+`. **Underscores are not in this set.** Docker Compose service names with underscores (e.g. `websocket_server`, `booking_service`) are valid Docker DNS names but fail Werkzeug's host regex, so Flask 3 returns 400 before the route handler runs.

Setting `app.config["TRUSTED_HOSTS"]` does NOT fix this — the regex check runs before the trusted-hosts check, and the IDNA encoder also rejects underscores, causing `return False` for every entry in the list.

**Fix:** Give the service a hyphenated network alias and update callers to use it:

In `docker-compose.yml` for the receiving service:
```yaml
services:
  websocket_server:
    networks:
      rental-net:
        aliases:
          - websocket-server   # hyphen passes Werkzeug's [a-z0-9.-]+ regex
```

In callers' environment:
```yaml
WEBSOCKET_SERVER_URL: http://websocket-server:6100   # was websocket_server
```

Then `docker-compose up -d --build <affected services>`.

**Note:** This affects any Flask 3 / Werkzeug 3.1+ service called internally by its underscored Docker service name. The bug is silent — add a `print(r.status_code, r.text)` after any `requests.post/get` if a call seems to vanish.

---

## 10. Frontend edits don't appear in the browser

**Symptom:** You edit a `.vue` file in `frontend/src/`, reload the browser, and nothing changes.

**Cause:** The frontend Docker container is a **pre-built static bundle** (Nginx serving files from `npm run build`). It is NOT a Vite dev server with HMR. Source edits on the host have no effect until the image is rebuilt.

**Fix:**
```bash
docker-compose up -d --build frontend
```
Then hard-refresh the browser (`Cmd+Shift+R` / `Ctrl+Shift+R`) to bypass the browser cache.

---

## 11. Service Dashboard shows "No pending reports" despite reports existing in Firestore

**Symptom:** The Service Dashboard loads, shows "No pending reports", even though `GET /api/reports/pending` returns data.

**Cause (API shape mismatch):** `report_service` returns `{"status": "ok", "data": [...]}`. The Vue component was extracting `res.data.reports` (undefined) then falling back to `res.data` (the whole object), so `reports.value` became a plain object instead of an array. `reports.length` was `undefined`, `v-if="reports.length > 0"` evaluated to false. The Socket.IO `findIndex` call then threw `TypeError` because `reports.value` was no longer an array, breaking real-time updates too.

**Fix:** Use `res.data.data || res.data.reports || []` and guard with `Array.isArray()`.

**Cause (WebSocket events not reaching frontend):** The workers post to `websocket_server` via its Docker service name, which contains an underscore — see error #9. The POST silently returned 400, so `socketio.emit("report_update", ...)` was never called.

**Combined checklist when dashboard is empty:**
1. Check the diagnostic panel (API fetch status + Socket.IO connection status).
2. Confirm `activity_log` logs show `[activity_log] Firestore write:` entries.
3. Confirm `websocket_server` logs show `[websocket_server] /notify received:` after each report.
4. If `/notify received` never appears: test with `docker exec activity_log python3 -c "import requests; r = requests.post('http://websocket-server:6100/notify', json={'test':1}, timeout=5); print(r.status_code)"` — should be 200.
5. If Socket.IO shows "Not connected": check browser console for `connect_error` and confirm port 6100 is reachable from the browser's perspective.
