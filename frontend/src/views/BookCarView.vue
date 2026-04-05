<template>
  <div class="bookcar-page">

    <!-- ── PAGE HEADER ──────────────────────────────────────── -->
    <div class="bookcar-header">
      <div class="bookcar-header__inner view-container">
        <div>
          <h1>Book a Car</h1>
          <p class="bookcar-header__sub">Click a map marker to browse vehicles at that location, then confirm your booking below.</p>
        </div>
        <div class="bookcar-header__stats" aria-hidden="true">
          <div class="header-stat">
            <span class="header-stat-val">{{ availableVehicles.length }}</span>
            <span class="header-stat-label">Available</span>
          </div>
          <div class="header-stat-divider"></div>
          <div class="header-stat">
            <span class="header-stat-val">3</span>
            <span class="header-stat-label">Locations</span>
          </div>
        </div>
      </div>
    </div>

  <div class="view-container bookcar-body">
    <div class="map-section">
      <p class="map-hint" style="display:none">Click a marker to choose from vehicles at the same location</p>
      <GMapMap
        ref="mapRef"
        :center="mapCenter"
        :zoom="12"
        style="width: 100%; height: 480px; border-radius: 8px;"
      />
    </div>

    <!-- Existing booking banner — hidden immediately after a successful booking -->
    <div v-if="!bookingCheckLoading && existingBooking && !bookingJustSucceeded" class="existing-booking-banner">
      <div class="existing-booking-banner__body">
        <strong>You already have an active booking</strong>
        <span>Booking <code>{{ existingBooking.id }}</code> is still active or upcoming. Cancel it before making a new one.</span>
      </div>
      <router-link to="/cancel-booking" class="btn-primary existing-booking-banner__cta">Cancel Booking</router-link>
    </div>

    <div class="booking-panel">
      <div v-if="selectedVehicle" class="selected-vehicle">
        <h3>Selected Vehicle</h3>
        <p><strong>Type:</strong> {{ selectedVehicle.vehicle_type }}</p>
        <p><strong>Plate:</strong> {{ selectedVehicle.plate_number }}</p>
        <p><strong>Status:</strong> {{ selectedVehicle.status }}</p>
      </div>
      <div v-else class="no-selection">
        <p>No vehicle selected. Click a marker on the map.</p>
      </div>

      <form v-if="selectedVehicle" class="booking-form" :inert="!!existingBooking">
        <div class="form-group">
          <label>Pickup Date & Time</label>
          <input v-model="pickupDatetime" type="datetime-local" required :disabled="submitting" />
        </div>
        <div class="form-group">
          <label>Duration (hours)</label>
          <input v-model.number="hours" type="number" min="1" max="72" required :disabled="submitting" />
        </div>
        <div v-if="estimatedPrice !== null" class="price-preview">
          <span class="price-label">Estimated Total</span>
          <span class="price-amount">SGD {{ estimatedPrice.toFixed(2) }}</span>
        </div>
        <p v-else-if="priceLoading" class="price-loading">Calculating price…</p>
        <p v-if="bookingError" class="error-msg">{{ bookingError }}</p>
        <p v-if="bookingSuccess" class="success-msg">{{ bookingSuccess }}</p>
        <button type="button" class="btn-primary" :disabled="submitting || !estimatedPrice || bookingCheckLoading" @click="openPaymentModal">
          {{ submitting ? 'Booking...' : bookingCheckLoading ? 'Checking availability…' : `Pay SGD ${estimatedPrice ? estimatedPrice.toFixed(2) : '—'} & Book` }}
        </button>
      </form>
    </div>

    <div class="vehicle-list">
      <h3>Available Vehicles <span class="count" v-if="availableVehicles.length">({{ availableVehicles.length }})</span></h3>
      <p v-if="loading" class="empty-state">Loading...</p>
      <p v-else-if="vehicleLoadError" class="error-msg empty-state">{{ vehicleLoadError }}</p>
      <p v-else-if="!availableVehicles.length" class="empty-state">No vehicles available.</p>
      <div v-else class="vehicle-cards">
        <div
          v-for="vehicle in availableVehicles"
          :key="vehicle.id"
          class="vehicle-card"
          :class="{ selected: selectedVehicle?.id === vehicle.id }"
          @click="selectVehicle(vehicle)"
        >
          <div class="vehicle-card-top">
            <span class="vehicle-type">{{ vehicle.vehicle_type }}</span>
            <span class="vehicle-status" :class="vehicle.status">{{ vehicle.status }}</span>
          </div>
          <div class="vehicle-plate">{{ vehicle.plate_number }}</div>
          <div class="vehicle-meta">{{ [vehicle.make, vehicle.model, vehicle.year].filter(Boolean).join(' · ') }}</div>
        </div>
      </div>
    </div>
  </div>
  </div>

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
        <div class="dummy-card-fields">
          <div class="dummy-field-group">
            <label class="dummy-field-label">Card Number</label>
            <input class="dummy-field-input" type="text" value="4242 4242 4242 4242" readonly />
          </div>
          <div class="dummy-field-row">
            <div class="dummy-field-group">
              <label class="dummy-field-label">Expiry</label>
              <input class="dummy-field-input" type="text" value="12/34" readonly />
            </div>
            <div class="dummy-field-group">
              <label class="dummy-field-label">CVC</label>
              <input class="dummy-field-input" type="text" value="123" readonly />
            </div>
          </div>
        </div>
      </div>

      <div class="payment-modal__footer">
        <button type="button" class="btn-primary payment-confirm-btn"
          :disabled="submitting"
          @click="submitBooking">
          {{ submitting ? 'Processing…' : `Pay SGD ${estimatedPrice?.toFixed(2)}` }}
        </button>
        <button type="button" class="payment-cancel-btn" :disabled="submitting" @click="closePaymentModal">
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const paymentModalOpen = ref(false)

