<template>
  <div class="view-container">
    <h1>My Driver Profile</h1>
    <p class="subtitle">Your details are used to validate your license before each booking.</p>

    <!-- Status badge -->
    <div v-if="statusMsg" class="status-badge" :class="statusType">{{ statusMsg }}</div>

    <!-- Personal Info Card -->
    <div class="card">
      <div class="card-header">
        <h3>Personal Information</h3>
      </div>
      <div class="card-body">
        <div class="form-grid">
          <div class="form-group">
            <label>Full Name</label>
            <input v-model="form.name" type="text" placeholder="Your name" :disabled="saving" />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input v-model="form.email" type="email" placeholder="your@email.com" :disabled="saving" />
          </div>
          <div class="form-group">
            <label>Phone Number</label>
            <input v-model="form.phone" type="tel" placeholder="+65XXXXXXXX" :disabled="saving" />
          </div>
        </div>
      </div>
    </div>

    <!-- Driver License Card -->
    <div class="card">
      <div class="card-header">
        <h3>Driver License</h3>
        <span v-if="licenseExpired" class="badge expired">Expired</span>
        <span v-else-if="driverExists" class="badge valid">Valid</span>
        <span v-else class="badge unregistered">Not registered</span>
      </div>
      <div class="card-body">
        <div class="form-grid">
          <div class="form-group">
            <label>License Number</label>
            <input v-model="form.license_number" type="text" placeholder="e.g. S1234567A" :disabled="saving || driverExists" />
            <p v-if="driverExists" class="field-hint">License number cannot be changed after registration.</p>
          </div>
          <div class="form-group">
            <label>License Expiry</label>
            <input v-model="form.license_expiry" type="date" :disabled="saving" />
          </div>
        </div>
      </div>
    </div>

    <!-- Firebase UID (read-only) -->
    <div class="uid-box">
      <span class="uid-label">Firebase UID</span>
      <span class="uid-value">{{ authStore.currentUser?.uid }}</span>
    </div>

    <!-- Error / success -->
    <p v-if="saveError" class="error-msg">{{ saveError }}</p>

    <button class="btn-primary" @click="saveProfile" :disabled="saving">
      {{ saving ? 'Saving...' : driverExists ? 'Save Changes' : 'Register Driver Profile' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const driverExists = ref(false)
const saving       = ref(false)
const saveError    = ref('')
const statusMsg    = ref('')
const statusType   = ref('success')

const form = ref({
  name:            '',
  email:           '',
  license_number:  '',
  license_expiry:  '',
  phone:           '',
})

const licenseExpired = computed(() => {
  if (!form.value.license_expiry) return false
  return new Date(form.value.license_expiry) <= new Date()
})

onMounted(async () => {
  const uid = authStore.currentUser?.uid
  if (!uid) return
  // Pre-fill email from Firebase Auth
  form.value.email = authStore.currentUser?.email || ''
  // Fetch existing driver record
  try {
    const res = await api.get(`/api/drivers/${uid}`)
    const d = res.data.data || res.data
    form.value.name           = d.name           || ''
    form.value.email          = d.email          || form.value.email
    form.value.license_number = d.license_number || ''
    form.value.license_expiry = d.license_expiry || ''
    form.value.phone          = d.phone          || ''
    driverExists.value = true
    statusMsg.value  = 'Driver record found — fields pre-filled.'
    statusType.value = 'success'
  } catch {
    driverExists.value = false
    statusMsg.value  = 'No driver record yet. Fill in the form to register.'
    statusType.value = 'info'
  }
})

async function saveProfile() {
  saving.value   = true
  saveError.value = ''
  statusMsg.value = ''
  const uid = authStore.currentUser?.uid
  try {
    if (driverExists.value) {
      await api.put(`/api/drivers/${uid}`, {
        name:           form.value.name,
        email:          form.value.email,
        license_expiry: form.value.license_expiry,
        phone:          form.value.phone,
      })
      statusMsg.value  = 'Profile updated successfully.'
      statusType.value = 'success'
    } else {
      await api.post('/api/drivers', {
        uid,
        name:           form.value.name,
        email:          form.value.email,
        license_number: form.value.license_number,
        license_expiry: form.value.license_expiry,
        phone:          form.value.phone,
      })
      driverExists.value = true
      statusMsg.value  = 'Driver profile registered successfully.'
      statusType.value = 'success'
    }
  } catch (err) {
    saveError.value = err.response?.data?.message || err.response?.data?.error || 'Save failed. Please try again.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.view-container { max-width: 680px; margin: 0 auto; }
h1 { margin-bottom: 4px; color: #1a1a2e; }
.subtitle { color: #888; font-size: 0.9rem; margin-bottom: 20px; }

.status-badge { display: inline-block; padding: 8px 14px; border-radius: 6px; font-size: 0.85rem; margin-bottom: 20px; }
.status-badge.success { background: #d4edda; color: #155724; }
.status-badge.info    { background: #d1ecf1; color: #0c5460; }

.card { background: white; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); margin-bottom: 20px; overflow: hidden; }
.card-header { display: flex; align-items: center; gap: 10px; padding: 16px 20px; border-bottom: 1px solid #eee; }
.card-header h3 { margin: 0; color: #1a1a2e; font-size: 1rem; }
.card-body { padding: 20px; }

.badge { font-size: 0.7rem; padding: 3px 8px; border-radius: 10px; font-weight: 600; }
.badge.valid       { background: #d4edda; color: #155724; }
.badge.expired     { background: #f8d7da; color: #721c24; }
.badge.unregistered { background: #fff3cd; color: #856404; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-size: 0.85rem; color: #555; }
.form-group input { padding: 9px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.95rem; }
.form-group input:disabled { background: #f9f9f9; color: #999; }
.form-group input:focus { outline: none; border-color: #1a1a2e; }
.field-hint { font-size: 0.75rem; color: #999; margin: 0; }

.uid-box { background: #f5f5f5; border-radius: 6px; padding: 12px 16px; margin-bottom: 20px; display: flex; flex-direction: column; gap: 4px; }
.uid-label { font-size: 0.75rem; color: #888; }
.uid-value { font-size: 0.85rem; color: #555; font-family: monospace; word-break: break-all; }

.error-msg { color: #e94560; font-size: 0.875rem; margin-bottom: 12px; }
.btn-primary { padding: 12px 28px; background: #1a1a2e; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
.btn-primary:disabled { background: #999; cursor: not-allowed; }
.btn-primary:hover:not(:disabled) { background: #16213e; }

@media (max-width: 540px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
