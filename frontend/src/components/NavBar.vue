<template>
  <nav v-if="authStore.currentUser" class="navbar">
    <ul class="nav-list">
      <li v-for="item in navItems" :key="item.label" class="nav-item">
        <component
          :is="item.action ? 'button' : 'router-link'"
          v-bind="item.action ? {} : { to: item.href, 'active-class': 'is-active' }"
          class="nav-link"
          :class="{ 'is-logout': item.isLogout }"
          :style="{ '--glow': item.gradient }"
          @click="item.action && item.action()"
        >
          <span class="glow-bg" />
          <span class="face face-front">
            <component :is="item.icon" class="icon" :class="item.iconColor" />
            <span class="label">{{ item.label }}</span>
          </span>
          <span class="face face-back">
            <component :is="item.icon" class="icon" :class="item.iconColor" />
            <span class="label">{{ item.label }}</span>
          </span>
        </component>
      </li>
    </ul>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { signOut } from 'firebase/auth'
import { auth } from '../firebase'
import { useAuthStore } from '../stores/auth'
import {
  Car, XCircle, AlertTriangle, LayoutDashboard, User, LogOut
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

async function handleLogout() {
  await signOut(auth)
  router.push('/login')
}

const navItems = [
  {
    icon: Car,
    label: 'Book Car',
    href: '/book-car',
    gradient: 'radial-gradient(circle, rgba(59,130,246,0.18) 0%, rgba(37,99,235,0.07) 50%, transparent 100%)',
    iconColor: 'blue',
  },
  {
    icon: XCircle,
    label: 'Cancel',
    href: '/cancel-booking',
    gradient: 'radial-gradient(circle, rgba(249,115,22,0.18) 0%, rgba(234,88,12,0.07) 50%, transparent 100%)',
    iconColor: 'orange',
  },
  {
    icon: AlertTriangle,
    label: 'Report',
    href: '/report-incident',
    gradient: 'radial-gradient(circle, rgba(239,68,68,0.18) 0%, rgba(220,38,38,0.07) 50%, transparent 100%)',
    iconColor: 'red',
  },
  {
    icon: LayoutDashboard,
    label: 'Dashboard',
    href: '/service-dashboard',
    gradient: 'radial-gradient(circle, rgba(34,197,94,0.18) 0%, rgba(22,163,74,0.07) 50%, transparent 100%)',
    iconColor: 'green',
  },
  {
    icon: User,
    label: 'Profile',
    href: '/profile',
    gradient: 'radial-gradient(circle, rgba(147,51,234,0.18) 0%, rgba(126,34,206,0.07) 50%, transparent 100%)',
    iconColor: 'purple',
  },
  {
    icon: LogOut,
    label: 'Logout',
    href: null,
    isLogout: true,
    action: handleLogout,
    gradient: 'radial-gradient(circle, rgba(161,98,7,0.18) 0%, rgba(133,77,14,0.07) 50%, transparent 100%)',
    iconColor: 'amber',
  },
]
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 50;
  padding: 6px 8px;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
}

@media (min-width: 640px) {
  .navbar {
    top: 16px;
    left: 50%;
    transform: translateX(-50%);
    width: auto;
    border-radius: 9999px;
    border: 1px solid rgba(0,0,0,0.08);
    padding: 8px 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  }
}

.nav-list {
  display: flex;
  align-items: center;
  justify-content: space-around;
  gap: 4px;
  list-style: none;
  margin: 0;
  padding: 0;
}

@media (min-width: 640px) {
  .nav-list { justify-content: center; gap: 8px; }
}

/* Individual nav item wrapper */
.nav-item {
  flex: 1;
  display: flex;
  justify-content: center;
  perspective: 600px;
}

@media (min-width: 640px) {
  .nav-item { flex: none; }
}

/* The link/button itself */
.nav-link {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 6px 8px;
  border-radius: 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  text-decoration: none;
  color: #555;
  perspective: 600px;
  overflow: visible;
  width: 100%;
  min-width: 52px;
  transition: color 0.2s;
}

@media (min-width: 640px) {
  .nav-link {
    flex-direction: row;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 16px;
    width: auto;
  }
}

/* Glow background */
.glow-bg {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--glow);
  opacity: 0;
  transform: scale(0.8);
  transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.34,1.56,0.64,1);
  pointer-events: none;
  z-index: 0;
}

.nav-link:hover .glow-bg,
.nav-link.is-active .glow-bg {
  opacity: 1;
  transform: scale(1.8);
}

/* Shared face styles */
.face {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  position: relative;
  z-index: 1;
  backface-visibility: hidden;
  transform-style: preserve-3d;
  transition: transform 0.45s cubic-bezier(0.4,0,0.2,1), opacity 0.35s ease;
}

@media (min-width: 640px) {
  .face { flex-direction: row; gap: 6px; }
}

/* Front face — visible by default */
.face-front {
  transform-origin: center bottom;
  transform: rotateX(0deg);
  opacity: 1;
}

.nav-link:hover .face-front {
  transform: rotateX(-90deg);
  opacity: 0;
}

/* Back face — hidden by default, flips in on hover */
.face-back {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  transform-origin: center top;
  transform: rotateX(90deg);
  opacity: 0;
}

@media (min-width: 640px) {
  .face-back { flex-direction: row; gap: 6px; }
}

.nav-link:hover .face-back {
  transform: rotateX(0deg);
  opacity: 1;
}

.icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  transition: color 0.3s;
}

.label {
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}

@media (min-width: 640px) {
  .label { font-size: 14px; }
}

/* Icon colours */
.icon.blue   { color: inherit; } .nav-link:hover .icon.blue,   .nav-link.is-active .icon.blue   { color: #3b82f6; }
.icon.orange { color: inherit; } .nav-link:hover .icon.orange, .nav-link.is-active .icon.orange { color: #f97316; }
.icon.red    { color: inherit; } .nav-link:hover .icon.red,    .nav-link.is-active .icon.red    { color: #ef4444; }
.icon.green  { color: inherit; } .nav-link:hover .icon.green,  .nav-link.is-active .icon.green  { color: #22c55e; }
.icon.purple { color: inherit; } .nav-link:hover .icon.purple, .nav-link.is-active .icon.purple { color: #9333ea; }
.icon.amber  { color: inherit; } .nav-link:hover .icon.amber                                    { color: #d97706; }

</style>