const authStore = useAuthStore()

// Existing booking guard — true if user already has a confirmed booking not yet expired
const existingBooking    = ref(null)
const bookingCheckLoading = ref(true)
// Suppress the "cancel before booking" banner immediately after a successful booking.
// existingBooking is still set (so openPaymentModal blocks double-booking), but we
// don't want to show the scary red banner right after the user just confirmed a booking.
const bookingJustSucceeded = ref(false)

// Returns true if the booking is confirmed AND its end time (pickup + hours) is in the future.
// Covers both currently-active and upcoming bookings.
function isBookingActiveOrUpcoming(booking) {
  if (!booking || booking.status !== 'confirmed') return false
  const end = new Date(booking.pickup_datetime).getTime() + (booking.hours || 0) * 3600 * 1000
  return Date.now() < end
}

const envBookingBaseUrl = (import.meta.env.VITE_BOOKING_SERVICE_URL || '').trim()
const directBookingBaseUrl = (() => {
  if (!envBookingBaseUrl) return 'http://localhost:5002'
  try {
    const host = new URL(envBookingBaseUrl).hostname
    if (host === 'localhost' || host === '127.0.0.1' || !host.includes('_')) return envBookingBaseUrl
  } catch {}
  return 'http://localhost:5002'
})()
const bookingApi = axios.create({ baseURL: directBookingBaseUrl })
const fallbackBookingBaseUrls = [directBookingBaseUrl, 'http://localhost:5002', 'http://127.0.0.1:5002']
  .filter((url, i, arr) => url && arr.indexOf(url) === i)

let bookingValidityTimer = null

const mapRef = ref(null)
const mapObject = ref(null)
const markerOverlays = ref([])
const popupOverlay = ref(null)
const mapClickListener = ref(null)
const selectedLocationKey = ref('')
const mapCenter = ref({ lat: 1.3521, lng: 103.8198 })
const vehicles = ref([])
const selectedVehicle = ref(null)
const loading = ref(false)
const vehicleLoadError = ref('')
const pickupDatetime = ref('')
const hours = ref(2)
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

function openPaymentModal() {
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
}

function closePaymentModal() {
  paymentModalOpen.value = false
}

const submitting = ref(false)
const bookingError = ref('')
const bookingSuccess = ref('')

