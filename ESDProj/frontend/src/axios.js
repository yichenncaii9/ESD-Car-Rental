import axios from 'axios'
import { auth } from './firebase'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
})

api.interceptors.request.use(async (config) => {
  const user = auth.currentUser
  if (user) {
    const token = await user.getIdToken()  // auto-refreshes; do NOT use getIdToken(true) on every request
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api
