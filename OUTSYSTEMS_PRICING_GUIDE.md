# OutSystems Migration Guide: Pricing Service

This document covers replacing the hardcoded Python Pricing microservice with an OutSystems-exposed REST API backed by a real database.

---

## Status Legend

- **FIXED** = Already patched in the codebase
- **NEEDS OUTSYSTEMS FIX** = Must be fixed inside OutSystems Service Studio
- **NEEDS CODE** = Requires new code to be written

---

## Architecture Change

**Before (hardcoded Python):**
```
book_car composite       ──► pricing_service:5005 (Docker, hardcoded dict)
cancel_booking composite ──► pricing_service:5005 (Docker, hardcoded dict)
```

**After (OutSystems via Kong):**
```
book_car composite       ──► kong:8000 ──► OutSystems PricingService (cloud DB)
cancel_booking composite ──► kong:8000 ──► OutSystems PricingService (cloud DB)
```

The `pricing_service` Docker container is removed. Both composites now route through Kong (internal Docker DNS), which proxies to OutSystems. **No composite Python code changes needed.**

---

## Why the Pricing Service?

| Reason | Detail |
|--------|--------|
| No infrastructure deps | No RabbitMQ, no Firestore, no Redis |
| Read-only consumers | Both composites only call GET |
| Hardcoded data today | Rates and tiers are literals in `app.py` — trivially stored in OutSystems entities |
| Admin-configurable | Moving to OutSystems lets an admin update prices without redeploying Docker |
| Clean replacement | Route through Kong — composites need zero code changes |

---

## Task 1 — Create OutSystems Application and Module

1. Open **OutSystems Studio** and connect to your personal environment.
2. Create a **New Application**:
   - Select **From Scratch → As a Service**
   - Name: `ESD Car Rental Services` (or reuse existing)
3. Create a **New Module**:
   - Name: `TB_PricingService`
   - Type: **Service**
4. Open the newly created module.

---

## Task 2 — Create Entities (Database Tables)

Under the **Data** tab, right-click **Entities → Database** and create two entities.

### Entity 1: `VehicleRate`

| Attribute | Type | Properties |
|-----------|------|------------|
| `Id` | Long Integer | Auto Number (PK) — auto-created |
| `VehicleType` | Text (50) | Mandatory — store lowercase: `"sedan"`, `"suv"`, `"van"` |
| `RatePerHour` | Decimal | Mandatory |

### Entity 2: `CancellationPolicyTier`

| Attribute | Type | Properties |
|-----------|------|------------|
| `Id` | Long Integer | Auto Number (PK) — auto-created |
| `HoursBefore` | Decimal | Mandatory — threshold in hours before pickup |
| `RefundPercent` | Integer | Mandatory — 0–100 |

> These replace the two hardcoded constants in `atomic/pricing_service/app.py`:
> ```python
> RATES = {"sedan": 12.50, "suv": 18.00, "van": 15.00}
> tiers = [{"hours_before": 24, "refund_percent": 100}, ...]
> ```

---

## Task 3 — Setup Data Structures

Under the **Data** tab, create the following Structures. For every attribute, set the **Name in JSON** exactly as shown — this controls the JSON key name in the API response.

> **Note on Name in JSON:** For most structures the OutSystems attribute name is PascalCase and you must manually override "Name in JSON" to the snake_case value shown. For `RateItem` and `PricingRatesResponse`, the attribute names are already snake_case — OutSystems will auto-generate the matching "Name in JSON" so no override is needed.

---

### Structure: `RateItem`

> One entry in the rates list. Contains only the two scalar fields — **do NOT add a `rates` attribute here** (that causes a recursive structure error).

| Attribute (OutSystems) | Type | Name in JSON (auto) |
|------------------------|------|-------------|
| `vehicle_type` | Text | `vehicle_type` |
| `rate_per_hour` | Decimal | `rate_per_hour` |

---

### Structure: `PricingRatesResponse`

> The full response wrapper for `GET /pricing`. The `rates` attribute is a list of `RateItem` — this is the only place it appears.