const availableVehicles = computed(() =>
  vehicles.value.filter((vehicle) =>
    String(vehicle?.status || '').trim().toLowerCase() === 'available'
  )
)

const locationGroups = computed(() => {
  const groups = new Map()

  availableVehicles.value.forEach((vehicle) => {
    const position = getVehiclePosition(vehicle)
    const key = `${position.lat.toFixed(5)},${position.lng.toFixed(5)}`

    if (!groups.has(key)) {
      groups.set(key, {
        key,
        position,
        vehicles: [],
      })
    }

    groups.get(key).vehicles.push(vehicle)
  })

  return Array.from(groups.values())
})

const envVehicleBaseUrl = (import.meta.env.VITE_VEHICLE_SERVICE_URL || '').trim()

const carMarkerSvg = `
  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48" fill="none">
    <path d="M24 2C15.163 2 8 9.163 8 18c0 12.271 14.252 25.481 14.859 26.037a1.68 1.68 0 0 0 2.282 0C25.748 43.481 40 30.271 40 18 40 9.163 32.837 2 24 2Z" fill="#102542"/>
    <path d="M15.225 20.39a2 2 0 0 1 1.888-1.346h13.774a2 2 0 0 1 1.888 1.346l1.975 5.925a2 2 0 0 1 .102.632V31a2 2 0 0 1-2 2h-.9a1 1 0 0 1-1-1v-.8H17.048v.8a1 1 0 0 1-1 1h-.9a2 2 0 0 1-2-2v-4.053c0-.216.035-.43.102-.632l1.975-5.925Z" fill="#fff"/>
    <path d="M18.106 18.2 19.64 14h8.72l1.533 4.2H18.107Z" fill="#7FC8F8"/>
    <circle cx="18.8" cy="27.2" r="2.3" fill="#102542"/>
    <circle cx="29.2" cy="27.2" r="2.3" fill="#102542"/>
    <path d="M21 11.2c0-.663.537-1.2 1.2-1.2h3.6c.663 0 1.2.537 1.2 1.2V14H21v-2.8Z" fill="#102542"/>
  </svg>
`.trim()

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

const directVehicleBaseUrl = isBrowserReachableBaseUrl(envVehicleBaseUrl)
  ? envVehicleBaseUrl
  : 'http://localhost:5001'

const vehicleApi = axios.create({
  baseURL: directVehicleBaseUrl
})

const fallbackVehicleBaseUrls = [
  directVehicleBaseUrl,
  'http://localhost:5001',
  'http://127.0.0.1:5001'
].filter((url, index, list) => url && list.indexOf(url) === index)

function getVehiclePosition(vehicle) {
  return {
    lat: Number(vehicle.location_lat) || 1.3521,
    lng: Number(vehicle.location_lng) || 103.8198
  }
}

function selectVehicle(vehicle) {
  selectedVehicle.value = vehicle
  bookingError.value = ''
  bookingSuccess.value = ''

  const group = locationGroups.value.find((entry) =>
    entry.vehicles.some((candidate) => candidate.id === vehicle.id)
  )

  if (group) {
    openLocationPopup(group)
  }
}

function normalizeVehicles(payload) {
  if (Array.isArray(payload)) return payload

  const rawVehicles =
    payload?.data?.vehicles ||
    payload?.data ||
    payload?.vehicles ||
    payload?.results ||
    []

  return Array.isArray(rawVehicles) ? rawVehicles : []
}

