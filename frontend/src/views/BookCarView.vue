<template>
  <div class="view-container">
    <h1>Book a Car</h1>

    <!-- Map with vehicle markers -->
    <div class="map-section">
      <p class="map-hint">Click a marker to select a vehicle</p>
      <GMapMap
        :center="mapCenter"
        :zoom="12"
        style="width: 100%; height: 480px; border-radius: 8px;"
      >
        <GMapMarker
          v-for="v in vehicles"
          :key="v.id"
          :position="{ lat: v.location_lat || 1.3521, lng: v.location_lng || 103.8198 }"
          :clickable="true"
          :title="`${v.vehicle_type} — ${v.plate_number}`"
          @click="selectVehicle(v)"
        />
      </GMapMap>
    </div>

    <!-- Booking panel -->
    <div class="booking-panel">
      <!-- Selected vehicle card -->
      <div v-if="selectedVehicle" class="selected-vehicle">
        <h3>Selected Vehicle</h3>
        <p><strong>Type:</strong> {{ selectedVehicle.vehicle_type }}</p>
        <p><strong>Plate:</strong> {{ selectedVehicle.plate_number }}</p>
        <p><strong>Status:</strong> {{ selectedVehicle.status }}</p>
      </div>
      <div v-else class="no-selection">
        <p>No vehicle selected. Click a marker on the map.</p>
      </div>

      <!-- Booking form -->
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

    <!-- Live vehicle list -->
    <div class="vehicle-list">
      <h3>Available Vehicles <span class="count" v-if="vehicles.length">({{ vehicles.length }})</span></h3>
      <p v-if="loading" class="empty-state">Loading...</p>
      <p v-else-if="!vehicles.length" class="empty-state">No vehicles available.</p>
      <div v-else class="vehicle-cards">
        <div
          v-for="v in vehicles"
          :key="v.id"
          class="vehicle-card"
          :class="{ selected: selectedVehicle?.id === v.id, unavailable: v.status !== 'available' }"
          @click="v.status === 'available' && selectVehicle(v)"
        >
          <div class="vehicle-card-top">
            <span class="vehicle-type">{{ v.vehicle_type }}</span>
            <span class="vehicle-status" :class="v.status">{{ v.status }}</span>
          </div>
          <div class="vehicle-plate">{{ v.plate_number }}</div>
          <div class="vehicle-meta">{{ v.make }} {{ v.model }} · {{ v.year }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const mapCenter     = ref({ lat: 1.3521, lng: 103.8198 })
const vehicles      = ref([])
const selectedVehicle = ref(null)
const loading       = ref(false)
const pickupDatetime = ref('')
const hours         = ref(2)
const submitting    = ref(false)
const bookingError  = ref('')
const bookingSuccess = ref('')

function selectVehicle(v) {
  selectedVehicle.value = v
  bookingError.value = ''
  bookingSuccess.value = ''
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await api.get('/api/vehicles')
    vehicles.value = res.data.data || res.data.vehicles || []
  } catch (err) {
    console.error('Failed to load vehicles:', err.message)
  } finally {
    loading.value = false
  }
})

async function submitBooking() {
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
      hours:            hours.value
    })
    bookingSuccess.value = `Booking confirmed! ID: ${res.data.booking_id || res.data.id}`
    selectedVehicle.value = null
  } catch (err) {
    bookingError.value = err.response?.data?.error || 'Booking failed. Please try again.'
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
</style>
