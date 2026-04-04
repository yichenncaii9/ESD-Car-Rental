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

**Fix:** Already applied. The import in `ReportIncidentView.vue` uses:
```js
import(/* @vite-ignore */ '../components/DebugReportPanel.vue').catch(() => ({ render: () => null }))
```

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