function createCarMarkerClass() {
  if (!window.google?.maps || window.CarMarkerOverlay) return window.CarMarkerOverlay

  class CarMarkerOverlay extends window.google.maps.OverlayView {
    constructor({ map, position, title, onClick, isSelected }) {
      super()
      this.position = position
      this.title = title
      this.onClick = onClick
      this.isSelected = isSelected
      this.element = null
      this.setMap(map)
    }

    onAdd() {
      const element = document.createElement('button')
      element.type = 'button'
      element.className = 'car-map-marker'
      if (this.isSelected) element.classList.add('is-active')
      element.setAttribute('aria-label', this.title)
      element.innerHTML = carMarkerSvg
      element.addEventListener('click', (event) => {
        event.preventDefault()
        event.stopPropagation()
        this.onClick?.()
      })
      this.element = element

      this.getPanes()?.overlayMouseTarget?.appendChild(element)
    }

    draw() {
      if (!this.element) return
      const projection = this.getProjection()
      if (!projection) return

      const point = projection.fromLatLngToDivPixel(new window.google.maps.LatLng(this.position))
      if (!point) return

      this.element.style.left = `${point.x}px`
      this.element.style.top = `${point.y}px`
    }

    onRemove() {
      if (this.element) {
        this.element.remove()
        this.element = null
      }
    }

    setSelected(isSelected) {
      this.isSelected = isSelected
      if (this.element) {
        this.element.classList.toggle('is-active', isSelected)
      }
    }
  }

  window.CarMarkerOverlay = CarMarkerOverlay
  return CarMarkerOverlay
}

function createLocationPopupClass() {
  if (!window.google?.maps || window.LocationPopupOverlay) return window.LocationPopupOverlay

  class LocationPopupOverlay extends window.google.maps.OverlayView {
    constructor({ map, group }) {
      super()
      this.group = group
      this.element = null
      this.setMap(map)
    }

    onAdd() {
      const container = document.createElement('div')
      container.className = 'map-location-panel'
      container.addEventListener('click', (event) => {
        event.stopPropagation()
      })
      container.addEventListener('wheel', (event) => {
        event.stopPropagation()
      })
      container.addEventListener('touchmove', (event) => {
        event.stopPropagation()
      })

      const closeButton = document.createElement('button')
      closeButton.type = 'button'
      closeButton.className = 'map-location-panel__close'
      closeButton.textContent = '×'
      closeButton.addEventListener('click', (event) => {
        event.preventDefault()
        event.stopPropagation()
        closeLocationPopup()
      })

      const header = document.createElement('div')
      header.className = 'map-location-panel__header'
      header.textContent = `${this.group.vehicles.length} vehicle${this.group.vehicles.length === 1 ? '' : 's'} here`

      const list = document.createElement('div')
      list.className = 'map-location-panel__list'
      list.addEventListener('wheel', (event) => {
        event.stopPropagation()
      })
      list.addEventListener('touchmove', (event) => {
        event.stopPropagation()
      })

      this.group.vehicles.forEach((vehicle) => {
        const button = document.createElement('button')
        button.type = 'button'
        button.className = 'map-location-panel__item'
        if (selectedVehicle.value?.id === vehicle.id) {
          button.classList.add('is-selected')
        }

        const title = document.createElement('div')
        title.className = 'map-location-panel__title'
        title.textContent = `${vehicle.vehicle_type} · ${vehicle.plate_number}`

        const meta = document.createElement('div')
        meta.className = 'map-location-panel__meta'
        meta.textContent = [vehicle.make, vehicle.model, vehicle.year].filter(Boolean).join(' · ')

        button.appendChild(title)
        button.appendChild(meta)
        button.addEventListener('click', (event) => {
          event.preventDefault()
          event.stopPropagation()
          selectVehicle(vehicle)
        })

        list.appendChild(button)
      })

      container.appendChild(closeButton)
      container.appendChild(header)
      container.appendChild(list)
      this.element = container

      this.getPanes()?.floatPane?.appendChild(container)
    }

    draw() {
      if (!this.element) return
      const projection = this.getProjection()
      if (!projection) return

      const point = projection.fromLatLngToDivPixel(new window.google.maps.LatLng(this.group.position))
      if (!point) return

      this.element.style.left = `${point.x + 34}px`
      this.element.style.top = `${point.y - 28}px`
    }

    onRemove() {
      if (this.element) {
        this.element.remove()
        this.element = null
      }
    }
  }

  window.LocationPopupOverlay = LocationPopupOverlay
  return LocationPopupOverlay
}

function clearMarkerOverlays() {
  markerOverlays.value.forEach((overlay) => overlay.setMap(null))
  markerOverlays.value = []
}

function syncMarkerSelectionState() {
  markerOverlays.value.forEach((overlay) => {
    overlay.setSelected(overlay.locationKey === selectedLocationKey.value)
  })
}

