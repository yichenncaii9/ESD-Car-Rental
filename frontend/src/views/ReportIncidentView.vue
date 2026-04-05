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

    <!-- No active booking state -->
    <div v-if="!bookingLoading && !activeBooking" class="empty-state">
      <p class="empty-icon">🚗</p>
      <p class="empty-title">No active booking found</p>
      <p class="empty-body">You can only report an incident during an active rental. Please make a booking first.</p>
      <button type="button" class="btn-primary empty-cta" @click="router.push('/book-car')">Book a Car</button>
    </div>

    <!-- Report form — only shown when there's a current active booking -->
    <div v-if="activeBooking">
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

        <div class="photo-actions">
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
          <button type="button" class="camera-btn" :disabled="submitting" @click="openCamera">
            Take Photo
          </button>
        </div>
        <p v-if="cameraError" class="error-msg" style="margin-top:8px;margin-bottom:0">{{ cameraError }}</p>

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

    <!-- Camera modal -->
    <div v-if="cameraOpen" class="camera-overlay" @click.self="closeCamera">
      <div class="camera-modal">
        <video ref="videoRef" class="camera-preview" autoplay playsinline muted />
        <div class="camera-controls">
          <button type="button" class="btn-primary camera-capture-btn" @click="capturePhoto">Capture</button>
          <button type="button" class="camera-cancel-btn" @click="closeCamera">Cancel</button>
        </div>
      </div>
    </div>
    </div><!-- end v-if="activeBooking" -->
  </div>
</template>

<script setup>
import axios from 'axios'
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const router = useRouter()

// Active booking — null means no valid booking in current time window
const activeBooking  = ref(null)
const bookingLoading = ref(true)

// Returns true only if now falls within [pickup, pickup + hours]
function isBookingCurrentlyActive(booking) {
  if (!booking || booking.status !== 'confirmed') return false
  const now    = Date.now()
  const pickup = new Date(booking.pickup_datetime).getTime()
  const end    = pickup + (booking.hours || 0) * 3600 * 1000
  return now >= pickup && now <= end
}

// Default to central Singapore; overridden by geolocation on mount
const incidentLocation = ref({ lat: 1.3521, lng: 103.8198 })
const vehicleId   = ref('')
const bookingId   = ref('')
const description = ref('')
const imageBase64 = ref('')        // empty string = no image attached
const imagePreviewUrl = ref('')    // blob URL (file upload) or data URL (camera capture)

// Camera
const cameraOpen  = ref(false)
const cameraError = ref('')
const videoRef    = ref(null)
const cameraStream = ref(null)   // MediaStream — must be stopped on close/unmount

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
  // Only revoke blob URLs; data URLs (camera captures) have no object to revoke
  if (imagePreviewUrl.value?.startsWith('blob:')) URL.revokeObjectURL(imagePreviewUrl.value)
  imagePreviewUrl.value = ''
}

async function openCamera() {
  cameraError.value = ''
  try {
    cameraStream.value = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    })
    cameraOpen.value = true
    // Attach stream to video element after Vue renders the modal
    await nextTick()
    if (videoRef.value) videoRef.value.srcObject = cameraStream.value
  } catch (err) {
    cameraError.value = err.name === 'NotAllowedError'
      ? 'Camera access denied. Allow camera permission and try again.'
      : `Camera unavailable: ${err.message}`
  }
}

function capturePhoto() {
  const video = videoRef.value
  if (!video) return
  const canvas = document.createElement('canvas')
  canvas.width  = video.videoWidth  || 1280
  canvas.height = video.videoHeight || 720
  canvas.getContext('2d').drawImage(video, 0, 0)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.85)
  imageBase64.value = dataUrl.split(',')[1] ?? ''
  // Revoke old blob URL if present, then use dataURL directly as preview
  if (imagePreviewUrl.value?.startsWith('blob:')) URL.revokeObjectURL(imagePreviewUrl.value)
  imagePreviewUrl.value = dataUrl
  closeCamera()
}

function closeCamera() {
  cameraOpen.value = false
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(t => t.stop())
    cameraStream.value = null
  }
}

let validityTimer = null

onUnmounted(() => {
  if (cameraStream.value) cameraStream.value.getTracks().forEach(t => t.stop())
  if (imagePreviewUrl.value?.startsWith('blob:')) URL.revokeObjectURL(imagePreviewUrl.value)
  clearInterval(validityTimer)
})

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

function clearActiveBooking() {
  activeBooking.value = null
  bookingId.value = ''
  vehicleId.value = ''
}

onMounted(async () => {
  // Auto-detect user location via browser Geolocation API
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => { incidentLocation.value = { lat: pos.coords.latitude, lng: pos.coords.longitude } },
      (err) => { console.warn('Geolocation denied or unavailable:', err.message) }
    )
  }

  // Fetch booking and validate against current time window
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
    if (booking && isBookingCurrentlyActive(booking)) {
      activeBooking.value = booking
      bookingId.value  = booking.id        || ''
      vehicleId.value  = booking.vehicle_id || ''
    }
  } catch {
    // No active booking — show empty state
  } finally {
    bookingLoading.value = false
  }

  // Reactively expire the booking when its time window ends (check every 5 seconds)
  validityTimer = setInterval(() => {
    if (activeBooking.value && !isBookingCurrentlyActive(activeBooking.value)) {
      clearActiveBooking()
    }
  }, 5000)
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
  // Re-validate booking window at submit time — guards against expired bookings
  if (!activeBooking.value || !isBookingCurrentlyActive(activeBooking.value)) {
    clearActiveBooking()
    return
  }
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
  try {
    const res = await api.post('/api/report-issue', payload)
    submitResult.value = res.data
  } catch (err) {
    const errData = err.response?.data || { message: err.message }
    submitError.value = errData.message || errData.error || 'Report submission failed. Please try again.'
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

.empty-state {
  text-align: center;
  padding: 56px 24px;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}
.empty-icon { font-size: 40px; margin-bottom: 12px; }
.empty-title { font-size: 18px; font-weight: 700; color: var(--c-dark); margin-bottom: 8px; }
.empty-body  { font-size: 14px; color: var(--c-muted); margin-bottom: 24px; line-height: 1.6; }
.empty-cta   { width: auto; padding: 11px 32px; display: inline-flex; }

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

.photo-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.camera-btn {
  padding: 9px 18px;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--c-dark);
  background: var(--c-bg);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.camera-btn:hover:not(:disabled) { border-color: var(--c-accent); background: var(--c-surface); }
.camera-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Camera modal overlay */
.camera-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-modal {
  background: #000;
  border-radius: var(--radius);
  overflow: hidden;
  max-width: 640px;
  width: 100%;
  margin: 16px;
}

.camera-preview {
  width: 100%;
  display: block;
  max-height: 60vh;
  object-fit: cover;
  background: #111;
}

.camera-controls {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  background: #111;
  justify-content: center;
}

.camera-capture-btn {
  width: auto;
  padding: 11px 32px;
  font-size: 14px;
}

.camera-cancel-btn {
  padding: 11px 24px;
  border: 1.5px solid #444;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  color: #aaa;
  background: transparent;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.camera-cancel-btn:hover { border-color: #888; color: #fff; }
</style>
