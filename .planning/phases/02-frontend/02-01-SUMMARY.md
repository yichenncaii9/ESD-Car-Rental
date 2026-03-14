---
phase: 02-frontend
plan: "01"
subsystem: ui
tags: [vue3, vite, firebase, pinia, vue-router, axios, nginx, docker]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: docker-compose.yml skeleton, Kong proxy on port 8000, CORS for localhost:8080
provides:
  - Vue 3 Vite project with all core infrastructure modules
  - firebase.js singleton (app + auth exports)
  - axios.js Axios instance with Firebase JWT interceptor
  - router/index.js with 6 routes + requiresAuth guard using onAuthStateChanged promise
  - stores/auth.js Pinia auth store tracking currentUser
  - NavBar.vue hidden on /login via v-if on currentUser
  - Multi-stage Dockerfile (node:20-alpine build + nginx:stable-alpine serve on 8080)
  - nginx.conf with SPA fallback (try_files)
  - docker-compose.yml frontend service updated with VITE_* build args
affects:
  - 02-02 (LoginView depends on firebase.js, router, auth store)
  - 02-03 (BookCar and CancelBooking views depend on axios.js, router, NavBar)
  - 02-04 (ReportIncident and ServiceDashboard views depend on all core modules)

# Tech tracking
tech-stack:
  added:
    - vue@3.4
    - vite@5 with @vitejs/plugin-vue
    - firebase@10 (Firebase JS SDK v9 modular)
    - axios@1.7
    - vue-router@4
    - pinia@2
    - socket.io-client@4
    - "@fawmi/vue-google-maps@0.9"
    - nginx:stable-alpine (frontend container)
  patterns:
    - Firebase singleton pattern (never re-initialize per component)
    - Axios interceptor pattern for JWT attachment
    - onAuthStateChanged promise pattern for router guard (avoids race condition on page refresh)
    - Pinia composition store pattern (setup stores)
    - Multi-stage Docker build (node build + nginx serve)
    - VITE_* env vars as ARG/ENV in Dockerfile (baked at build time, not runtime-injectable)

key-files:
  created:
    - frontend/package.json
    - frontend/vite.config.js
    - frontend/index.html
    - frontend/.env.example
    - frontend/src/firebase.js
    - frontend/src/axios.js
    - frontend/src/router/index.js
    - frontend/src/stores/auth.js
    - frontend/src/components/NavBar.vue
    - frontend/src/App.vue
    - frontend/src/main.js
    - frontend/src/views/LoginView.vue
    - frontend/src/views/BookCarView.vue
    - frontend/src/views/CancelBookingView.vue
    - frontend/src/views/ReportIncidentView.vue
    - frontend/src/views/ServiceDashboardView.vue
    - frontend/nginx.conf
  modified:
    - frontend/Dockerfile (replaced Phase 1 placeholder with multi-stage build)
    - docker-compose.yml (frontend service updated with build.args for all 8 VITE_* vars)

key-decisions:
  - "VITE_* vars passed as Docker build ARGs (not runtime env) — Vite bakes them statically into the JS bundle"
  - "axios.js baseURL uses VITE_API_BASE_URL || http://localhost:8000 — all view calls use full /api/* paths"
  - "Router guard uses onAuthStateChanged promise (not auth.currentUser directly) to avoid race condition on page refresh"
  - "NavBar hidden on /login via v-if on authStore.currentUser — not via route meta"
  - "vue-google-maps loaded with libraries:'places' in main.js — required for GMapAutocomplete in ReportIncidentView"
  - "npm create vite interactive prompt cancelled in non-TTY — manually created package.json and index.html instead (Rule 3 deviation)"

patterns-established:
  - "Firebase singleton: import { auth } from './firebase' — never call initializeApp per component"
  - "API calls: import api from './axios' then api.get('/api/resource') — full path with /api/ prefix"
  - "Auth guard: onAuthStateChanged promise in getCurrentUser() wrapper — resolves once then unsubscribes"

requirements-completed: [FE-01, FE-03, FE-04, FE-06]

# Metrics
duration: 4min
completed: 2026-03-14
---

# Phase 2 Plan 01: Vue 3 Frontend Infrastructure Summary

**Vue 3 Vite app scaffolded with Firebase singleton, Axios JWT interceptor, Pinia auth store, Vue Router with auth guard, NavBar component, multi-stage Dockerfile, and nginx SPA config wired into docker-compose**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-14T06:26:29Z
- **Completed:** 2026-03-14T06:30:41Z
- **Tasks:** 3
- **Files modified:** 18

## Accomplishments

