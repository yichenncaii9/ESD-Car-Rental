<template>
  <div class="view-container">
    <div class="header-row">
      <h1>Service Dashboard</h1>
      <span class="ws-status" :class="wsConnected ? 'connected' : 'disconnected'">
        <span class="ws-status-dot" aria-hidden="true"></span>
        {{ wsConnected ? 'Live' : 'Connecting...' }}
      </span>
    </div>

    <p class="subtitle">Pending incident reports requiring service team attention.</p>

    <!-- Diagnostic panel -->
    <div class="diag-panel">
      <div class="diag-row">
        <span class="diag-label">Socket.IO</span>
        <span :class="['diag-val', wsConnected ? 'ok' : 'err']">
          {{ wsConnected ? `Connected (${socketId})` : 'Not connected' }}
        </span>
      </div>
      <div class="diag-row">
        <span class="diag-label">Last event</span>
        <span class="diag-val" style="font-family:monospace;font-size:0.78rem">
          {{ lastEvent || '—' }}
        </span>
      </div>
      <div v-if="eventLog.length > 0" class="diag-row event-log-row">
        <span class="diag-label">Event log</span>
        <ul class="event-log">
          <li v-for="(e, i) in eventLog" :key="i">{{ e }}</li>
        </ul>
      </div>
    </div>

    <div v-if="reports.length > 0" class="table-container">
      <table>
        <thead>
          <tr>
            <th>Report ID</th>
            <th>Vehicle</th>
            <th>Location</th>
            <th>Severity</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="report in reports"
            :key="report.id"
            :class="[severityClass(report.severity), report._flash ? 'flash' : '']"
          >
            <td class="mono">{{ report.id }}</td>
            <td>{{ report.vehicle_id || '—' }}</td>
            <td class="location-cell">{{ report.location || formatCoords(report) }}</td>
            <td>
              <span class="severity-badge" :class="severityClass(report.severity)">
                {{ report.severity || 'pending' }}
              </span>
            </td>
            <td>{{ report.status || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="empty-state">
      <p>No pending reports.</p>
    </div>

    <p class="update-hint">Updates appear automatically via real-time connection to websocket_server.</p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { io } from 'socket.io-client'
import api from '../axios'

const reports     = ref([])
const wsConnected = ref(false)
const socketId    = ref('')
const lastEvent   = ref('')
const eventLog    = ref([])   // last 5 raw events
let socket = null

function formatCoords(report) {
  if (report.lat && report.lng) return `${report.lat.toFixed(4)}, ${report.lng.toFixed(4)}`
  return '—'
}

function severityClass(severity) {
  const map = { high: 'sev-high', medium: 'sev-medium', low: 'sev-low' }
  return map[severity] || ''
}

function logEvent(data) {
  const ts = new Date().toLocaleTimeString()
  const summary = `[${ts}] report_id=${data.report_id ?? data.id ?? '?'} event=${data.event ?? '?'} severity=${data.severity ?? '?'}`
  lastEvent.value = summary
  eventLog.value = [summary, ...eventLog.value].slice(0, 5)
}

function flashRow(id) {
  const idx = reports.value.findIndex(r => r.id === id)
  if (idx < 0) return
  reports.value[idx] = { ...reports.value[idx], _flash: true }
  setTimeout(() => {
    const i = reports.value.findIndex(r => r.id === id)
    if (i >= 0) reports.value[i] = { ...reports.value[i], _flash: false }
  }, 1500)
}

onMounted(async () => {
  // Fetch initial pending reports
  try {
    const res = await api.get('/api/reports/pending')
    const data = res.data.data || res.data.reports || []
    reports.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('Failed to load pending reports:', err)
  }

  // Connect Socket.IO to websocket_server
  socket = io('http://localhost:6100', {
    transports: ['websocket'],
    reconnection: true
  })

  socket.on('connect', () => {
    wsConnected.value = true
    socketId.value = socket.id
    console.log('ServiceDashboard: Socket.IO connected', socket.id)
  })

  socket.on('connect_error', (err) => {
    console.error('ServiceDashboard: Socket.IO connect error', err.message)
  })

  socket.on('disconnect', (reason) => {
    wsConnected.value = false
    socketId.value = ''
    console.warn('ServiceDashboard: Socket.IO disconnected', reason)
  })

  socket.on('report_update', (data) => {
    logEvent(data)
    const reportId = data.id || data.report_id
    const idx = reports.value.findIndex(r => r.id === reportId)
    if (idx >= 0) {
      reports.value[idx] = { ...reports.value[idx], ...data, _flash: false }
      flashRow(reportId)
    } else {
      reports.value.unshift({ ...data, id: reportId, _flash: true })
      setTimeout(() => {
        const i = reports.value.findIndex(r => r.id === reportId)
        if (i >= 0) reports.value[i] = { ...reports.value[i], _flash: false }
      }, 1500)
    }
  })
})

onUnmounted(() => {
  if (socket) {
    socket.disconnect()
    socket = null
  }
})
</script>

<style scoped>
.view-container { max-width: 1000px; margin: 0 auto; padding-bottom: 48px; }

/* ── HEADER ROW ──────────────────────────────────────────── */
.header-row {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 4px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--c-border);
  margin-bottom: 20px;
}
h1 { font-size: 26px; font-weight: 800; color: var(--c-dark); letter-spacing: -0.4px; }

.ws-status {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 9999px;
  font-size: 12px; font-weight: 700; margin-left: auto;
}
.ws-status-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.ws-status.connected    { background: var(--c-success-bg); color: var(--c-success); }
.ws-status.disconnected { background: var(--c-error-bg);   color: var(--c-error); }
.ws-status.connected .ws-status-dot { background: var(--c-success); animation: pulse 1.5s ease-in-out infinite; }
.ws-status.disconnected .ws-status-dot { background: var(--c-error); }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.35;} }