function closeLocationPopup() {
  selectedLocationKey.value = ''
  if (popupOverlay.value) {
    popupOverlay.value.setMap(null)
    popupOverlay.value = null
  }
  syncMarkerSelectionState()
}

function openLocationPopup(group) {
  if (!mapObject.value || !window.google?.maps) return

  selectedLocationKey.value = group.key

  if (popupOverlay.value) {
    popupOverlay.value.setMap(null)
    popupOverlay.value = null
  }

  const LocationPopupOverlay = createLocationPopupClass()
  popupOverlay.value = new LocationPopupOverlay({
    map: mapObject.value,
    group,
  })

  syncMarkerSelectionState()
}

function renderLocationMarkers() {
  if (!mapObject.value || !window.google?.maps) return

  clearMarkerOverlays()
  const CarMarkerOverlay = createCarMarkerClass()

  markerOverlays.value = locationGroups.value.map((group) => {
    const overlay = new CarMarkerOverlay({
      map: mapObject.value,
      position: group.position,
      title: `${group.vehicles.length} vehicle${group.vehicles.length === 1 ? '' : 's'} available`,
      isSelected: selectedLocationKey.value === group.key,
      onClick: () => openLocationPopup(group),
    })

    overlay.locationKey = group.key
    return overlay
  })
}

async function loadVehicles() {
  loading.value = true
  vehicleLoadError.value = ''
  try {
    let res
    let lastFallbackError = null

    try {
      res = await api.get('/api/vehicles')
    } catch (err) {
      for (const baseURL of fallbackVehicleBaseUrls) {
        try {
          res = await vehicleApi.get('/api/vehicles', { baseURL })
          break
        } catch (fallbackErr) {
          lastFallbackError = fallbackErr
        }
      }

      if (!res) {
        throw lastFallbackError || err
      }
    }

    vehicles.value = normalizeVehicles(res.data)
    if (selectedVehicle.value) {
      selectedVehicle.value =
        vehicles.value.find((vehicle) => vehicle.id === selectedVehicle.value.id) || null
    }

    if (selectedLocationKey.value) {
      const activeGroup = locationGroups.value.find((group) => group.key === selectedLocationKey.value)
      if (activeGroup) {
        openLocationPopup(activeGroup)
      } else {
        closeLocationPopup()
      }
    }
  } catch (err) {
    console.error('Failed to load vehicles:', err.message)
    vehicles.value = []
    vehicleLoadError.value =
      err.response?.data?.message || 'Unable to load vehicles right now.'
  } finally {
    loading.value = false
  }
}

watch(locationGroups, () => {
  renderLocationMarkers()
}, { deep: true })

watch(selectedVehicle, () => {
  if (!selectedLocationKey.value) return
  const activeGroup = locationGroups.value.find((group) => group.key === selectedLocationKey.value)
  if (activeGroup) {
    openLocationPopup(activeGroup)
  }
})

watch([selectedVehicle, hours], () => {
  fetchPrice()
}, { immediate: false })

async function checkExistingBooking() {
  const uid = authStore.currentUser?.uid
  if (!uid) { bookingCheckLoading.value = false; return }
  try {
    let res
    for (const baseURL of fallbackBookingBaseUrls) {
      try {
        res = await bookingApi.get(`/api/bookings/user/${uid}/active`, { baseURL })
        break
      } catch (err) {
        if (err?.response?.status === 404) break
      }
    }
    const booking = res?.data?.data ?? res?.data
    existingBooking.value = (booking && isBookingActiveOrUpcoming(booking)) ? booking : null
  } catch {
    existingBooking.value = null
  } finally {
    bookingCheckLoading.value = false
  }
}

onMounted(async () => {
  await checkExistingBooking()

  // Reactively unlock the form once the existing booking expires
  bookingValidityTimer = setInterval(() => {
    if (existingBooking.value && !isBookingActiveOrUpcoming(existingBooking.value)) {
      existingBooking.value = null
    }
  }, 10000)

  mapObject.value = await mapRef.value?.$mapPromise

  if (mapObject.value && window.google?.maps) {
    mapClickListener.value = mapObject.value.addListener('click', () => {
      closeLocationPopup()
    })
  }

  await loadVehicles()
  renderLocationMarkers()
})