- Complete Vue 3 Vite project skeleton with 7 required npm dependencies installed
- Core shared modules: firebase.js singleton, axios.js JWT interceptor, router with 6 routes + auth guard, Pinia auth store, NavBar
- Multi-stage Dockerfile (node:20-alpine build, nginx:stable-alpine serve) with all 8 VITE_* ARG/ENV vars declared
- docker-compose.yml frontend service updated to pass VITE_* build args from .env file

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Vue 3 Vite project + install dependencies** - `17575a0` (feat)
2. **Task 2: Create core modules — firebase.js, axios.js, router, auth store, NavBar** - `7d82dc5` (feat)
3. **Task 3: Multi-stage Dockerfile, nginx.conf, docker-compose.yml build args** - `5ab232e` (feat)

## Files Created/Modified

- `frontend/package.json` - Vue 3 project with firebase, axios, vue-router, pinia, socket.io-client, @fawmi/vue-google-maps
- `frontend/vite.config.js` - Vite config with optimizeDeps for vue-google-maps, dev server on port 8080
- `frontend/index.html` - SPA entry point mounting #app
- `frontend/.env.example` - Documents all 8 VITE_* keys required by this phase
- `frontend/src/firebase.js` - Firebase app + auth singleton using VITE_* env vars
- `frontend/src/axios.js` - Axios instance with baseURL=localhost:8000 and JWT interceptor
- `frontend/src/router/index.js` - 6 routes with requiresAuth guard using onAuthStateChanged promise
- `frontend/src/stores/auth.js` - Pinia auth store with currentUser ref via onAuthStateChanged
- `frontend/src/components/NavBar.vue` - Nav with links, user email, logout; hidden when not authenticated
- `frontend/src/App.vue` - Root component with NavBar + RouterView
- `frontend/src/main.js` - App entry registering Pinia, router, VueGoogleMaps with libraries:'places'
- `frontend/src/views/*.vue` - 5 placeholder views (Login, BookCar, CancelBooking, ReportIncident, ServiceDashboard)
- `frontend/Dockerfile` - Multi-stage: node:20-alpine build + nginx:stable-alpine serve on 8080
- `frontend/nginx.conf` - SPA fallback with try_files $uri $uri/ /index.html
- `docker-compose.yml` - Frontend service updated with build.args for all 8 VITE_* vars

## Decisions Made

- VITE_* vars are ARG/ENV in Dockerfile — Vite bakes them statically into the JS bundle; they cannot be injected at container runtime
- axios.js uses `getIdToken()` not `getIdToken(true)` — avoids forcing token refresh on every request
- Router guard uses onAuthStateChanged promise wrapper — avoids race condition where auth.currentUser is null before Firebase initializes on page refresh
- NavBar uses `v-if="authStore.currentUser"` — hidden naturally on /login since user is unauthenticated there

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Manually scaffolded Vite project instead of using `npm create vite`**
- **Found during:** Task 1 (Scaffold Vue 3 Vite project)
- **Issue:** `npm create vite@latest . -- --template vue` cancelled immediately in non-TTY environment — the interactive "overwrite files?" prompt could not be confirmed
- **Fix:** Manually created package.json, index.html, and vite.config.js following Vite's Vue template structure, then ran `npm install`
- **Files modified:** frontend/package.json, frontend/index.html, frontend/vite.config.js
- **Verification:** All required dependencies present in package.json; vite.config.js has optimizeDeps block
- **Committed in:** 17575a0 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** Functionally equivalent outcome — same file structure and dependencies as npm create vite would have generated. No scope creep.

## Issues Encountered

- `npm create vite` non-interactive mode not supported in this version — workaround was manual file creation (see deviation above)

## User Setup Required

Firebase and Google Maps API keys are required at Docker build time:

- `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_STORAGE_BUCKET`, `VITE_FIREBASE_MESSAGING_SENDER_ID`, `VITE_FIREBASE_APP_ID` — from Firebase Console -> Project Settings -> Your apps -> Web app SDK snippet
- `VITE_GOOGLE_MAPS_KEY` — from Google Cloud Console -> APIs & Services -> Credentials (Maps JS API + Places API enabled)
- `VITE_API_BASE_URL` — defaults to http://localhost:8000 if not set

Add these to the root `.env` file (template already appended to `.env` by this plan).

## Next Phase Readiness

- All shared modules exist and are importable by view plans (02-02 through 02-04)
- Placeholder views prevent router import errors during development
- Firebase singleton ready for LoginView authentication (Plan 02-02)
- Axios JWT interceptor ready for all authenticated API calls
- Docker build ready once VITE_* keys are populated in .env

## Self-Check: PASSED

All 13 key files verified present. All 3 task commits verified in git log.

---
*Phase: 02-frontend*
*Completed: 2026-03-14*