.subtitle { color: var(--c-muted); margin-bottom: 20px; font-size: 14px; }

/* ── DIAG PANEL ──────────────────────────────────────────── */
.diag-panel {
  background: #f8faff;
  border: 1px solid #e0e7ff;
  border-left: 3px solid #818cf8;
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  margin-bottom: 20px;
  font-size: 13px;
}
.diag-row { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 5px; }
.diag-row:last-child { margin-bottom: 0; }
.diag-label { color: var(--c-muted); width: 80px; flex-shrink: 0; font-weight: 600; font-size: 12px; padding-top: 1px; }
.diag-val { color: var(--c-dark); }
.diag-val.ok      { color: var(--c-success); font-weight: 600; }
.diag-val.err     { color: var(--c-error);   font-weight: 600; }
.diag-val.pending { color: var(--c-warn); }
.event-log-row { align-items: flex-start; }
.event-log { margin:0; padding:0; list-style:none; font-family:'Courier New',monospace; font-size:11px; color:var(--c-dark); }
.event-log li+li { margin-top: 2px; }

/* ── TABLE ───────────────────────────────────────────────── */
.table-container {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}
table { width: 100%; border-collapse: collapse; }
th {
  background: var(--c-primary);
  color: rgba(255,255,255,0.7);
  padding: 11px 16px;
  text-align: left;
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.7px;
}
th:first-child { color: #fff; }
td { padding: 13px 16px; border-bottom: 1px solid var(--c-border); font-size: 14px; color: var(--c-dark); }
tr:last-child td { border-bottom: none; }
tbody tr { transition: background 0.1s; }
tbody tr:hover { background: #f8fafc; }
tr.sev-high   td { border-left: 3px solid var(--c-error);   }
tr.sev-medium td { border-left: 3px solid #f59e0b; }
tr.sev-high   td:not(:first-child) { border-left: none; }
tr.sev-medium td:not(:first-child) { border-left: none; }
tr.flash { animation: flash-in 1.5s ease-out; }
@keyframes flash-in { 0%{background:#bbf7d0;} 100%{background:transparent;} }

.location-cell { max-width: 200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.mono { font-family:'Courier New',monospace; font-size:12px; color: var(--c-muted); }

.severity-badge {
  display: inline-block; padding: 3px 10px;
  border-radius: 9999px; font-size: 11px; font-weight: 700;
}
.severity-badge.sev-high   { background: var(--c-error-bg);   color: var(--c-error); }
.severity-badge.sev-medium { background: var(--c-warn-bg);    color: var(--c-warn); }
.severity-badge.sev-low    { background: var(--c-success-bg); color: var(--c-success); }

.empty-state {
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius); padding: 64px; text-align: center;
  box-shadow: var(--shadow); color: var(--c-muted); font-size: 14px;
}
.update-hint { margin-top: 14px; font-size: 12px; color: var(--c-muted); }
</style>