| Attribute (OutSystems) | Type | Name in JSON (auto) |
|------------------------|------|-------------|
| `status` | Text | `status` |
| `rates` | RateItem List | `rates` |

---

### Structure: `CalculateResponse`

> Response for `GET /pricing/calculate`. `Total` is the only field `book_car` reads.

| Attribute (OutSystems) | Type | Name in JSON |
|------------------------|------|-------------|
| `Status` | Text | `status` |
| `VehicleType` | Text | `vehicle_type` |
| `Hours` | Decimal | `hours` |
| `Total` | Decimal | `total` |

---

### Structure: `PolicyTier`

> One tier entry. `HoursBefore` and `RefundPercent` are what `cancel_booking` reads — both must be snake_case in JSON.

| Attribute (OutSystems) | Type | Name in JSON |
|------------------------|------|-------------|
| `HoursBefore` | Decimal | `hours_before` |
| `RefundPercent` | Integer | `refund_percent` |

---

### Structure: `PolicyResponse`

> The full response wrapper for `GET /pricing/policy`.

| Attribute (OutSystems) | Type | Name in JSON |
|------------------------|------|-------------|
| `Status` | Text | `status` |
| `Tiers` | PolicyTier List | `tiers` |

---

### Structure: `ErrorResponse`

| Attribute (OutSystems) | Type | Name in JSON |
|------------------------|------|-------------|
| `Status` | Text | `status` |
| `Message` | Text | `message` |

---

## Task 4 — Expose REST API Endpoints

Under **Logic → Integrations → REST**, right-click and select **Expose REST API**.

**REST API settings:**

| Field | Value |
|-------|-------|
| Name | `PricingService` |
| URL | `/TB_PricingService/rest/PricingService` |
| HTTP Security | SSL/TLS |
| Authentication | None |

> The base URL above is auto-generated from the module and API name. Do not change it.

---

### Prerequisite: Add SetStatusCode Dependency

Before building any endpoint logic, add the `SetStatusCode` action so you can return proper HTTP error codes.

1. Logic tab → expand **Server Actions** → right-click **(System)** → **Manage Dependencies**
2. On the left, select **HTTPRequestHandler (extension)**
3. On the right, check **SetStatusCode** → click **Apply**

`SetStatusCode` will now appear under Logic → Server Actions → HTTPRequestHandler.

Also add a User Exception for error flows:

1. Logic tab → right-click **Exceptions** → **Add Exception** → name it `PricingException`

---

### Endpoint 1: GET — List All Rates

**Method settings:**

| Field | Value |
|-------|-------|
| Name | `GetPricing` |
| URL Path | `/rates` |
| HTTP Method | GET |

> Full URL: `https://your-env.outsystemscloud.com/TB_PricingService/rest/PricingService/rates`
> Note: Do NOT use `/` as the URL path — it causes OutSystems routing conflicts with sibling methods. Use `/rates` instead.
> This endpoint is not called by any composite — it is for direct testing only.

**Output Parameter:** `Response` (PricingRatesResponse)

**Local Variable to add first** (right-click the method → Add Local Variable):

| Name | Type |
|------|------|
| `NewRateItem` | RateItem |

**Logic Flow — nodes in order:**

| # | Node | Configuration |
|---|------|---------------|
| 1 | **Aggregate** — name it `GetAllVehicleRates` | Source: `VehicleRate` (drag from Data tab). No filter. Sort: `VehicleRate.VehicleType` Ascending. |
| 2 | **Assign** | `Response.status = "ok"` |
| 3 | **For Each** | List = `GetAllVehicleRates.List` |
| 3a | **Assign** *(inside loop body)* | `NewRateItem.vehicle_type = GetAllVehicleRates.List.Current.VehicleRate.VehicleType` `NewRateItem.rate_per_hour = GetAllVehicleRates.List.Current.VehicleRate.RatePerHour` |
| 3b | **ListAppend** *(inside loop body, after 3a)* | List = `Response.rates` · Element = `NewRateItem` · Find ListAppend under Logic → Server Actions → (System) → List |
| 4 | **End** | (loop cycles back automatically; place End after the For Each exits) |

