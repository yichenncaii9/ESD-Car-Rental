<template>
  <div class="profile-page">

    <!-- ── HERO HEADER ──────────────────────────────────────── -->
    <div class="profile-hero">
      <div class="profile-hero__orb" aria-hidden="true"></div>
      <div class="profile-hero__inner view-container">
        <div class="profile-avatar">
          {{ (form.name || authStore.currentUser?.email || 'U').charAt(0).toUpperCase() }}
        </div>
        <div class="profile-hero__copy">
          <h1>{{ form.name || 'Driver Profile' }}</h1>
          <p class="profile-hero__email">{{ authStore.currentUser?.email }}</p>
        </div>
        <div class="profile-hero__badge-wrap">
          <span v-if="licenseExpired" class="hero-badge hero-badge--red">
            <span class="hero-badge-dot"></span>License Expired
          </span>
          <span v-else-if="driverExists" class="hero-badge hero-badge--green">
            <span class="hero-badge-dot"></span>Verified Driver
          </span>
          <span v-else class="hero-badge hero-badge--amber">
            <span class="hero-badge-dot"></span>Unregistered
          </span>
        </div>
      </div>
    </div>

    <!-- ── BODY ─────────────────────────────────────────────── -->
    <div class="view-container profile-body">

      <div v-if="statusMsg" class="status-toast" :class="statusType">
        <svg v-if="statusType === 'success'" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <svg v-else width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        {{ statusMsg }}
      </div>

      <!-- Onboarding welcome banner -->
      <div v-if="isOnboarding && !driverExists" class="onboarding-banner">
        <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <div>
          <strong>Welcome! Complete your profile to get started.</strong>
          <p>Fill in your details and driver license below, then click Register.</p>
        </div>
      </div>

      <!-- Personal Info -->
      <div class="profile-section">
        <div class="section-label">
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
          Personal Information
        </div>
        <div class="card">
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
                <input v-model="form.phone" type="tel" placeholder="e.g. +65 9123 4567" :disabled="saving" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Driver License -->
      <div class="profile-section">
        <div class="section-label">
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M16 10h2M16 14h2M6 10h4v4H6z"/></svg>
          Driver License
          <span v-if="licenseExpired" class="label-badge label-badge--red">Expired</span>
          <span v-else-if="driverExists" class="label-badge label-badge--green">Valid</span>
          <span v-else class="label-badge label-badge--amber">Not registered</span>
        </div>
        <div class="card">
          <div class="card-body">
            <div class="form-grid">
              <div class="form-group">
                <label>License Number</label>
                <input v-model="form.license_number" type="text" placeholder="e.g. S1234567A" :disabled="saving || driverExists" />
                <p v-if="driverExists" class="field-hint">Cannot be changed after registration.</p>
              </div>
              <div class="form-group">
                <label>License Expiry</label>
                <input v-model="form.license_expiry" type="date" :disabled="saving" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- UID -->
      <div class="uid-box">
        <span class="uid-label">Firebase UID</span>
        <span class="uid-value">{{ authStore.currentUser?.uid }}</span>
      </div>

      <p v-if="saveError" class="error-msg">{{ saveError }}</p>

      <button class="btn-primary save-btn" @click="saveProfile" :disabled="saving">
        <span class="btn-spinner" v-if="saving" aria-hidden="true"></span>
        {{ saving ? 'Saving...' : driverExists ? 'Save Changes' : 'Register Driver Profile' }}
      </button>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const isOnboarding = computed(() => route.query.onboarding === '1')

const driverExists = ref(false)
const saving       = ref(false)
const saveError    = ref('')
const statusMsg    = ref('')
const statusType   = ref('success')

const form = ref({
  name:            '',
  email:           '',
  phone:           '',
  license_number:  '',
  license_expiry:  '',
})

const licenseExpired = computed(() => {
  if (!form.value.license_expiry) return false
  return new Date(form.value.license_expiry) <= new Date()
})

