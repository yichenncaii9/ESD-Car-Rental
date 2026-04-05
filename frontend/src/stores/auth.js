import { defineStore } from 'pinia'
import { ref } from 'vue'
import { auth } from '../firebase'
import { onAuthStateChanged } from 'firebase/auth'
import api from '../axios'

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref(null)
  // null = unknown/loading, true = profile exists, false = no profile yet
  const profileComplete = ref(null)

  // Deduplicates concurrent calls — both onAuthStateChanged and the router guard
  // may call this simultaneously; we only ever fire one request.
  let _checkPromise = null

  async function checkProfile(uid) {
    if (profileComplete.value !== null) return
    if (!_checkPromise) {
      _checkPromise = api.get(`/api/drivers/${uid}`)
        .then(() => { profileComplete.value = true })
        .catch(() => { profileComplete.value = false })
    }
    return _checkPromise
  }

  function setProfileComplete(val) {
    profileComplete.value = val
  }

  onAuthStateChanged(auth, (user) => {
    currentUser.value = user
    if (user) {
      checkProfile(user.uid)
    } else {
      profileComplete.value = null
      _checkPromise = null
    }
  })

  return { currentUser, profileComplete, checkProfile, setProfileComplete }
})
