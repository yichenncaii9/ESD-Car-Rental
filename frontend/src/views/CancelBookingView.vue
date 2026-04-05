<template>
  <div class="view-container">
    <h1>Cancel Booking</h1>

    <!-- Auto-fetched active booking -->
    <div v-if="activeBooking" class="booking-card">
      <h3>Your Active Booking</h3>
      <p><strong>Booking ID:</strong> {{ activeBooking.id }}</p>
      <p><strong>Vehicle:</strong> {{ activeBooking.vehicle_id }}</p>
      <p><strong>Pickup:</strong> {{ formatDate(activeBooking.pickup_datetime) }}</p>
      <p><strong>Status:</strong> {{ activeBooking.status }}</p>

      <div class="cancel-section">
        <p class="warning">Cancellation policy: Full refund if more than 24 hours before pickup, 50% refund within 24 hours, no refund within 1 hour.</p>
        <p v-if="cancelError" class="error-msg">{{ cancelError }}</p>
        <p v-if="cancelResult" class="success-msg">
          Cancelled. Refund: ${{ cancelResult.refund_amount }} ({{ cancelResult.refund_status }})
        </p>
        <button
          v-if="!cancelResult"
          @click="cancelBooking(activeBooking.id)"
          class="btn-danger"
          :disabled="cancelling"
        >
          {{ cancelling ? 'Cancelling...' : 'Cancel This Booking' }}
        </button>
      </div>
    </div>

    <!-- Manual booking ID lookup -->
    <div class="manual-lookup">
      <h3>{{ activeBooking ? 'Or look up another booking' : 'Look up a booking' }}</h3>
      <form @submit.prevent="lookupBooking" class="lookup-form">
        <div class="form-group">
          <label>Booking ID</label>
          <input v-model="manualBookingId" type="text" placeholder="e.g. b001" :disabled="looking" />
        </div>
        <button type="submit" class="btn-primary" :disabled="looking || !manualBookingId">
          {{ looking ? 'Looking up...' : 'Look Up' }}
        </button>
      </form>

      <div v-if="lookedUpBooking" class="booking-card">
        <h3>Booking Details</h3>
        <p><strong>Booking ID:</strong> {{ lookedUpBooking.id }}</p>
        <p><strong>Vehicle:</strong> {{ lookedUpBooking.vehicle_id }}</p>
        <p><strong>Pickup:</strong> {{ formatDate(lookedUpBooking.pickup_datetime) }}</p>
        <p><strong>Status:</strong> {{ lookedUpBooking.status }}</p>
        <p v-if="manualCancelError" class="error-msg">{{ manualCancelError }}</p>
        <p v-if="manualCancelResult" class="success-msg">
          Cancelled. Refund: ${{ manualCancelResult.refund_amount }} ({{ manualCancelResult.refund_status }})
        </p>
        <button
          v-if="!manualCancelResult && isBookingCancellable(lookedUpBooking)"
          @click="cancelBooking(lookedUpBooking.id, true)"
          class="btn-danger"
          :disabled="cancelling"
        >
          {{ cancelling ? 'Cancelling...' : 'Cancel This Booking' }}
        </button>
      </div>
      <p v-if="lookupError" class="error-msg">{{ lookupError }}</p>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

// Returns true if booking is confirmed and the rental window has not yet ended.
// This covers both upcoming bookings (before pickup) and in-progress rentals
// (past pickup but not yet past pickup + hours), ensuring mid-rental bookings
// are visible and cancellable — matching BookCarView's active booking guard.
function isBookingCancellable(booking) {
  if (!booking || booking.status !== 'confirmed') return false
  const end = new Date(booking.pickup_datetime).getTime() + (booking.hours || 0) * 3600 * 1000
  return Date.now() < end
}

const activeBooking    = ref(null)
const manualBookingId  = ref('')
const lookedUpBooking  = ref(null)
const cancelResult     = ref(null)
const manualCancelResult = ref(null)
const cancelError      = ref('')
const manualCancelError = ref('')
const lookupError      = ref('')
const cancelling       = ref(false)
const looking          = ref(false)

const envBookingBaseUrl = (import.meta.env.VITE_BOOKING_SERVICE_URL || '').trim()

function isBrowserReachableBaseUrl(baseUrl) {
  if (!baseUrl) return false
  try {
    const parsed = new URL(baseUrl)
    const host = parsed.hostname
    if (host === 'localhost' || host === '127.0.0.1') return true
    if (host.includes('_')) return false
    return host === window.location.hostname
  } catch {
    return false
  }
}

