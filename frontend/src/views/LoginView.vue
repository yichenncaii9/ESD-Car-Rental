<template>
  <div class="login-shell">

    <!-- ── LEFT BRAND PANEL ───────────────────────────────── -->
    <div class="brand-panel" aria-hidden="true">
      <div class="bp-orb bp-orb--1"></div>
      <div class="bp-orb bp-orb--2"></div>
      <div class="bp-grid"></div>
      <div class="bp-content">
        <div class="bp-logo">
          <span class="bp-logo-dot"></span>
          <span class="bp-logo-name">DriveEase</span>
        </div>
        <h2 class="bp-headline">The road is yours.</h2>
        <p class="bp-sub">Premium vehicles on demand. Book by the hour, pay securely, drive instantly.</p>
        <div class="bp-pills">
          <span class="bp-pill">Sedan · $12.50/hr</span>
          <span class="bp-pill">SUV · $18.00/hr</span>
          <span class="bp-pill">Van · $15.00/hr</span>
        </div>
        <div class="bp-trust">
          <div class="bp-trust-item">
            <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
            Stripe-secured payments
          </div>
          <div class="bp-trust-item">
            <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><circle cx="12" cy="11" r="3"/></svg>
            Google Maps integrated
          </div>
        </div>
      </div>
    </div>

    <!-- ── RIGHT FORM PANEL ──────────────────────────────── -->
    <div class="form-panel">
      <div class="login-card">
        <div class="lc-header">
          <div class="lc-mode-indicator" :class="{ signup: !isLogin }"></div>
          <h2>{{ isLogin ? 'Welcome back' : 'Create account' }}</h2>
          <p class="lc-sub">{{ isLogin ? 'Sign in to continue your journey.' : 'Join DriveEase and start booking.' }}</p>
        </div>

        <form @submit.prevent="submit" class="lc-form">
          <div class="form-group">
            <label for="email">Email address</label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              placeholder="you@example.com"
              :disabled="loading"
            />
          </div>
          <div class="form-group">
            <label for="password">Password</label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              placeholder="••••••••"
              :disabled="loading"
            />
          </div>
          <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
          <button type="submit" class="btn-primary" :disabled="loading">
            <span class="btn-spinner" v-if="loading" aria-hidden="true"></span>
            {{ loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Create Account') }}
          </button>
        </form>

        <div class="lc-divider"><span>or</span></div>

        <button class="btn-toggle" @click="toggleMode">
          {{ isLogin ? "Don't have an account? Sign Up" : 'Already have an account? Log In' }}
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { signInWithEmailAndPassword, createUserWithEmailAndPassword } from 'firebase/auth'
import { auth } from '../firebase'

const router = useRouter()

const isLogin  = ref(true)
const email    = ref('')
const password = ref('')
const loading  = ref(false)
const errorMsg = ref('')

function toggleMode() {
  isLogin.value  = !isLogin.value
  errorMsg.value = ''
}

function friendlyError(code) {
  const map = {
    'auth/user-not-found':        'No account found with this email.',
    'auth/wrong-password':        'Incorrect password.',
    'auth/invalid-credential':    'Invalid email or password.',
    'auth/email-already-in-use':  'An account with this email already exists.',
    'auth/invalid-email':         'Please enter a valid email address.',
    'auth/weak-password':         'Password must be at least 6 characters.',
    'auth/too-many-requests':     'Too many attempts. Please try again later.',
  }
  return map[code] || 'An error occurred. Please try again.'
}

async function submit() {
  loading.value  = true
  errorMsg.value = ''
  try {
    if (isLogin.value) {
      await signInWithEmailAndPassword(auth, email.value, password.value)
    } else {
      await createUserWithEmailAndPassword(auth, email.value, password.value)
    }
    router.push('/book-car')
  } catch (err) {
    errorMsg.value = friendlyError(err.code)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ── SHELL ───────────────────────────────────────────────── */
.login-shell {
  display: flex;
  min-height: 100vh;
  font-family: var(--font);
}

/* ── LEFT BRAND PANEL ─────────────────────────────────────── */
.brand-panel {
  position: relative;
  flex: 1;
  display: none;
  background: var(--c-dark);
  overflow: hidden;
}
@media (min-width: 900px) { .brand-panel { display: flex; align-items: center; } }

.bp-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
}
.bp-orb--1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(220,38,38,0.25) 0%, transparent 70%);
  top: -120px; right: -100px;
}
.bp-orb--2 {
  width: 350px; height: 350px;
  background: radial-gradient(circle, rgba(30,64,175,0.2) 0%, transparent 70%);
  bottom: -80px; left: -60px;
}
.bp-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
}

.bp-content {
  position: relative;
  z-index: 1;
  padding: 56px;
  max-width: 460px;
}

.bp-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 48px;
}
.bp-logo-dot {
  width: 32px; height: 32px;
  background: var(--c-accent);
  border-radius: 9px;
}
.bp-logo-name {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.3px;
}

.bp-headline {
  font-size: 44px;
  font-weight: 900;
  color: #fff;
  line-height: 1.1;
  letter-spacing: -1px;
  margin-bottom: 16px;
}

.bp-sub {
  font-size: 16px;
  color: #94a3b8;
  line-height: 1.7;
  margin-bottom: 32px;
}

.bp-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 36px;
}
.bp-pill {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 9999px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #cbd5e1;
}

.bp-trust { display: flex; flex-direction: column; gap: 10px; }
.bp-trust-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #64748b;
}

/* ── RIGHT FORM PANEL ──────────────────────────────────────── */
.form-panel {
  width: 100%;
  max-width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 32px;
  background: var(--c-bg);
  min-height: 100vh;
}
@media (min-width: 900px) { .form-panel { flex: none; } }

.login-card {
  width: 100%;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 20px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.10);
  padding: 40px;
}

.lc-header { margin-bottom: 28px; }
.lc-mode-indicator {
  width: 40px; height: 4px;
  background: var(--c-accent);
  border-radius: 9999px;
  margin-bottom: 20px;
  transition: width 0.3s ease;
}
.lc-mode-indicator.signup { width: 64px; }

.lc-header h2 {
  font-size: 26px;
  font-weight: 800;
  color: var(--c-dark);
  letter-spacing: -0.5px;
  margin-bottom: 6px;
}
.lc-sub { font-size: 14px; color: var(--c-muted); }

.lc-form { margin-bottom: 0; }

.btn-primary {
  width: 100%;
  padding: 13px;
  font-size: 15px;
  justify-content: center;
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 10px;
  margin-top: 4px;
}

.btn-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.lc-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
  color: var(--c-border);
  font-size: 12px;
}
.lc-divider::before,
.lc-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--c-border);
}
.lc-divider span { color: var(--c-muted); }

.btn-toggle {
  display: block;
  width: 100%;
  padding: 10px;
  background: transparent;
  border: 1.5px solid var(--c-border);
  border-radius: 10px;
  color: var(--c-muted);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font);
  text-align: center;
  transition: border-color 0.15s, color 0.15s;
}
.btn-toggle:hover { border-color: var(--c-accent); color: var(--c-accent); }

@media (prefers-reduced-motion: reduce) {
  .btn-spinner { animation: none; }
}
</style>