> OutSystems REST APIs serialize the output parameter automatically — do **not** add a "JSON Serialize" node.

**Expected response:**
```json
{
  "status": "ok",
  "rates": [
    {"vehicle_type": "sedan", "rate_per_hour": 12.50},
    {"vehicle_type": "suv",   "rate_per_hour": 18.00},
    {"vehicle_type": "van",   "rate_per_hour": 15.00}
  ]
}
```

---

### Endpoint 2: GET — Calculate Total Price

> Right-click the **PricingService** REST API (same parent as GetPricing) → **Add REST API Method**

**Method settings:**

| Field | Value |
|-------|-------|
| Name | `GetPricingCalculate` |
| URL Path | `/calculate` |
| HTTP Method | GET |

> Full URL: `https://your-env.outsystemscloud.com/TB_PricingService/rest/PricingService/calculate`
> Kong routes `GET /api/pricing/calculate` → strips `/api/pricing` → forwards `/calculate` → hits this method.

**Input Parameters** — right-click `GetPricingCalculate` → **Add Input Parameter** for each:

| Name | Type | Receive In |
|------|------|------------|
| `vehicle_type` | Text | **URL** (default for GET — verify this is set) |
| `hours` | Decimal | **URL** (default for GET — verify this is set) |

> These become query string params: `?vehicle_type=sedan&hours=3`. OutSystems sets "Receive In" to URL automatically for GET methods, but double-check in the parameter properties panel.

**Output Parameter:** `Response` (CalculateResponse)

**Logic Flow — nodes in order:**

**Node 1 — If**
```
vehicle_type = "" or hours <= 0
```
→ True: **SetStatusCode** `400` → **Raise Exception** `PricingException` with message:
```
"Invalid parameters"
```
→ leads to End

**Node 2 — Aggregate**, name it `GetVehicleRateByType`
- Source: `VehicleRate`
- Filter:
```
ToLower(VehicleRate.VehicleType) = ToLower(vehicle_type)
```

**Node 3 — If**
```
GetVehicleRateByType.Count = 0
```
→ True: **SetStatusCode** `400` → **Raise Exception** `PricingException` with message:
```
"Invalid vehicle_type"
```
→ leads to End

**Node 4 — Assign** (one Assign node, four rows):
```
Response.Status = "ok"
```
```
Response.VehicleType = vehicle_type
```
```
Response.Hours = hours
```
```
Response.Total = Round(GetVehicleRateByType.List.Current.VehicleRate.RatePerHour * hours, 2)
```

**Node 5 — End**

> `ToLower()` on both sides prevents case mismatch — the composite sends lowercase (`sedan`) but the DB may store any case.

**Expected response** (`?vehicle_type=sedan&hours=3`):
```json
{
  "status": "ok",
  "vehicle_type": "sedan",
  "hours": 3.0,
  "total": 37.50
}
```

> `book_car/app.py` line 89: `total_price = r.json().get("total", 0)` — **`total` is load-bearing.**

---

### Endpoint 3: GET — Get Cancellation Policy

**Method settings:**

| Field | Value |
|-------|-------|
| Name | `GetPricingPolicy` |
| URL Path | `/policy` |
| HTTP Method | GET |

> Full URL: `https://your-env.outsystemscloud.com/TB_PricingService/rest/PricingService/policy`
> Kong routes `GET /api/pricing/policy` → strips `/api/pricing` → forwards `/policy` → hits this method.

**Output Parameter:** `Response` (PolicyResponse)

**Local Variable to add first** (right-click the method → Add Local Variable):

| Name | Type |
|------|------|
| `NewPolicyTier` | PolicyTier |

**Logic Flow — nodes in order:**