const directBookingBaseUrl = isBrowserReachableBaseUrl(envBookingBaseUrl)
  ? envBookingBaseUrl
  : 'http://localhost:5002'

const bookingApi = axios.create({
  baseURL: directBookingBaseUrl
})

const fallbackBookingBaseUrls = [
  directBookingBaseUrl,
  'http://localhost:5002',
  'http://127.0.0.1:5002'
].filter((url, index, list) => url && list.indexOf(url) === index)

function formatDate(dt) {
  if (!dt) return 'N/A'
  return new Date(dt).toLocaleString()
}

let validityTimer = null

onUnmounted(() => clearInterval(validityTimer))

onMounted(async () => {
  try {
    const uid = authStore.currentUser?.uid
    if (!uid) return
    let res
    let lastFallbackError = null

    for (const baseURL of fallbackBookingBaseUrls) {
      try {
        res = await bookingApi.get(`/api/bookings/user/${uid}/active`, { baseURL })
        break
      } catch (fallbackErr) {
        if (fallbackErr?.response?.status === 404) { lastFallbackError = fallbackErr; break }
        lastFallbackError = fallbackErr
      }
    }

    if (!res) throw lastFallbackError || new Error('Unable to load active booking')

    const booking = res.data?.data ?? res.data
    // Only display if booking is still cancellable (confirmed + before pickup)
    if (booking && isBookingCancellable(booking)) {
      activeBooking.value = booking
    }
  } catch {
    // No cancellable booking — show manual lookup only
  }

  // Reactively hide the booking card once it's no longer cancellable
  validityTimer = setInterval(() => {
    if (activeBooking.value && !isBookingCancellable(activeBooking.value)) {
      activeBooking.value = null
    }
  }, 5000)
})

async function lookupBooking() {
  looking.value = true
  lookupError.value = ''
  lookedUpBooking.value = null
  manualCancelResult.value = null
  try {
    const res = await api.get(`/api/bookings/${manualBookingId.value}`)
    lookedUpBooking.value = res.data.data || res.data
  } catch (err) {
    lookupError.value = err.response?.data?.message || err.response?.data?.error || 'Booking not found.'
  } finally {
    looking.value = false
  }
}

async function cancelBooking(bookingId, isManual = false) {
  cancelling.value = true
  if (isManual) manualCancelError.value = ''
  else cancelError.value = ''
  try {
    const res = await api.post('/api/cancel-booking', { booking_id: bookingId })
    if (isManual) manualCancelResult.value = res.data
    else cancelResult.value = res.data
  } catch (err) {
    const msg = err.response?.data?.message || err.response?.data?.error || 'Cancellation failed. Please try again.'
    if (isManual) manualCancelError.value = msg
    else cancelError.value = msg
  } finally {
    cancelling.value = false
  }
}
</script>

<style scoped>
.view-container { max-width: 720px; margin: 0 auto; padding-bottom: 48px; }

h1 {
  font-size: 26px; font-weight: 800; color: var(--c-dark);
  letter-spacing: -0.4px; margin-bottom: 6px;
}
/* policy strip above cards */
.view-container::before {
  content: '';
  display: block;
  height: 3px;
  width: 48px;
  background: var(--c-accent);
  border-radius: 9999px;
  margin-bottom: 20px;
}

.booking-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-left: 3px solid var(--c-accent);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
  margin-bottom: 20px;
}
.booking-card h3 {
  font-size: 11px; font-weight: 800; text-transform: uppercase;
  letter-spacing: 0.8px; color: var(--c-muted); margin-bottom: 16px;
}
.booking-card p {
  font-size: 14px; color: var(--c-dark); margin-bottom: 10px;
  display: flex; gap: 8px;
}
.booking-card p strong {
  min-width: 80px; color: var(--c-muted);
  font-weight: 600; font-size: 12px;
  text-transform: uppercase; letter-spacing: 0.3px;
  flex-shrink: 0; padding-top: 1px;
}

.cancel-section { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--c-border); }
.warning {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  margin-bottom: 16px;
  line-height: 1.6;
}
.warning::before {
  content: '⚠';
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 1px;
}

.manual-lookup {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
}
.manual-lookup h3 {
  font-size: 15px; font-weight: 700; color: var(--c-dark); margin-bottom: 16px;
  display: flex; align-items: center; gap: 8px;
}
.manual-lookup h3::before {
  content: '';
  width: 3px; height: 16px;
  background: var(--c-border);
  border-radius: 2px;
  display: inline-block;
}

.lookup-form { display: flex; gap: 12px; align-items: flex-end; margin-bottom: 20px; }
.lookup-form .form-group { flex: 1; margin-bottom: 0; }
</style>
