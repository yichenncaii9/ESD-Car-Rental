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

## 14. K8s pods stuck in `ContainerCreating` — missing Secrets

**Symptom:** Many pods (driver-service, booking-service, vehicle-service, composites, activity-log) stay in `ContainerCreating` indefinitely. `kubectl describe pod` shows:
```
MountVolume.SetUp failed for volume "firebase-sa": secret "firebase-sa" not found
```
Or wrappers (openai, googlemaps, stripe) show `CreateContainerConfigError` with:
```
secret "api-keys" not found
```

**Cause:** K8s Secrets are not stored in git (correctly). A fresh cluster has no secrets. All service pods that need Firebase or API keys will block on mount until the secrets exist.

**Fix:** Run once after cluster setup or after wiping the cluster:
```bash
# 1. Firebase service account (for all Firestore-connected services)
kubectl create secret generic firebase-sa \
  --from-file=firebase-service-account.json=./firebase-service-account.json

# 2. API keys (for openai-wrapper, googlemaps-wrapper, stripe-wrapper)
kubectl create secret generic api-keys \
  --from-literal=OPENAI_API_KEY="<from .env>" \
  --from-literal=GOOGLE_MAPS_API_KEY="<from .env>" \
  --from-literal=STRIPE_SECRET_KEY="<from Stripe dashboard>"
```

After creating secrets, restart the stuck deployments:
```bash
kubectl rollout restart deployment --all
```

**Note:** Pods stuck in ContainerCreating BEFORE the secret was created will not automatically recover — they require a rollout restart.

---

## 12. K8s frontend calls wrong Kong port — CORS blocked, profile save fails

**Symptom:** Frontend served from `http://localhost:30080` (K8s NodePort) sends API calls to `http://localhost:8000` (docker-compose Kong) instead of `http://localhost:30000` (k8s Kong NodePort). Browser blocks the request with:
```
Access-Control-Allow-Origin: http://localhost:8080 ≠ http://localhost:30080
```
Users see "save failed, please try again" and are re-prompted for profile completion because the driver POST silently fails.

**Root cause:** Vite bakes `VITE_API_BASE_URL` into the JS bundle at Docker build time. The default in `scripts/build-images.sh` was `http://localhost:8000`. When deployed to k8s, the Kong proxy is on NodePort `30000`, not `8000`.

**Fix (already applied):**
- `scripts/build-images.sh` default changed to `http://localhost:30000`
- `k8s/kong/kong.yml` CORS origins updated to include `http://localhost:30080`
- Rebuild frontend image: `docker build -t esd-frontend:latest --build-arg VITE_API_BASE_URL=http://localhost:30000 ./frontend`
- Redeploy: `kubectl rollout restart deployment/frontend`

**Key rule:** Always use `http://localhost:30000` as the API base URL when building for k8s. The docker-compose dev environment uses `http://localhost:8000`.

**Regression trap:** `deploy-k8s.sh` may export `VITE_API_BASE_URL=http://localhost:30000`, but if `build-images.sh` re-sources `.env` afterward, `.env` can overwrite it back to `http://localhost:8000`. Preserve the exported override when building for k8s.

---

## 15. K8s Flask pods fail health probes with HTTP 400, then Kong returns 502/503

**Symptom:** `vehicle-service`, `booking-service`, or `report-service` pods keep restarting in k8s, while Kong returns `502` for routes like `/api/vehicles` and composites like `/api/book-car` fail with `503`.

**Cause:** These Flask services set `TRUSTED_HOSTS`. Kubernetes health probes hit `/health` using a pod-IP host header, which Flask rejects with `400`, so kubelet marks the pod unhealthy and keeps restarting it.

**Important:** This is a different failure mode from error #9. Error #9 is the older Docker/internal-DNS underscore problem (`websocket_server` vs `websocket-server`, `booking_service` vs `booking-service`). That older bug breaks service-to-service calls because Flask rejects underscored `Host` headers. This k8s bug happens even with correctly hyphenated service names, because kubelet probes `/health` with the pod IP as the host.

**Fix:** In the k8s Deployment probes, send `Host: localhost`:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5001
    httpHeaders:
      - name: Host
        value: localhost
