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
          v-if="!manualCancelResult && lookedUpBooking.status === 'confirmed'"
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
import { ref, onMounted } from 'vue'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

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
        if (fallbackErr?.response?.status === 404) {
          lastFallbackError = fallbackErr
          break
        }
        lastFallbackError = fallbackErr
      }
    }

    if (!res) {
      throw lastFallbackError || new Error('Unable to load active booking')
    }

    const booking = res.data?.data ?? res.data
    if (!booking) return
    activeBooking.value = booking
  } catch {
    // No active booking — that's fine, show manual lookup only
  }
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
.view-container { max-width: 720px; margin: 0 auto; }
h1 { margin-bottom: 24px; color: #1a1a2e; }
.booking-card { background: white; padding: 24px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); margin-bottom: 24px; }
.booking-card h3 { margin-bottom: 16px; color: #1a1a2e; }
.booking-card p { margin-bottom: 8px; }
.cancel-section { margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; }
.warning { font-size: 0.875rem; color: #888; margin-bottom: 16px; }
.manual-lookup { background: white; padding: 24px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.manual-lookup h3 { margin-bottom: 16px; color: #1a1a2e; }
.lookup-form { display: flex; gap: 12px; align-items: flex-end; margin-bottom: 20px; }
.form-group { flex: 1; }
.form-group label { display: block; margin-bottom: 6px; color: #555; font-size: 0.9rem; }
.form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem; }
.error-msg { color: #e94560; font-size: 0.875rem; margin-top: 8px; }
.success-msg { color: #2ecc71; font-size: 0.875rem; margin-top: 8px; }
.btn-primary { padding: 10px 20px; background: #1a1a2e; color: white; border: none; border-radius: 4px; cursor: pointer; white-space: nowrap; }
.btn-primary:disabled { background: #999; cursor: not-allowed; }
.btn-danger { padding: 10px 20px; background: #e94560; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-danger:disabled { background: #999; cursor: not-allowed; }
</style>
