<template>
  <div class="view-container">
    <div class="header-row">
      <h1>Service Dashboard</h1>
      <span class="ws-status" :class="wsConnected ? 'connected' : 'disconnected'">
        {{ wsConnected ? 'Live' : 'Connecting...' }}
      </span>
    </div>

    <p class="subtitle">Pending incident reports requiring service team attention.</p>

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
            :class="severityClass(report.severity)"
          >
            <td class="mono">{{ report.id }}</td>
            <td>{{ report.vehicle_id || '—' }}</td>
            <td class="location-cell">{{ report.location || formatCoords(report) }}</td>
            <td>
              <span class="severity-badge" :class="severityClass(report.severity)">
                {{ report.severity || 'pending' }}
              </span>
            </td>
            <td>{{ report.status }}</td>
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
let socket = null

function formatCoords(report) {
  if (report.lat && report.lng) return `${report.lat.toFixed(4)}, ${report.lng.toFixed(4)}`
  return '—'
}

function severityClass(severity) {
  const map = { high: 'sev-high', medium: 'sev-medium', low: 'sev-low' }
  return map[severity] || ''
}

onMounted(async () => {
  // Fetch initial pending reports
  try {
    const res = await api.get('/api/reports/pending')
    reports.value = res.data.reports || res.data || []
  } catch (err) {
    console.error('Failed to load pending reports:', err.message)
  }

  // Connect Socket.IO to websocket_server
  // Event name 'report_update' — Phase 5 websocket_server MUST emit this exact name
  socket = io('http://localhost:6100', {
    transports: ['websocket'],
    reconnection: true
  })

  socket.on('connect', () => {
    wsConnected.value = true
    console.log('ServiceDashboard: Socket.IO connected to websocket_server')
  })

  socket.on('disconnect', () => {
    wsConnected.value = false
  })

  socket.on('report_update', (data) => {
    // Update existing report or prepend new one
    const idx = reports.value.findIndex(r => r.id === data.report_id || r.id === data.id)
    if (idx >= 0) {
      reports.value[idx] = { ...reports.value[idx], ...data }
    } else {
      reports.value.unshift(data)
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
.view-container { max-width: 1000px; margin: 0 auto; }
.header-row { display: flex; align-items: center; gap: 16px; margin-bottom: 8px; }
h1 { color: #1a1a2e; }
.ws-status { padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
.ws-status.connected { background: #d4edda; color: #155724; }
.ws-status.disconnected { background: #f8d7da; color: #721c24; }
.subtitle { color: #666; margin-bottom: 24px; font-size: 0.95rem; }
.table-container { background: white; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #1a1a2e; color: white; padding: 12px 16px; text-align: left; font-size: 0.85rem; font-weight: 600; }
td { padding: 12px 16px; border-bottom: 1px solid #eee; font-size: 0.9rem; }
tr:last-child td { border-bottom: none; }
tr.sev-high { background: #fff5f5; }
tr.sev-medium { background: #fffbf0; }
.location-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mono { font-family: monospace; font-size: 0.85rem; }
.severity-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.severity-badge.sev-high { background: #fde8e8; color: #c53030; }
.severity-badge.sev-medium { background: #fef3c7; color: #92400e; }
.severity-badge.sev-low { background: #d1fae5; color: #065f46; }
.empty-state { background: white; padding: 48px; text-align: center; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); color: #999; }
.update-hint { margin-top: 12px; font-size: 0.8rem; color: #aaa; }
</style>
