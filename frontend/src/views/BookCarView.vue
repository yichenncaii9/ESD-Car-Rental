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
          :position="{ lat: v.lat || 1.3521, lng: v.lng || 103.8198 }"
          :clickable="true"
          :title="`${v.type} — ${v.plate}`"
          @click="selectVehicle(v)"
        />
      </GMapMap>
    </div>

    <!-- Booking panel -->
    <div class="booking-panel">
      <!-- Selected vehicle card -->
      <div v-if="selectedVehicle" class="selected-vehicle">
        <h3>Selected Vehicle</h3>
        <p><strong>Type:</strong> {{ selectedVehicle.type }}</p>
        <p><strong>Plate:</strong> {{ selectedVehicle.plate }}</p>
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

    <!-- Vehicle list fallback -->
    <div class="vehicle-list" v-if="vehicles.length > 0">
      <h3>Available Vehicles ({{ vehicles.length }})</h3>
      <table>
        <thead><tr><th>Type</th><th>Plate</th><th>Status</th><th></th></tr></thead>
        <tbody>
          <tr v-for="v in vehicles" :key="v.id" :class="{ selected: selectedVehicle?.id === v.id }">
            <td>{{ v.type }}</td>
            <td>{{ v.plate }}</td>
            <td>{{ v.status }}</td>
            <td><button @click="selectVehicle(v)" class="btn-select">Select</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="!loading" class="empty-state">No vehicles available.</p>
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
    vehicles.value = res.data.vehicles || res.data || []
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
      vehicle_id:       selectedVehicle.value.id,
      uid,
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
.vehicle-list h3 { margin-bottom: 12px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #eee; }
th { background: #f8f8f8; font-size: 0.85rem; color: #555; }
tr.selected { background: #e8f0fe; }
.btn-select { padding: 4px 10px; background: #16213e; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; }
.empty-state { color: #999; text-align: center; padding: 24px; }
</style>