| # | Node | Configuration |
|---|------|---------------|
| 1 | **Aggregate** — name it `GetAllPolicyTiers` | Source: `CancellationPolicyTier` (drag from Data tab). No filter. Sort: `CancellationPolicyTier.HoursBefore` Descending. |
| 2 | **Assign** | `Response.Status = "ok"` |
| 3 | **For Each** | List = `GetAllPolicyTiers.List` |
| 3a | **Assign** *(inside loop body)* | `NewPolicyTier.HoursBefore = GetAllPolicyTiers.List.Current.CancellationPolicyTier.HoursBefore` `NewPolicyTier.RefundPercent = GetAllPolicyTiers.List.Current.CancellationPolicyTier.RefundPercent` |
| 3b | **ListAppend** *(inside loop body, after 3a)* | List = `Response.Tiers` · Element = `NewPolicyTier` |
| 4 | **End** | |

> OutSystems REST APIs serialize the output parameter automatically — do **not** add a "JSON Serialize" node.

**Expected response:**
```json
{
  "status": "ok",
  "tiers": [
    {"hours_before": 24, "refund_percent": 100},
    {"hours_before": 1,  "refund_percent": 50},
    {"hours_before": 0,  "refund_percent": 0}
  ]
}
```

> `cancel_booking/app.py` lines 74–79 reads `tiers`, `hours_before`, `refund_percent` — **all three are load-bearing.**

---

### Add Exception Handling Inside Each Method

> **Note:** Exposed REST APIs in OutSystems have no global OnException handler. Error handling must be added directly inside each method's logic flow using an **Exception Handler** node.

For each method that has error paths (`GetPricingCalculate` in particular):

1. Open the method's logic flow (double-click the method)
2. From the toolbox on the left, drag an **Exception Handler** node into the flow
3. Set **Exception** to `All Exceptions` (or your specific `PricingException`)
4. Inside the exception handler branch, add **SetStatusCode** with `StatusCode = 400`
5. Add **End**

**Exception Handler branch:**

| Node | Configuration |
|------|---------------|
| **SetStatusCode** | StatusCode = `400` |
| **End** | |

---

## Task 5 — Seed Initial Data

### VehicleRate records

| VehicleType | RatePerHour |
|-------------|-------------|
| `sedan` | `12.50` |
| `suv` | `18.00` |
| `van` | `15.00` |

> Store `VehicleType` in lowercase to match what the composite sends as query params.

### CancellationPolicyTier records

| HoursBefore | RefundPercent |
|-------------|---------------|
| `24` | `100` |
| `1` | `50` |
| `0` | `0` |

**Easiest method:** Data tab → right-click entity → **View Data** → add rows directly in Service Studio.

**Or use a Timer** (`SeedPricingData` Server Action):
```
→ Aggregate VehicleRate — if Count > 0, End (already seeded)
→ CreateRecord VehicleRate (VehicleType="sedan", RatePerHour=12.50)
→ CreateRecord VehicleRate (VehicleType="suv",   RatePerHour=18.00)
→ CreateRecord VehicleRate (VehicleType="van",   RatePerHour=15.00)
→ CreateRecord CancellationPolicyTier (HoursBefore=24, RefundPercent=100)
→ CreateRecord CancellationPolicyTier (HoursBefore=1,  RefundPercent=50)
→ CreateRecord CancellationPolicyTier (HoursBefore=0,  RefundPercent=0)
```

---

## Task 6 — Publish and Test

1. Click **Publish** in OutSystems Studio.
2. Right-click `PricingService` REST API → **Open Documentation** to confirm the URLs.
3. Test directly in Postman using the OutSystems URL paths (note: `/`, `/calculate`, `/policy` — not `/pricing/...`):

```bash
# List rates
GET https://personal-fptjqc79.outsystemscloud.com/TB_PricingService/rest/PricingService/

# Calculate (sedan, 3 hours)
GET https://personal-fptjqc79.outsystemscloud.com/TB_PricingService/rest/PricingService/calculate?vehicle_type=sedan&hours=3

# Policy tiers
GET https://personal-fptjqc79.outsystemscloud.com/TB_PricingService/rest/PricingService/policy
```

> The `/pricing` prefix only exists in Kong's routing (`/api/pricing`). OutSystems itself knows nothing about it — its paths are just `/`, `/calculate`, `/policy`.

---

