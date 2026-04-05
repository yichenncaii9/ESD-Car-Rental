# Stripe Payment Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real Stripe card payment step to the Book Car flow so users see a price estimate and enter card details before confirming a booking.

**Architecture:** The backend (`composite/book_car/app.py`) already calls `stripe_wrapper/charge` with a `payment_method` field — it defaults to `pm_card_visa` when omitted. We add Stripe.js to the frontend to tokenize card details into a real `payment_method` ID and pass it through. No backend changes are needed. Price preview fetches from the already-Kong-routed `/api/pricing/calculate` endpoint. The flow is: select vehicle → see price → enter card → Stripe.js tokenizes → POST `/api/book-car` with `payment_method`.

**Tech Stack:** Vue 3 Composition API, `@stripe/stripe-js` (npm), Stripe Card Element, `VITE_STRIPE_PUBLISHABLE_KEY` env var, existing `/api/pricing/calculate` Kong route (GET, params: `vehicle_type`, `hours`).

---

## File Map

| File | Change |
|------|--------|
| `frontend/package.json` | Add `@stripe/stripe-js` dependency |
| `frontend/.env.example` | Add `VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...` |
| `frontend/src/views/BookCarView.vue` | Price preview + Stripe Card Element modal + pass `payment_method` |
| `docker-compose.yml` | Add `VITE_STRIPE_PUBLISHABLE_KEY` build-arg and env |
| `frontend/Dockerfile` | Add `VITE_STRIPE_PUBLISHABLE_KEY` ARG + ENV |

---

## Task 1: Install Stripe.js and Wire Publishable Key

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/.env.example`
- Modify: `docker-compose.yml`
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: Install @stripe/stripe-js**

```bash
cd /Applications/MAMP/htdocs/y2s2/ESD/ESDProj/frontend
npm install @stripe/stripe-js
```

Expected: `@stripe/stripe-js` appears in `package.json` dependencies, `package-lock.json` updated.

- [ ] **Step 2: Add env var to `.env.example`**

Open `frontend/.env.example`. Append:

```
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_replace_with_your_key
```

- [ ] **Step 3: Add build-arg to `docker-compose.yml`**

Find the `frontend` service block. It has a `build.args` section (or add one). Add:

```yaml
      VITE_STRIPE_PUBLISHABLE_KEY: ${VITE_STRIPE_PUBLISHABLE_KEY:-pk_test_placeholder}
```

under `build: args:`, and also add to `environment:` if present:

```yaml
      VITE_STRIPE_PUBLISHABLE_KEY: ${VITE_STRIPE_PUBLISHABLE_KEY:-pk_test_placeholder}
```

- [ ] **Step 4: Add ARG + ENV to `frontend/Dockerfile`**

Read the Dockerfile. Find the existing `ARG VITE_API_BASE_URL` line. Add immediately after it:

```dockerfile
ARG VITE_STRIPE_PUBLISHABLE_KEY
ENV VITE_STRIPE_PUBLISHABLE_KEY=$VITE_STRIPE_PUBLISHABLE_KEY
```

- [ ] **Step 5: Commit**

```bash
cd /Applications/MAMP/htdocs/y2s2/ESD/ESDProj
git add frontend/package.json frontend/package-lock.json frontend/.env.example docker-compose.yml frontend/Dockerfile
git commit -m "feat(frontend): add Stripe.js dependency and VITE_STRIPE_PUBLISHABLE_KEY wiring"
```

---

## Task 2: Price Preview in Booking Form

**Files:**
- Modify: `frontend/src/views/BookCarView.vue` (script + template + style)

The pricing service is reachable via Kong at `GET /api/pricing/calculate?vehicle_type=sedan&hours=2`. Response shape: `{ total: 25.00, ... }`. The `api` axios instance (imported as `import api from '../axios'`) already routes through Kong with the auth header.

- [ ] **Step 1: Add price preview refs and fetch function**

In `<script setup>`, after the `const hours = ref(2)` line, add:

```js
const estimatedPrice = ref(null)
const priceLoading   = ref(false)

