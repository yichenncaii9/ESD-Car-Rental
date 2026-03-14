import { defineStore } from 'pinia'
import { ref } from 'vue'
import { auth } from '../firebase'
import { onAuthStateChanged } from 'firebase/auth'

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref(null)

  onAuthStateChanged(auth, (user) => {
    currentUser.value = user
  })

  return { currentUser }
})
