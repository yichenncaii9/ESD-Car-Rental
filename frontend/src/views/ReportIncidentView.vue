<template>
  <div class="view-container">
    <h1>Report an Incident</h1>

    <!-- Location section -->
    <div class="location-section">
      <h3>Incident Location</h3>
      <p class="map-hint">Your location is auto-detected. Search or drag the pin to adjust.</p>

      <!-- Places Autocomplete — componentRestrictions limits to Singapore -->
      <GMapAutocomplete
        class="places-input"
        placeholder="Search Singapore location..."
        :options="{ componentRestrictions: { country: 'sg' } }"
        @place_changed="onPlaceChanged"
      />

      <GMapMap
        :center="incidentLocation"
        :zoom="14"
        style="width: 100%; height: 380px; border-radius: 8px; margin-top: 12px;"
      >
        <GMapMarker
          :position="incidentLocation"
          :draggable="true"
          @dragend="onMarkerDrag"
        />
      </GMapMap>

      <p class="coords-display">
        Selected: {{ incidentLocation.lat.toFixed(5) }}, {{ incidentLocation.lng.toFixed(5) }}
      </p>
    </div>

    <!-- Report form -->
    <form @submit.prevent="submitReport" class="report-form">
      <div class="form-group">
        <label>Booking ID</label>
        <input
          v-model="bookingId"
          type="text"
          placeholder="Auto-filled from your active booking"
          required
          :disabled="submitting"
        />
      </div>
      <div class="form-group">
        <label>Vehicle ID</label>
        <input
          v-model="vehicleId"
          type="text"
          placeholder="Auto-filled from your active booking"
          required
          :disabled="submitting"
        />
      </div>
      <div class="form-group">
        <label>Incident Description</label>
        <textarea
          v-model="description"
          rows="4"
          placeholder="Describe what happened..."
          required
          :disabled="submitting"
        />
      </div>

      <p v-if="submitError" class="error-msg">{{ submitError }}</p>

      <div v-if="submitResult" class="result-card">
        <p class="success-msg">Report submitted successfully!</p>
        <p><strong>Report ID:</strong> {{ submitResult.report_id }}</p>
        <p><strong>Severity:</strong> {{ submitResult.severity }}</p>
        <p><strong>Status:</strong> {{ submitResult.status }}</p>
      </div>

      <button type="submit" class="btn-primary" :disabled="submitting || !!submitResult">
        {{ submitting ? 'Submitting...' : 'Submit Report' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

// Default to central Singapore; overridden by geolocation on mount
const incidentLocation = ref({ lat: 1.3521, lng: 103.8198 })
const vehicleId   = ref('')
const bookingId   = ref('')
const description = ref('')
const submitting  = ref(false)
const submitError = ref('')
const submitResult = ref(null)

onMounted(async () => {
  // Auto-detect user location via browser Geolocation API
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        incidentLocation.value = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude
        }
      },
      (err) => {
        console.warn('Geolocation denied or unavailable:', err.message)
      }
    )
  }
  // Auto-fill booking_id and vehicle_id from active booking
  try {
    const uid = authStore.currentUser?.uid
    if (!uid) return
    const res = await api.get(`/api/bookings/user/${uid}/active`)
    const booking = res.data.data || res.data
    if (booking?.id) bookingId.value = booking.id
    if (booking?.vehicle_id) vehicleId.value = booking.vehicle_id
  } catch {
    // No active booking — user can fill in manually
  }
})

function onPlaceChanged(place) {
  if (place && place.geometry && place.geometry.location) {
    incidentLocation.value = {
      lat: place.geometry.location.lat(),
      lng: place.geometry.location.lng()
    }
  }
}

function onMarkerDrag(event) {
  incidentLocation.value = {
    lat: event.latLng.lat(),
    lng: event.latLng.lng()
  }
}

async function submitReport() {
  submitting.value = true
  submitError.value = ''
  submitResult.value = null
  try {
    const uid = authStore.currentUser?.uid
    const res = await api.post('/api/report-issue', {
      user_uid:    uid,
      booking_id:  bookingId.value,
      vehicle_id:  vehicleId.value,
      description: description.value,
      lat:         incidentLocation.value.lat,
      lng:         incidentLocation.value.lng
    })
    submitResult.value = res.data
  } catch (err) {
    submitError.value = err.response?.data?.message || err.response?.data?.error || 'Report submission failed. Please try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.view-container { max-width: 800px; margin: 0 auto; }
h1 { margin-bottom: 24px; color: #1a1a2e; }
.location-section { background: white; padding: 24px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); margin-bottom: 24px; }
.location-section h3 { margin-bottom: 8px; color: #1a1a2e; }
.map-hint { color: #666; font-size: 0.9rem; margin-bottom: 12px; }
.places-input {
  width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 4px;
  font-size: 1rem; outline: none;
}
.places-input:focus { border-color: #16213e; }
.coords-display { margin-top: 8px; font-size: 0.85rem; color: #888; }
.report-form { background: white; padding: 24px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; color: #555; font-size: 0.9rem; }
.form-group input, .form-group textarea {
  width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem;
  font-family: inherit; resize: vertical;
}
.error-msg { color: #e94560; font-size: 0.875rem; margin-bottom: 12px; }
.success-msg { color: #2ecc71; font-size: 0.875rem; margin-bottom: 8px; }
.result-card { background: #f0fff4; border: 1px solid #2ecc71; padding: 16px; border-radius: 6px; margin-bottom: 16px; }
.result-card p { margin-bottom: 4px; }
.btn-primary { width: 100%; padding: 12px; background: #1a1a2e; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
.btn-primary:disabled { background: #999; cursor: not-allowed; }
</style>
