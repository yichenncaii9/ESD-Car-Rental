import { createRouter, createWebHistory } from 'vue-router'
import { auth } from '../firebase'
import { onAuthStateChanged } from 'firebase/auth'

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
  { path: '/',                  redirect: '/book-car' },
  { path: '/book-car',          component: () => import('../views/BookCarView.vue'),          meta: { requiresAuth: true } },
  { path: '/cancel-booking',    component: () => import('../views/CancelBookingView.vue'),    meta: { requiresAuth: true } },
  { path: '/report-incident',   component: () => import('../views/ReportIncidentView.vue'),   meta: { requiresAuth: true } },
  { path: '/service-dashboard', component: () => import('../views/ServiceDashboardView.vue'), meta: { requiresAuth: true } }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth && !(await getCurrentUser())) {
    return '/login'
  }
})

export default router