onMounted(async () => {
  const uid = authStore.currentUser?.uid
  if (!uid) return
  form.value.email = authStore.currentUser?.email || ''
  try {
    const res = await api.get(`/api/drivers/${uid}`)
    const d = res.data.data || res.data
    form.value.name           = d.name           || ''
    form.value.email          = d.email          || form.value.email
    form.value.phone          = d.phone          || ''
    form.value.license_number = d.license_number || ''
    form.value.license_expiry = d.license_expiry || ''
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
        phone:          form.value.phone,
        license_expiry: form.value.license_expiry,
      })
      statusMsg.value  = 'Profile updated successfully.'
      statusType.value = 'success'
    } else {
      await api.post('/api/drivers', {
        uid,
        name:           form.value.name,
        email:          form.value.email,
        phone:          form.value.phone,
        license_number: form.value.license_number,
        license_expiry: form.value.license_expiry,
      })
      driverExists.value = true
      authStore.setProfileComplete(true)
      if (isOnboarding.value) {
        router.push('/book-car')
        return
      }
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
.profile-page { min-height: 100vh; }

/* ── HERO ──────────────────────────────────────────────────── */
.profile-hero {
  position: relative;
  background: var(--c-dark);
  overflow: hidden;
  padding: 36px 24px 40px;
  margin-bottom: 32px;
}
.profile-hero__orb {
  position: absolute;
  width: 400px; height: 400px;
  right: -80px; top: -120px;
  background: radial-gradient(circle, rgba(220,38,38,0.2) 0%, transparent 65%);
  border-radius: 50%;
  pointer-events: none;
}
.profile-hero__inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.profile-avatar {
  width: 64px; height: 64px;
  background: var(--c-accent);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 800;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 20px rgba(220,38,38,0.35);
}

.profile-hero__copy { flex: 1; min-width: 0; }
.profile-hero__copy h1 {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.3px;
  margin-bottom: 3px;
}
.profile-hero__email { font-size: 13px; color: #94a3b8; }

.profile-hero__badge-wrap { margin-left: auto; }
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.hero-badge-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.hero-badge--green { background: rgba(34,197,94,0.15); color: #4ade80; }
.hero-badge--red   { background: rgba(220,38,38,0.15);  color: #f87171; }
.hero-badge--amber { background: rgba(245,158,11,0.15); color: #fbbf24; }

/* ── BODY ──────────────────────────────────────────────────── */
.profile-body { max-width: 680px; padding-bottom: 48px; }

.status-toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 24px;
}
.status-toast.success { background: var(--c-success-bg); color: var(--c-success); border: 1px solid #86efac; }
.status-toast.info    { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }

/* Sections */
.profile-section { margin-bottom: 8px; }
.section-label {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--c-muted);
  margin-bottom: 10px;
}

.label-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 9999px;
  margin-left: 4px;
}
.label-badge--green { background: var(--c-success-bg); color: var(--c-success); }
.label-badge--red   { background: var(--c-error-bg);   color: var(--c-error); }
.label-badge--amber { background: var(--c-warn-bg);    color: var(--c-warn); }

.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 20px;
}
.card-body { padding: 20px; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.field-hint { font-size: 11px; color: var(--c-muted); margin: 4px 0 0; }

/* UID */
.uid-box {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  margin-bottom: 24px;
}
.uid-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--c-muted);
  white-space: nowrap;
  flex-shrink: 0;
}
.uid-value {
  font-size: 12px;
  color: var(--c-dark);
  font-family: 'Courier New', monospace;
  word-break: break-all;
  min-width: 0;
}

.onboarding-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-left: 3px solid #3b82f6;
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  margin-bottom: 24px;
  color: #1e40af;
  font-size: 13px;
  line-height: 1.6;
}
.onboarding-banner svg { flex-shrink: 0; margin-top: 2px; }
.onboarding-banner strong { display: block; font-size: 14px; margin-bottom: 2px; }
.onboarding-banner p { margin: 0; color: #3b82f6; }

.save-btn {
  padding: 13px 32px;
  font-size: 15px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.btn-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 540px) {
  .form-grid { grid-template-columns: 1fr; }
  .profile-hero__badge-wrap { width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  .btn-spinner { animation: none; }
}
</style>
