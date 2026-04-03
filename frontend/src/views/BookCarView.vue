<template>
  <div class="view-container">
    <h1>Book a Car</h1>

    <div class="map-section">
      <p class="map-hint">Click a marker to choose from vehicles at the same location</p>
      <GMapMap
        ref="mapRef"
        :center="mapCenter"
        :zoom="12"
        style="width: 100%; height: 480px; border-radius: 8px;"
      />
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

      <form v-if="selectedVehicle" @submit.prevent="submitBooking" class="booking-form">
        <div class="form-group">
          <label>Pickup Date & Time</label>
          <input v-model="pickupDatetime" type="datetime-local" required :disabled="submitting" />
        </div>
        <div class="form-group">
          <label>Duration (hours)</label>
          <input v-model.number="hours" type="number" min="1" max="72" required :disabled="submitting" />
        </div>
        <p v-if="bookingError" class="error-msg">{{ bookingError }}</p>
        <p v-if="bookingSuccess" class="success-msg">{{ bookingSuccess }}</p>
        <button type="submit" class="btn-primary" :disabled="submitting">
          {{ submitting ? 'Booking...' : 'Confirm Booking' }}
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
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

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
    <path d="M12.6 23.2a2.4 2.4 0 0 1 2.264-1.616h18.272a2.4 2.4 0 0 1 2.264 1.616l2.367 7.102c.08.242.121.496.121.75v4.148A2.4 2.4 0 0 1 35.488 37h-1.08a1.2 1.2 0 0 1-1.2-1.2v-.96H14.792v.96a1.2 1.2 0 0 1-1.2 1.2h-1.08a2.4 2.4 0 0 1-2.4-2.4v-4.148c0-.254.041-.508.121-.75l2.367-7.102Z" fill="#f8fafc"/>
    <path d="M16.08 20.56 17.92 15.52h12.16l1.84 5.04H16.08Z" fill="#9bd3ff"/>
    <path d="M19.2 14.08c0-.796.645-1.44 1.44-1.44h6.72c.795 0 1.44.644 1.44 1.44v1.44H19.2v-1.44Z" fill="#1f2937"/>
    <circle cx="18.72" cy="30.76" r="2.76" fill="#111827"/>
    <circle cx="29.28" cy="30.76" r="2.76" fill="#111827"/>
    <path d="M12.6 23.2a2.4 2.4 0 0 1 2.264-1.616h18.272a2.4 2.4 0 0 1 2.264 1.616l2.367 7.102c.08.242.121.496.121.75v1.028H10.112v-1.028c0-.254.041-.508.121-.75l2.367-7.102Z" stroke="#1f2937" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M16.08 20.56 17.92 15.52h12.16l1.84 5.04H16.08Z" stroke="#1f2937" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M19.2 15.52v-1.44c0-.796.645-1.44 1.44-1.44h6.72c.795 0 1.44.644 1.44 1.44v1.44" stroke="#1f2937" stroke-width="1.6" stroke-linecap="round"/>
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

onMounted(async () => {
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
  clearMarkerOverlays()
  closeLocationPopup()
  if (mapClickListener.value && window.google?.maps?.event) {
    window.google.maps.event.removeListener(mapClickListener.value)
  }
})

async function submitBooking() {
  if (!selectedVehicle.value) return

  submitting.value = true
  bookingError.value = ''
  bookingSuccess.value = ''
  try {
    const uid = authStore.currentUser?.uid
    const res = await api.post('/api/book-car', {
      user_uid: uid,
      vehicle_id: selectedVehicle.value.id,
      vehicle_type: selectedVehicle.value.vehicle_type,
      pickup_datetime: pickupDatetime.value,
      hours: hours.value
    })
    bookingSuccess.value = `Booking confirmed! ID: ${res.data.booking_id || res.data.id}`
    selectedVehicle.value = null
    await loadVehicles()
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
.view-container { max-width: 960px; margin: 0 auto; }
h1 { margin-bottom: 20px; color: #1a1a2e; }
.map-section { margin-bottom: 24px; }
.map-hint { margin-bottom: 8px; color: #666; font-size: 0.9rem; }
.booking-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }
.selected-vehicle, .no-selection { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.selected-vehicle h3 { margin-bottom: 12px; color: #1a1a2e; }
.no-selection { color: #999; display: flex; align-items: center; justify-content: center; }
.booking-form { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; color: #555; font-size: 0.9rem; }
.form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem; }
.error-msg { color: #e94560; font-size: 0.875rem; margin-bottom: 12px; }
.success-msg { color: #2ecc71; font-size: 0.875rem; margin-bottom: 12px; }
.btn-primary { width: 100%; padding: 12px; background: #1a1a2e; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-primary:disabled { background: #999; cursor: not-allowed; }
.vehicle-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.vehicle-list h3 { margin-bottom: 16px; }
.count { font-weight: normal; color: #888; font-size: 0.9rem; }
.vehicle-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.vehicle-card { border: 2px solid #eee; border-radius: 8px; padding: 14px; cursor: pointer; transition: all 0.15s; }
.vehicle-card:hover:not(.unavailable) { border-color: #1a1a2e; background: #f5f7ff; }
.vehicle-card.selected { border-color: #1a1a2e; background: #e8f0fe; }
.vehicle-card.unavailable { opacity: 0.5; cursor: not-allowed; }
.vehicle-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.vehicle-type { font-size: 0.75rem; text-transform: uppercase; font-weight: 600; color: #555; letter-spacing: 0.05em; }
.vehicle-status { font-size: 0.7rem; padding: 2px 7px; border-radius: 12px; font-weight: 600; }
.vehicle-status.available { background: #d4edda; color: #155724; }
.vehicle-status.rented { background: #f8d7da; color: #721c24; }
.vehicle-status.maintenance { background: #fff3cd; color: #856404; }
.vehicle-plate { font-size: 1.1rem; font-weight: 700; color: #1a1a2e; margin-bottom: 4px; }
.vehicle-meta { font-size: 0.8rem; color: #888; }
.empty-state { color: #999; text-align: center; padding: 24px; }

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
</style>