## Task 7 — Update Kong

In [kong.yml](kong.yml), update the pricing service block (lines 391–432):

**Before:**
```yaml
  - name: pricing-service
    url: http://pricing_service:5005
    routes:
      - name: pricing-route
        paths:
          - /api/pricing
        strip_path: false
```

**After:**
```yaml
  - name: pricing-service
    url: https://personal-fptjqc79.outsystemscloud.com/TB_PricingService/rest/PricingService
    routes:
      - name: pricing-route
        paths:
          - /api/pricing
        strip_path: true
```

> **`strip_path: true`** is required. It strips `/api/pricing` before forwarding, so:
> - `GET /api/pricing` → forwards to OutSystems `/`
> - `GET /api/pricing/calculate` → forwards to OutSystems `/calculate`
> - `GET /api/pricing/policy` → forwards to OutSystems `/policy`
>
> Keep all existing CORS, rate-limiting, and JWT plugins unchanged.

---

## Task 8 — Update Docker Compose

In [docker-compose.yml](docker-compose.yml), make three changes:

### 8a. Comment out the `pricing_service` container

```yaml
# pricing_service:
#   build:
#     context: ./atomic/pricing_service
#   container_name: pricing_service
#   ports:
#     - "5005:5005"
#   networks:
#     - rental-net
#   healthcheck:
#     test: ["CMD", "curl", "-f", "http://localhost:5005/health"]
#     interval: 15s
#     timeout: 5s
#     retries: 3
#     start_period: 20s
#   restart: unless-stopped
```

### 8b. Remove `pricing_service` from `depends_on`

Find and remove `pricing_service` from the `depends_on` blocks of both `book_car` and `cancel_booking`.

### 8c. Route composites through Kong instead of directly to pricing

Both composites use `PRICING_SERVICE_HOST` to build their request URL. Point them at Kong's internal Docker DNS address — **no Python code changes needed**:

```yaml
book_car:
  environment:
    PRICING_SERVICE_HOST: kong:8000

cancel_booking:
  environment:
    PRICING_SERVICE_HOST: kong:8000
```

**How this works:** The composite code calls `http://kong:8000/api/pricing/calculate` → Kong receives it, matches the `/api/pricing` route, strips the prefix, and forwards `/calculate` to OutSystems over HTTPS. The composites stay on `http://` internally (Docker network) and Kong handles the HTTPS leg to OutSystems.

---

## Field Mapping Reference

The only fields actually consumed by the composite services:

| Composite | Endpoint called | Field read from response | OutSystems attribute | Name in JSON |
|-----------|----------------|--------------------------|---------------------|-------------|
| `book_car` | `/api/pricing/calculate` | `r.json().get("total", 0)` | `CalculateResponse.Total` | **`total`** |
| `cancel_booking` | `/api/pricing/policy` | `r.json().get("tiers", [])` | `PolicyResponse.Tiers` | **`tiers`** |
| `cancel_booking` | `/api/pricing/policy` | `tier.get("hours_before", 0)` | `PolicyTier.HoursBefore` | **`hours_before`** |
| `cancel_booking` | `/api/pricing/policy` | `tier.get("refund_percent", 0)` | `PolicyTier.RefundPercent` | **`refund_percent`** |

All other fields (`status`, `vehicle_type`, `hours`, `rate_per_hour`) are informational only.

---

## Known Issues and Fixes

### Issue 1: `RateItem` recursive structure error in Service Studio

**Symptom:** `Invalid Structure — RateItem.rates defines a nested recursive Structure data type definition`

**Cause:** The `Rates` attribute (type `RateItem List`) was added inside `RateItem` instead of `PricingRatesResponse`.

**Fix:** Open `RateItem`, delete the `rates` attribute. Open `PricingRatesResponse`, add `rates` there as type `RateItem List`.

---

### Issue 2: `/pricing/calculate` returns 0 or wrong total

**Cause:** OutSystems string comparison is case-sensitive. The composite sends `vehicle_type=sedan` (lowercase) but the DB record may have `Sedan` or `SEDAN`.