onUnmounted(() => {
  clearInterval(bookingValidityTimer)
  clearMarkerOverlays()
  closeLocationPopup()
  if (mapClickListener.value && window.google?.maps?.event) {
    window.google.maps.event.removeListener(mapClickListener.value)
  }
})

async function submitBooking() {
  if (!selectedVehicle.value) return
  if (existingBooking.value && isBookingActiveOrUpcoming(existingBooking.value)) {
    bookingError.value = 'You already have an active or upcoming booking. Cancel it first.'
    return
  }
  submitting.value = true
  bookingError.value = ''
  bookingSuccess.value = ''

  try {
    const uid = authStore.currentUser?.uid
    const res = await api.post('/api/book-car', {
      user_uid:         uid,
      vehicle_id:       selectedVehicle.value.id,
      vehicle_type:     selectedVehicle.value.vehicle_type,
      pickup_datetime:  pickupDatetime.value,
      hours:            hours.value,
      payment_method:   'pm_card_visa',
    })

    bookingSuccess.value = `Booking confirmed! ID: ${res.data.booking_id || res.data.id}`
    bookingJustSucceeded.value = true  // suppress "cancel before booking" banner
    closePaymentModal()
    selectedVehicle.value = null
    estimatedPrice.value = null
    await loadVehicles()
    await checkExistingBooking()  // still sets existingBooking so openPaymentModal blocks re-booking
  } catch (err) {
    bookingError.value =
      err.response?.data?.error ||
      err.response?.data?.message ||
      'Booking failed. Please try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.bookcar-page { min-height: 100vh; }

/* ── PAGE HEADER ─────────────────────────────────────────── */
.bookcar-header {
  background: var(--c-dark);
  padding: 28px 24px 32px;
  margin-bottom: 0;
}
.bookcar-header__inner {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.bookcar-header h1 {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.4px;
  margin-bottom: 4px;
}
.bookcar-header__sub { font-size: 13px; color: #64748b; }
.bookcar-header__stats { display: flex; align-items: center; gap: 20px; }
.header-stat { text-align: center; }
.header-stat-val { display: block; font-size: 22px; font-weight: 800; color: #fff; line-height: 1; }
.header-stat-label { font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.header-stat-divider { width: 1px; height: 32px; background: rgba(255,255,255,0.08); }

.bookcar-body { padding-top: 28px; padding-bottom: 48px; max-width: 960px; }

.existing-booking-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-left: 3px solid #f59e0b;
  border-radius: var(--radius);
  padding: 16px 20px;
  margin-bottom: 20px;
}
.existing-booking-banner__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
  color: #92400e;
}
.existing-booking-banner__body strong { font-weight: 700; }
.existing-booking-banner__body code {
  font-family: monospace;
  background: rgba(0,0,0,0.06);
  padding: 1px 5px;
  border-radius: 3px;
}
.existing-booking-banner__cta { width: auto; padding: 9px 20px; font-size: 13px; flex-shrink: 0; }

/* Map */
.map-section { margin-bottom: 24px; }

/* Booking panel */
.booking-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }

.selected-vehicle,
.no-selection {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
}
.selected-vehicle h3 {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.7px; color: var(--c-muted); margin-bottom: 14px;
  display: flex; align-items: center; gap: 6px;
}
.selected-vehicle h3::before {
  content: ''; display: inline-block; width: 3px; height: 14px;
  background: var(--c-accent); border-radius: 2px;
}
.selected-vehicle p { font-size: 14px; color: var(--c-dark); margin-bottom: 8px; }
.selected-vehicle strong { font-weight: 700; color: var(--c-primary); }
.no-selection {
  color: var(--c-muted); display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px;
  font-size: 14px; text-align: center; min-height: 120px;
  border-style: dashed;
}

.booking-form {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
}
.btn-primary { width: 100%; padding: 13px; justify-content: center; font-size: 15px; }

/* Vehicle list */
.vehicle-list {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  padding: 20px 20px 24px;
  box-shadow: var(--shadow);
}
.vehicle-list h3 {
  font-size: 15px; font-weight: 700; color: var(--c-dark);
  margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
}
.count {
  background: var(--c-accent); color: #fff;
  font-size: 11px; font-weight: 700;
  padding: 2px 8px; border-radius: 9999px;
}
.vehicle-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }

.vehicle-card {
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm);
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
  background: var(--c-surface);
}
.vehicle-card:hover { border-color: var(--c-accent); box-shadow: var(--shadow-md); transform: translateY(-2px); }
.vehicle-card.selected {
  border-color: var(--c-accent);
  background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
  box-shadow: 0 0 0 3px rgba(220,38,38,0.12);
}
.vehicle-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.vehicle-type { font-size: 10px; text-transform: uppercase; font-weight: 800; color: var(--c-muted); letter-spacing: 0.8px; }
.vehicle-status { font-size: 10px; padding: 2px 8px; border-radius: 9999px; font-weight: 700; }
.vehicle-status.available   { background: var(--c-success-bg); color: var(--c-success); }
.vehicle-status.rented      { background: var(--c-error-bg);   color: var(--c-error); }
.vehicle-status.maintenance { background: var(--c-warn-bg);    color: var(--c-warn); }
.vehicle-plate { font-size: 17px; font-weight: 800; color: var(--c-dark); margin-bottom: 4px; letter-spacing: 0.5px; }
.vehicle-meta  { font-size: 12px; color: var(--c-muted); }

.empty-state { color: var(--c-muted); text-align: center; padding: 40px; font-size: 14px; }

:deep(.car-map-marker) {
  position: absolute;
  width: 42px;
  height: 42px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  transform: translate(-50%, -50%);
  transition: transform 0.15s ease, filter 0.15s ease;
}

:deep(.car-map-marker svg) {
  display: block;
  width: 100%;
  height: 100%;
}

:deep(.car-map-marker:hover),
:deep(.car-map-marker.is-active) {
  transform: translate(-50%, -50%) scale(1.08);
  filter: drop-shadow(0 8px 16px rgba(16, 37, 66, 0.25));
}

:deep(.map-location-panel) {
  position: absolute;
  width: 252px;
  max-height: 260px;
  padding: 8px 0 0;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 18px 40px rgba(16, 37, 66, 0.18);
  border: 1px solid #e5e7eb;
  transform: translateY(-50%);
}

:deep(.map-location-panel__close) {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 999px;
  background: #f3f4f6;
  color: #374151;
  cursor: pointer;
}

:deep(.map-location-panel__header) {
  padding: 6px 14px 12px;
  font-size: 0.8rem;
  font-weight: 700;
  color: #1a1a2e;
  border-bottom: 1px solid #eef1f5;
}

:deep(.map-location-panel__list) {
  max-height: 190px;
  overflow-y: auto;
  padding: 10px;
}

:deep(.map-location-panel__item) {
  display: block;
  width: 100%;
  margin-bottom: 8px;
  padding: 10px 12px;
  border: 1px solid #dfe5ec;
  border-radius: 10px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

:deep(.map-location-panel__item:last-child) {
  margin-bottom: 0;
}

:deep(.map-location-panel__item:hover),
:deep(.map-location-panel__item.is-selected) {
  border-color: #1a1a2e;
  background: #f5f7ff;
}

:deep(.map-location-panel__title) {
  font-size: 0.85rem;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}

:deep(.map-location-panel__meta) {
  font-size: 0.75rem;
  color: #6b7280;
}

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
.dummy-card-fields { display: flex; flex-direction: column; gap: 12px; }
.dummy-field-row { display: flex; gap: 12px; }
.dummy-field-row .dummy-field-group { flex: 1; }
.dummy-field-group { display: flex; flex-direction: column; gap: 4px; }
.dummy-field-label { font-size: 11px; font-weight: 600; color: var(--c-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.dummy-field-input {
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  background: var(--c-bg);
  font-size: 14px; color: var(--c-dark);
  font-family: monospace;
  cursor: default;
  width: 100%; box-sizing: border-box;
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
</style>
