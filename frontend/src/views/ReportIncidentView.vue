<template>
  <div class="view-container">
    <h1>Report an Incident</h1>

    <p class="page-subtitle" style="color:var(--c-muted);font-size:13px;margin-bottom:28px;">Provide your location and a description. Severity is assessed automatically by AI.</p>

    <!-- Location section -->
    <div class="section-step"><span class="step-num">1</span><span class="step-title">Incident Location</span></div>
    <div class="location-section">
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
    <div class="section-step" style="margin-top:4px"><span class="step-num">2</span><span class="step-title">Incident Details</span></div>
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

    <!-- ⚠️ TEMP DEBUG PANEL — gitignored, never committed -->
    <DebugReportPanel ref="panel" />
  </div>
</template>

<script setup>
import axios from 'axios'
import { ref, onMounted, defineAsyncComponent } from 'vue'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const DebugReportPanel = defineAsyncComponent(() =>
  import(/* @vite-ignore */ '../components/Debug' + 'ReportPanel.vue').catch(() => ({ render: () => null }))
)
const panel = ref(null)

const authStore = useAuthStore()

// Default to central Singapore; overridden by geolocation on mount
const incidentLocation = ref({ lat: 1.3521, lng: 103.8198 })
const vehicleId   = ref('')
const bookingId   = ref('')
const description = ref('')
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

const submitting  = ref(false)
const submitError = ref('')
const submitResult = ref(null)

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
  const uid = authStore.currentUser?.uid
  const payload = {
    user_uid:    uid,
    booking_id:  bookingId.value,
    vehicle_id:  vehicleId.value,
    description: description.value,
    lat:         incidentLocation.value.lat,
    lng:         incidentLocation.value.lng,
    ...(imageBase64.value ? { image_base64: imageBase64.value } : {}),
  }
  panel.value?.logSubmit(payload, null)
  try {
    const res = await api.post('/api/report-issue', payload)
    submitResult.value = res.data
    panel.value?.logSubmit(payload, { ok: true, status: res.status, data: res.data })
    await panel.value?.fetchRecentReports()
  } catch (err) {
    const errData = err.response?.data || { message: err.message }
    submitError.value = errData.message || errData.error || 'Report submission failed. Please try again.'
    panel.value?.logSubmit(payload, { ok: false, status: err.response?.status, data: errData })
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.view-container { max-width: 800px; margin: 0 auto; padding-bottom: 48px; }

h1 { font-size: 26px; font-weight: 800; color: var(--c-dark); letter-spacing: -0.4px; margin-bottom: 4px; }

/* step label shared style */
.section-step {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.step-num {
  width: 24px; height: 24px;
  background: var(--c-accent);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 800; color: #fff;
  flex-shrink: 0;
}
.step-title {
  font-size: 12px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.7px;
  color: var(--c-muted);
}

.location-section {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
  margin-bottom: 20px;
}
.map-hint { color: var(--c-muted); font-size: 13px; margin-bottom: 12px; line-height: 1.5; }

.places-input {
  width: 100%;
  padding: 11px 14px;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: var(--font);
  outline: none;
  color: var(--c-dark);
  background: var(--c-bg);
  transition: border-color 0.15s, background 0.15s;
  margin-bottom: 4px;
}
.places-input:focus { border-color: var(--c-accent); background: var(--c-surface); }

.coords-display {
  margin-top: 8px;
  font-size: 11px;
  color: var(--c-muted);
  font-family: 'Courier New', monospace;
  background: var(--c-bg);
  padding: 6px 10px;
  border-radius: 6px;
  display: inline-block;
}

.report-form {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
}

.result-card {
  background: var(--c-success-bg);
  border: 1px solid #86efac;
  border-left: 3px solid var(--c-success);
  border-radius: var(--radius-sm);
  padding: 16px 20px;
  margin-bottom: 16px;
}
.result-card p { font-size: 14px; color: var(--c-dark); margin-bottom: 6px; }
.result-card p:last-child { margin-bottom: 0; }

.btn-primary { width: 100%; padding: 13px; justify-content: center; font-size: 15px; }

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
</style>