readinessProbe:
  httpGet:
    path: /health
    port: 5001
    httpHeaders:
      - name: Host
        value: localhost
```

This is now applied to the affected services. Redeploy with `./scripts/deploy-k8s.sh`.

---

## 16. Stripe key change — dependency and rollout map

**Symptom:** You want to swap `STRIPE_SECRET_KEY` from placeholder/test to a real key and need to know what actually changes.

**Where Stripe is used:**
- `stripe-wrapper` reads `STRIPE_SECRET_KEY` from the `api-keys` K8s Secret or from `.env` in Docker Compose.
- `composite/book_car` calls `stripe-wrapper` for charges.
- `composite/cancel_booking` calls `stripe-wrapper` for refunds.
- The frontend currently sends the hardcoded test payment method `pm_card_visa`, so secret changes alone do NOT make the browser flow production-ready.

**K8s: change only the Stripe secret key**
- Update `.env` with `STRIPE_SECRET_KEY=...` if you want `scripts/setup-secrets.sh` to source it.
- Re-run `./scripts/setup-secrets.sh` or `./scripts/deploy-k8s.sh --apply`.
- Required pod restart: `stripe-wrapper`.
- Pods that depend on it functionally but do not need rebuilds: `composite-book-car`, `composite-cancel-booking`.
- No image rebuild is required for a secret-only change.

**Docker Compose: change only the Stripe secret key**
- Update `.env`.
- Recreate `stripe_wrapper` so it picks up the new env var:
```bash
docker compose up -d stripe_wrapper
```
- Dependent services (`composite_book_car`, `composite_cancel_booking`) do not need rebuilds for a secret-only change.

**If you want real live Stripe payments, not fallback/mock behavior**
- Secret change alone is not enough.
- The frontend still posts:
```js
payment_method: 'pm_card_visa'
```
- `stripe-wrapper` also defaults to `pm_card_visa` if none is passed.
- With a real live secret key, that test payment method will usually fail and the wrapper will fall back to mock IDs unless the app is changed.

**Production-readiness checklist**
- Update `STRIPE_SECRET_KEY`.
- Add/use a Stripe publishable key in the frontend.
- Replace the hardcoded `pm_card_visa` flow with real Stripe.js payment method creation.
- Rebuild the frontend image after frontend payment changes.
- Rebuild `stripe-wrapper` only if you change its code, not if you only change the secret.

**Risk map**
- Low risk: changing only `STRIPE_SECRET_KEY` for the existing mock-friendly flow. Usually only `stripe-wrapper` needs restart.
- Medium risk: switching from test secret to live secret while still sending `pm_card_visa`. Charges will fail and silently fall back to mock behavior, which can hide the misconfiguration.
- High risk: moving to real live payments. This touches frontend payment collection, Stripe publishable-key config, and end-to-end booking/refund behavior.

---

## 13. Kong DB-less mode loads stale config after `kubectl rollout restart`

**Symptom:** After redeploying Kong via `kubectl rollout restart`, the new configmap content is visible inside the pod (`cat /usr/local/kong/declarative/kong.yml` shows the right content) but `GET /plugins` via the admin API shows old values. CORS or JWT rules appear not to change.

**Cause:** Kong DB-less mode reads `KONG_DECLARATIVE_CONFIG` **once at startup**. Kubernetes mounts configmaps as volume-backed symlinks that are synced by the kubelet on a ~60s cycle. There is a race: the pod starts, Kong reads the file (gets stale content), then kubelet syncs the updated content. Now the file is correct but Kong already loaded the old config and won't reload it.

**Fix:** After `kubectl rollout restart deployment/kong`, push the config explicitly via admin API:
```bash
curl -X POST http://localhost:30001/config \
  -F "config=<k8s/kong/kong.yml"
```
This is automated in `scripts/deploy-k8s.sh` — it waits for Kong ready then POSTs the config.

**Verify the fix worked:**
```bash
curl -s http://localhost:30001/plugins | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print([p['config']['origins'] for p in d['data'] if p['name']=='cors'][0])"
```

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
