import { createRouter, createWebHistory } from 'vue-router'
import { auth } from '../firebase'
import { onAuthStateChanged } from 'firebase/auth'
import { useAuthStore } from '../stores/auth'

function getCurrentUser() {
  return new Promise((resolve, reject) => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      unsubscribe()
      resolve(user)
    }, reject)
  })
}

const routes = [
  { path: '/login',             component: () => import('../views/LoginView.vue') },
  { path: '/',                  component: () => import('../views/LandingView.vue') },
  { path: '/book-car',          component: () => import('../views/BookCarView.vue'),          meta: { requiresAuth: true, requiresProfile: true } },
  { path: '/cancel-booking',    component: () => import('../views/CancelBookingView.vue'),    meta: { requiresAuth: true, requiresProfile: true } },
  { path: '/report-incident',   component: () => import('../views/ReportIncidentView.vue'),   meta: { requiresAuth: true, requiresProfile: true } },
  { path: '/service-dashboard', component: () => import('../views/ServiceDashboardView.vue'), meta: { requiresAuth: true, requiresProfile: true } },
  { path: '/profile',           component: () => import('../views/ProfileView.vue'),           meta: { requiresAuth: true } }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const user = await getCurrentUser()

  if (to.meta.requiresAuth && !user) return '/login'

  if (to.meta.requiresProfile && user) {
    const authStore = useAuthStore()
    if (authStore.profileComplete === null) {
      await authStore.checkProfile(user.uid)
    }
    if (!authStore.profileComplete) {
      return '/profile?onboarding=1'
    }
  }
})

export default router
