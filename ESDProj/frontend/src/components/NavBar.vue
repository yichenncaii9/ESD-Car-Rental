<template>
  <nav v-if="authStore.currentUser" class="navbar">
    <div class="nav-links">
      <router-link to="/book-car" active-class="active">Book Car</router-link>
      <router-link to="/cancel-booking" active-class="active">Cancel Booking</router-link>
      <router-link to="/report-incident" active-class="active">Report Incident</router-link>
      <router-link to="/service-dashboard" active-class="active">Service Dashboard</router-link>
    </div>
    <div class="nav-user">
      <span class="user-email">{{ authStore.currentUser.email }}</span>
      <button @click="handleLogout" class="btn-logout">Logout</button>
    </div>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { signOut } from 'firebase/auth'
import { auth } from '../firebase'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

async function handleLogout() {
  await signOut(auth)
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #1a1a2e;
  color: white;
}
.nav-links { display: flex; gap: 20px; }
.nav-links a { color: #ccc; text-decoration: none; padding: 6px 12px; border-radius: 4px; }
.nav-links a.active { color: white; background: #16213e; }
.nav-user { display: flex; align-items: center; gap: 12px; }
.user-email { font-size: 0.9rem; color: #aaa; }
.btn-logout { padding: 6px 14px; background: #e94560; color: white; border: none; border-radius: 4px; cursor: pointer; }
</style>