**Fix in Service Studio:** In the GetPricingCalculate Aggregate filter, use:
```
ToLower(VehicleRate.VehicleType) = ToLower(vehicle_type)
```

Also ensure seed data stores `VehicleType` in lowercase (`sedan`, `suv`, `van`).

---

### Issue 3: `/pricing/policy` tiers list is empty

**Cause:** `CancellationPolicyTier` table has no records — seeding was skipped.

**Fix:** Data tab → right-click `CancellationPolicyTier` → **View Data** → add the three tier records manually.

---

### Issue 4: Kong returns 301 redirect

**Cause:** Trailing slash mismatch on the Kong service URL.

**Fix:** Remove the trailing slash from the Kong service URL (the method URL paths `/`, `/calculate`, `/policy` already handle the path correctly):
```yaml
url: https://personal-fptjqc79.outsystemscloud.com/TB_PricingService/rest/PricingService
```

---

### Issue 5: `book_car` composite returns 502 "Pricing service error"

**Cause:** Either Kong is not running, `PRICING_SERVICE_HOST` is not set to `kong:8000`, or the `total` Name in JSON is wrong.

**Diagnosis:**
```bash
docker logs book_car
```
Look for the exact URL being called and the raw response body.

**Fix checklist:**
- `PRICING_SERVICE_HOST=kong:8000` in docker-compose.yml
- `CalculateResponse.Total` has Name in JSON = `total`
- OutSystems `/calculate` endpoint returns HTTP 200 (test directly in Postman first)

---

### Issue 6: `cancel_booking` always gives 0% refund

**Cause:** The policy endpoint failed silently — the composite defaults to 0% refund on any error.

**Fix:** Test the policy endpoint directly first:
```bash
curl https://personal-fptjqc79.outsystemscloud.com/TB_PricingService/rest/PricingService/policy
```
If `tiers` is empty → seed the data (Task 5).
If the request fails → check Kong routing with `strip_path: true`.

---

## Summary Table

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | `RateItem` recursive structure (`rates` attribute in wrong struct) | Critical | NEEDS OUTSYSTEMS FIX |
| 2 | `Name in JSON` not overridden to snake_case for `CalculateResponse`, `PolicyTier`, `PolicyResponse` (Note: `RateItem` and `PricingRatesResponse` use snake_case attribute names directly — no override needed) | Critical | NEEDS OUTSYSTEMS FIX |
| 3 | Method URL Paths left as default (`/GetPricing` etc.) | Critical | NEEDS OUTSYSTEMS FIX |
| 4 | Kong `strip_path: false` not changed to `true` | Critical | NEEDS CODE (`kong.yml`) |
| 5 | `PRICING_SERVICE_HOST` not updated to `kong:8000` | Critical | NEEDS CODE (`docker-compose.yml`) |
| 6 | `VehicleType` case-sensitive filter | High | NEEDS OUTSYSTEMS FIX |
| 7 | Empty `CancellationPolicyTier` table | High | NEEDS OUTSYSTEMS FIX (seed data) |
| 8 | `pricing_service` not removed from `depends_on` | Medium | NEEDS CODE (`docker-compose.yml`) |

---

## API Compatibility Checklist

```json
// GET /api/pricing  (OutSystems: GET /)
{
  "status": "ok",
  "rates": [
    {"vehicle_type": "sedan", "rate_per_hour": 12.50},
    {"vehicle_type": "suv",   "rate_per_hour": 18.00},
    {"vehicle_type": "van",   "rate_per_hour": 15.00}
  ]
}

// GET /api/pricing/calculate?vehicle_type=sedan&hours=3  (OutSystems: GET /calculate)
{
  "status": "ok",
  "vehicle_type": "sedan",
  "hours": 3.0,
  "total": 37.50
}

// GET /api/pricing/policy  (OutSystems: GET /policy)
{
  "status": "ok",
  "tiers": [
    {"hours_before": 24, "refund_percent": 100},
    {"hours_before": 1,  "refund_percent": 50},
    {"hours_before": 0,  "refund_percent": 0}
  ]
}
```
