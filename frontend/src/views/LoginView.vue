<template>
  <div class="login-wrapper">
    <div class="login-card">
      <h2>{{ isLogin ? 'Log In' : 'Sign Up' }}</h2>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label for="email">Email</label>
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
            placeholder="Password"
            :disabled="loading"
          />
        </div>
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? 'Processing...' : (isLogin ? 'Log In' : 'Sign Up') }}
        </button>
      </form>
      <button class="btn-toggle" @click="toggleMode">
        {{ isLogin ? "Don't have an account? Sign Up" : 'Already have an account? Log In' }}
      </button>
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
    'auth/invalid-credential':    'Invalid email or password.',  // Firebase v10 consolidated code
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
.login-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
}
.login-card {
  background: white;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 400px;
}
h2 { margin-bottom: 24px; color: #1a1a2e; font-size: 1.5rem; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; color: #555; font-size: 0.9rem; }
.form-group input {
  width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 4px;
  font-size: 1rem; outline: none; transition: border-color 0.2s;
}
.form-group input:focus { border-color: #16213e; }
.error-msg { color: #e94560; font-size: 0.875rem; margin-bottom: 12px; }
.btn-primary {
  width: 100%; padding: 12px; background: #1a1a2e; color: white;
  border: none; border-radius: 4px; font-size: 1rem; cursor: pointer;
  transition: background 0.2s;
}
.btn-primary:disabled { background: #999; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { background: #16213e; }
.btn-toggle {
  display: block; width: 100%; margin-top: 16px; padding: 8px;
  background: none; border: none; color: #16213e; cursor: pointer;
  font-size: 0.9rem; text-decoration: underline;
}
</style>
