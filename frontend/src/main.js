import { createApp } from 'vue'
import { createPinia } from 'pinia'
import VueGoogleMaps from '@fawmi/vue-google-maps'
import router from './router'
import App from './App.vue'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(VueGoogleMaps, {
  load: {
    key: import.meta.env.VITE_GOOGLE_MAPS_KEY,
    libraries: 'places'  // Required for GMapAutocomplete in ReportIncidentView.vue
  }
})

app.mount('#app')