async function fetchPrice() {
  if (!selectedVehicle.value || !hours.value) { estimatedPrice.value = null; return }
  priceLoading.value = true
  try {
    const res = await api.get('/api/pricing/calculate', {
      params: { vehicle_type: selectedVehicle.value.vehicle_type, hours: hours.value }
    })
    estimatedPrice.value = res.data.total ?? res.data.total_price ?? null
  } catch {
    estimatedPrice.value = null
  } finally {
    priceLoading.value = false
  }
}
```

- [ ] **Step 2: Trigger price fetch reactively**

Replace the existing `watch(selectedVehicle, ...)` block (the one that re-opens the popup) — keep it as-is and add a NEW watcher after it:

```js
watch([selectedVehicle, hours], () => {
  fetchPrice()
}, { immediate: false })
```

Also call `fetchPrice()` inside `selectVehicle()` after `bookingError.value = ''`:

```js
function selectVehicle(vehicle) {
  selectedVehicle.value = vehicle
  bookingError.value = ''
  bookingSuccess.value = ''
  fetchPrice()   // ← add this line
  // ... rest of existing function unchanged
```

- [ ] **Step 3: Add price display to template**

Inside `<form v-if="selectedVehicle" ...>`, after the Duration `<div class="form-group">` block and before `<p v-if="bookingError"`, add:

```html
        <div v-if="estimatedPrice !== null" class="price-preview">
          <span class="price-label">Estimated Total</span>
          <span class="price-amount">SGD {{ estimatedPrice.toFixed(2) }}</span>
        </div>
        <p v-else-if="priceLoading" class="price-loading">Calculating price…</p>
```

- [ ] **Step 4: Add price preview CSS**

Inside `<style scoped>`, append:

```css
.price-preview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--c-success-bg, #f0fdf4);
  border: 1px solid #86efac;
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  margin-bottom: 16px;
}
.price-label { font-size: 13px; font-weight: 600; color: var(--c-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.price-amount { font-size: 20px; font-weight: 800; color: var(--c-dark); }
.price-loading { font-size: 13px; color: var(--c-muted); margin-bottom: 16px; }
```

- [ ] **Step 5: Verify price renders**

Start the dev server or run docker compose. Select a vehicle, set hours to 3. The form should show "Estimated Total — SGD 37.50" (for sedan at $12.50/hr).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/BookCarView.vue
git commit -m "feat(frontend): add price estimate preview to booking form"
```

---

## Task 3: Stripe Card Element Payment Modal

**Files:**
- Modify: `frontend/src/views/BookCarView.vue` (script + template + style)

The Stripe Card Element is mounted into a `<div id="stripe-card-element">` inside a modal. On submit, `stripe.createPaymentMethod({ type: 'card', card: cardElement })` returns a `payment_method.id` which is then passed as `payment_method` in the `/api/book-car` POST body. The backend stripe_wrapper uses it instead of the default `pm_card_visa`.

- [ ] **Step 1: Add Stripe imports and refs**

At the top of `<script setup>`, add after the existing imports:

```js
import { loadStripe } from '@stripe/stripe-js'

const stripePublishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || ''
const paymentModalOpen = ref(false)
const stripeInstance   = ref(null)
const cardElement      = ref(null)
const cardError        = ref('')
const cardMounted      = ref(false)
```

- [ ] **Step 2: Add `openPaymentModal` and `mountCardElement` functions**

Add these functions after `fetchPrice()`:

```js
async function openPaymentModal() {
  if (!selectedVehicle.value || !pickupDatetime.value || !hours.value) {
    bookingError.value = 'Please select a vehicle, pickup time, and duration first.'
    return
  }
  if (existingBooking.value && isBookingActiveOrUpcoming(existingBooking.value)) {
    bookingError.value = 'You already have an active or upcoming booking. Cancel it first.'
    return
  }
  bookingError.value = ''
  paymentModalOpen.value = true
  await nextTick()
  await mountCardElement()
}

async function mountCardElement() {
  if (cardMounted.value) return
  if (!stripeInstance.value) {
    stripeInstance.value = await loadStripe(stripePublishableKey)
  }
  const elements = stripeInstance.value.elements()
  cardElement.value = elements.create('card', {
    style: {
      base: { fontSize: '15px', color: '#1a1a2e', fontFamily: 'inherit', '::placeholder': { color: '#94a3b8' } },
      invalid: { color: '#ef4444' },
    },
  })
  cardElement.value.mount('#stripe-card-element')
  cardElement.value.on('change', (event) => {
    cardError.value = event.error ? event.error.message : ''
  })
  cardMounted.value = true
}

function closePaymentModal() {
  paymentModalOpen.value = false
  if (cardElement.value) { cardElement.value.unmount(); cardElement.value = null }
  cardMounted.value = false
  cardError.value = ''
}
```

- [ ] **Step 3: Rewrite `submitBooking` to tokenize card then book**

Replace the existing `submitBooking` function entirely:

```js
async function submitBooking() {
  if (!selectedVehicle.value) return
  if (existingBooking.value && isBookingActiveOrUpcoming(existingBooking.value)) {
    bookingError.value = 'You already have an active or upcoming booking. Cancel it first.'
    return
  }
  if (!stripeInstance.value || !cardElement.value) {
    bookingError.value = 'Payment form not ready. Please try again.'
    return
  }

  submitting.value = true
  bookingError.value = ''
  bookingSuccess.value = ''

  try {
    // Step A: Tokenize card via Stripe.js
    const { paymentMethod, error } = await stripeInstance.value.createPaymentMethod({
      type: 'card',
      card: cardElement.value,
    })
    if (error) {
      bookingError.value = error.message
      return
    }

    // Step B: Submit booking with the payment_method ID
    const uid = authStore.currentUser?.uid
    const res = await api.post('/api/book-car', {
      user_uid:         uid,
      vehicle_id:       selectedVehicle.value.id,
      vehicle_type:     selectedVehicle.value.vehicle_type,
      pickup_datetime:  pickupDatetime.value,
      hours:            hours.value,
      payment_method:   paymentMethod.id,
    })

    bookingSuccess.value = `Booking confirmed! ID: ${res.data.booking_id || res.data.id}`
    closePaymentModal()
    selectedVehicle.value = null
    estimatedPrice.value = null
    await loadVehicles()
    await checkExistingBooking()
  } catch (err) {
    bookingError.value =
      err.response?.data?.error ||
      err.response?.data?.message ||
      'Booking failed. Please try again.'
  } finally {
    submitting.value = false
  }
}
```

- [ ] **Step 4: Change the form submit button to open the modal instead**

In the template, the form's `@submit.prevent="submitBooking"` fires when the user clicks "Confirm Booking" — but now we need a two-step flow: the form button opens the modal, and the modal has its own "Pay" button.

Change the form submit button:

```html
        <button type="button" class="btn-primary" :disabled="submitting || !estimatedPrice" @click="openPaymentModal">
          {{ submitting ? 'Booking...' : `Pay SGD ${estimatedPrice ? estimatedPrice.toFixed(2) : '—'} & Book` }}
        </button>
```

Remove `@submit.prevent="submitBooking"` from the `<form>` tag (change it to a plain `<form class="booking-form" :inert="!!existingBooking">`).

- [ ] **Step 5: Add payment modal to template**

Before the closing `</div>` of `.bookcar-page`, add:

```html
  <!-- Stripe payment modal -->
  <div v-if="paymentModalOpen" class="payment-overlay" @click.self="closePaymentModal">
    <div class="payment-modal">
      <div class="payment-modal__header">
        <span class="payment-modal__title">Complete Payment</span>
        <button type="button" class="payment-modal__close" @click="closePaymentModal">×</button>
      </div>

      <div class="payment-modal__summary">
        <span>{{ selectedVehicle?.vehicle_type }} · {{ selectedVehicle?.plate_number }}</span>
        <span class="payment-modal__amount">SGD {{ estimatedPrice?.toFixed(2) }}</span>
      </div>

      <div class="payment-modal__body">
        <label class="payment-modal__label">Card Details</label>
        <div id="stripe-card-element" class="stripe-card-box"></div>
        <p v-if="cardError" class="error-msg" style="margin-top:8px">{{ cardError }}</p>
        <p class="stripe-test-hint">Test card: <code>4242 4242 4242 4242</code> · any future expiry · any CVC</p>
      </div>

      <div class="payment-modal__footer">
        <button type="button" class="btn-primary payment-confirm-btn"
          :disabled="submitting || !!cardError"
          @click="submitBooking">
          {{ submitting ? 'Processing…' : `Pay SGD ${estimatedPrice?.toFixed(2)}` }}
        </button>
        <button type="button" class="payment-cancel-btn" :disabled="submitting" @click="closePaymentModal">
          Cancel
        </button>
      </div>
    </div>
  </div>
```

- [ ] **Step 6: Add payment modal CSS**

Append to `<style scoped>`:

```css
/* Payment modal */
.payment-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.55);
  z-index: 1000;
  display: flex; align-items: center; justify-content: center;
}
.payment-modal {
  background: #fff;
  border-radius: var(--radius);
  width: 100%; max-width: 440px;
  margin: 16px;
  box-shadow: 0 24px 60px rgba(0,0,0,0.22);
  overflow: hidden;
}
.payment-modal__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px 0;
}
.payment-modal__title { font-size: 16px; font-weight: 800; color: var(--c-dark); }
.payment-modal__close {
  width: 28px; height: 28px; border: none; border-radius: 50%;
  background: var(--c-bg); cursor: pointer; font-size: 18px;
  color: var(--c-muted); display: flex; align-items: center; justify-content: center;
}
.payment-modal__summary {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 24px;
  background: var(--c-bg);
  margin: 16px 24px;
  border-radius: var(--radius-sm);
  font-size: 14px; color: var(--c-dark);
}
.payment-modal__amount { font-weight: 800; font-size: 18px; }
.payment-modal__body { padding: 0 24px 8px; }
.payment-modal__label { font-size: 12px; font-weight: 600; color: var(--c-muted); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 8px; }
.stripe-card-box {
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  background: var(--c-bg);
  transition: border-color 0.15s;
}
.stripe-card-box:focus-within { border-color: var(--c-accent); }
.stripe-test-hint {
  font-size: 12px; color: var(--c-muted);
  margin-top: 10px; line-height: 1.5;
}
.stripe-test-hint code {
  font-family: monospace; background: var(--c-bg);
  padding: 1px 5px; border-radius: 3px;
}
.payment-modal__footer {
  display: flex; gap: 10px; padding: 16px 24px 24px;
}
.payment-confirm-btn { flex: 1; width: auto; font-size: 15px; padding: 13px; }
.payment-cancel-btn {
  padding: 13px 20px; border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm); font-size: 14px; font-weight: 600;
  color: var(--c-muted); background: transparent; cursor: pointer;
  transition: border-color 0.15s;
}
.payment-cancel-btn:hover:not(:disabled) { border-color: var(--c-dark); color: var(--c-dark); }
.payment-cancel-btn:disabled { opacity: 0.5; cursor: not-allowed; }
```

- [ ] **Step 7: Add `nextTick` to imports if not already present**

Verify `nextTick` is in the Vue import at the top of `<script setup>`:

```js
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/BookCarView.vue
git commit -m "feat(frontend): add Stripe Card Element payment modal to booking flow"
```

---

## Task 4: End-to-End Validation

- [ ] **VAL-1 — Price renders on vehicle + hours selection**
  1. Select a vehicle. Set hours to 2.
  2. Expected: "Estimated Total — SGD 25.00" (sedan) or correct amount for vehicle type.

- [ ] **VAL-2 — Pay button is disabled until price loads**
  1. Immediately after selecting a vehicle, before price returns: button shows "Pay SGD — & Book" and is disabled.
  2. After price loads: button shows correct amount and is enabled.

- [ ] **VAL-3 — Payment modal opens with card element**
  1. Click "Pay SGD X.XX & Book".
  2. Expected: dark overlay + modal with card input field, amount summary, and test card hint.

- [ ] **VAL-4 — Invalid card shows inline error**
  1. Enter `4000 0000 0000 0002` (Stripe decline test card), any future expiry, any CVC.
  2. Click "Pay SGD X.XX".
  3. Expected: booking error shown inside the modal ("Your card was declined." or similar from Stripe).

- [ ] **VAL-5 — Successful payment creates booking**
  1. Enter `4242 4242 4242 4242`, expiry `12/34`, CVC `123`.
  2. Click "Pay SGD X.XX".
  3. Expected: modal closes, success message shows booking ID, vehicle disappears from the available list.

- [ ] **VAL-6 — Missing VITE_STRIPE_PUBLISHABLE_KEY degrades gracefully**
  1. Set `VITE_STRIPE_PUBLISHABLE_KEY` to empty string in `.env`.
  2. Try to open payment modal.
  3. Expected: Stripe.js fails to load and `bookingError` shows "Payment form not ready. Please try again."

---

## Self-Review Checklist

| # | Check | Status |
|---|-------|--------|
| 1 | `VITE_STRIPE_PUBLISHABLE_KEY` wired through Dockerfile → docker-compose → Vite → runtime | ✅ |
| 2 | `payment_method` passed to `/api/book-car` → composite passes to stripe_wrapper → stripe_wrapper uses it | ✅ |
| 3 | `closePaymentModal` unmounts Card Element — avoids Stripe "already mounted" error on reopen | ✅ |
| 4 | `nextTick()` called before `mountCardElement()` — ensures `#stripe-card-element` div is in DOM | ✅ |
| 5 | Existing booking guard still active — `openPaymentModal` checks before opening | ✅ |
| 6 | `checkExistingBooking()` called after successful booking — guard updates immediately | ✅ |
| 7 | No placeholder steps | ✅ |
| 8 | `estimatedPrice` cleared on successful booking so next vehicle selection starts fresh | ✅ |
