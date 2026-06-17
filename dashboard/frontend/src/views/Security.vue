<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold mb-6">Security Center</h1>

    <!-- Active Alerts -->
    <div class="card mb-8">
      <h2 class="text-lg font-semibold mb-4">Active Alerts</h2>
      <div v-if="alerts.length === 0" class="text-gray-500 py-4">
        No active alerts
      </div>
      <div v-for="alert in alerts" :key="alert.id" class="border-l-4 border-red-500 pl-4 mb-4 p-4 bg-red-50">
        <div class="flex justify-between items-start">
          <div>
            <p class="font-semibold text-red-700">{{ alert.event_type }}</p>
            <p class="text-sm text-gray-600">PC #{{ alert.pc_id }} - {{ alert.details }}</p>
            <p class="text-xs text-gray-500">{{ formatDate(alert.created_at) }}</p>
          </div>
          <div class="flex space-x-2">
            <button
              v-if="alert.event_type === 'alarm_triggered'"
              @click="dismissAlert(alert)"
              class="btn btn-sm bg-green-500 text-white"
            >
              Dismiss
            </button>
            <button
              @click="banPC(alert.pc_id)"
              class="btn btn-sm bg-red-500 text-white"
            >
              Ban PC
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Master Code Generator -->
    <div class="card mb-8">
      <h2 class="text-lg font-semibold mb-4">Master Code Generator</h2>
      <div class="flex items-end space-x-4 mb-4">
        <div class="flex-1">
          <label class="block text-sm font-medium text-gray-700 mb-1">Select PC</label>
          <select v-model="selectedPC" class="input w-full">
            <option value="">Select a PC</option>
            <option v-for="pc in pcs" :key="pc.id" :value="pc.id">
              PC #{{ pc.pc_number }} - {{ pc.name }}
            </option>
          </select>
        </div>
        <div class="w-32">
          <label class="block text-sm font-medium text-gray-700 mb-1">Duration (min)</label>
          <input
            v-model.number="codeDuration"
            type="number"
            class="input w-full"
            min="1"
            max="480"
          />
        </div>
        <button @click="generateCode" class="btn btn-primary">
          Generate Code
        </button>
      </div>

      <!-- Generated Code Display -->
      <div v-if="generatedCode" class="bg-green-50 border border-green-200 p-4 rounded mb-4">
        <p class="text-sm text-green-700">Generated Code:</p>
        <p class="text-2xl font-mono font-bold text-green-800">{{ generatedCode }}</p>
        <p class="text-xs text-green-600">Expires in {{ codeDuration }} minutes</p>
      </div>

      <!-- Recent Codes -->
      <h3 class="font-semibold mb-2">Recent Codes</h3>
      <table class="table w-full">
        <thead>
          <tr>
            <th>Code</th>
            <th>PC</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="code in recentCodes" :key="code.id">
            <td class="font-mono">{{ code.code }}</td>
            <td>PC #{{ code.pc_id }}</td>
            <td>
              <span
                class="px-2 py-1 rounded-full text-xs"
                :class="code.is_used ? 'bg-gray-100 text-gray-700' : 'bg-green-100 text-green-700'"
              >
                {{ code.is_used ? 'Used' : 'Active' }}
              </span>
            </td>
            <td>{{ formatDate(code.created_at) }}</td>
            <td>
              <button
                v-if="!code.is_used"
                @click="revokeCode(code.id)"
                class="text-red-500 hover:text-red-700 text-sm"
              >
                Revoke
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- PC Status -->
    <div class="card mb-8">
      <h2 class="text-lg font-semibold mb-4">PC Security Status</h2>
      <table class="table w-full">
        <thead>
          <tr>
            <th>PC</th>
            <th>Status</th>
            <th>App Running</th>
            <th>Session</th>
            <th>Banned</th>
            <th>Alarm</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pc in pcStatuses" :key="pc.id">
            <td>PC #{{ pc.pc_number }} - {{ pc.name }}</td>
            <td>
              <span
                class="px-2 py-1 rounded-full text-xs"
                :class="getStatusClass(pc)"
              >
                {{ getStatusText(pc) }}
              </span>
            </td>
            <td>
              <span :class="pc.client_running ? 'text-green-600' : 'text-red-600'">
                {{ pc.client_running ? 'Yes' : 'No' }}
              </span>
            </td>
            <td>
              <span v-if="pc.has_active_session" class="text-green-600">
                Active ({{ formatTime(pc.time_left) }} left)
              </span>
              <span v-else class="text-gray-500">None</span>
            </td>
            <td>
              <span :class="pc.is_banned ? 'text-red-600 font-bold' : 'text-gray-500'">
                {{ pc.is_banned ? 'BANNED' : 'No' }}
              </span>
            </td>
            <td>
              <span :class="pc.is_alarming ? 'text-red-600 font-bold' : 'text-gray-500'">
                {{ pc.is_alarming ? 'ACTIVE' : 'No' }}
              </span>
            </td>
            <td>
              <div class="flex space-x-2">
                <button
                  v-if="!pc.is_banned"
                  @click="banPC(pc.id)"
                  class="text-sm px-2 py-1 bg-red-100 text-red-600 rounded"
                >
                  Ban
                </button>
                <button
                  v-else
                  @click="unbanPC(pc.id)"
                  class="text-sm px-2 py-1 bg-green-100 text-green-600 rounded"
                >
                  Unban
                </button>
                <button
                  v-if="pc.is_alarming"
                  @click="resetAlarm(pc.id)"
                  class="text-sm px-2 py-1 bg-yellow-100 text-yellow-600 rounded"
                >
                  Reset Alarm
                </button>
                <button
                  @click="viewRecoveryCombo(pc)"
                  class="text-sm px-2 py-1 bg-blue-100 text-blue-600 rounded"
                >
                  Recovery
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Audit Log -->
    <div class="card">
      <h2 class="text-lg font-semibold mb-4">Audit Log</h2>
      <div class="flex space-x-4 mb-4">
        <select v-model="auditFilter" class="input">
          <option value="">All Events</option>
          <option value="alarm_triggered">Alarms</option>
          <option value="bypass_attempt">Bypass Attempts</option>
          <option value="master_code_used">Master Codes</option>
          <option value="pc_banned">Bans</option>
        </select>
        <button @click="loadAuditLogs" class="btn btn-secondary">Refresh</button>
      </div>
      <table class="table w-full">
        <thead>
          <tr>
            <th>Time</th>
            <th>Event</th>
            <th>PC</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in auditLogs" :key="log.id">
            <td>{{ formatDate(log.created_at) }}</td>
            <td>
              <span
                class="px-2 py-1 rounded-full text-xs"
                :class="getEventClass(log.event_type)"
              >
                {{ log.event_type }}
              </span>
            </td>
            <td>PC #{{ log.pc_id }}</td>
            <td>{{ formatAuditDetails(log.details) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Recovery Combo Modal -->
    <div v-if="showRecoveryModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="card w-full max-w-md">
        <h2 class="text-xl font-semibold mb-4">Recovery Key Combo</h2>
        <div class="text-center">
          <p class="text-gray-600 mb-2">PC #{{ selectedPCForRecovery?.pc_number }}</p>
          <p class="text-3xl font-mono font-bold text-blue-600">
            Alt + {{ selectedPCForRecovery?.recovery_combo || 'Not set' }}
          </p>
          <p class="text-sm text-gray-500 mt-4">
            Press this combination to dismiss alarm on the PC
          </p>
        </div>
        <div class="flex justify-center mt-6">
          <button @click="showRecoveryModal = false" class="btn btn-primary">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const pcs = ref([])
const pcStatuses = ref([])
const alerts = ref([])
const recentCodes = ref([])
const auditLogs = ref([])

const selectedPC = ref('')
const codeDuration = ref(60)
const generatedCode = ref('')
const auditFilter = ref('')
const showRecoveryModal = ref(false)
const selectedPCForRecovery = ref(null)

const fetchPCs = async () => {
  try {
    const response = await api.get('/api/pcs/')
    pcs.value = response.data
  } catch (error) {
    console.error('Failed to fetch PCs:', error)
  }
}

const fetchPCStatuses = async () => {
  try {
    const response = await api.get('/api/pcs/status')
    pcStatuses.value = response.data
  } catch (error) {
    console.error('Failed to fetch PC statuses:', error)
  }
}

const fetchAlerts = async () => {
  try {
    const response = await api.get('/api/security/alerts')
    alerts.value = response.data
  } catch (error) {
    console.error('Failed to fetch alerts:', error)
  }
}

const loadAuditLogs = async () => {
  try {
    const params = auditFilter.value ? { event_type: auditFilter.value } : {}
    const response = await api.get('/api/security/audit-logs', { params })
    auditLogs.value = response.data
  } catch (error) {
    console.error('Failed to fetch audit logs:', error)
  }
}

const generateCode = async () => {
  if (!selectedPC.value) {
    alert('Please select a PC')
    return
  }

  try {
    const response = await api.post('/api/master-codes/generate', {
      pc_id: selectedPC.value,
      duration_minutes: codeDuration.value,
    })
    generatedCode.value = response.data.code
    fetchRecentCodes()
  } catch (error) {
    console.error('Failed to generate code:', error)
  }
}

const fetchRecentCodes = async () => {
  try {
    const response = await api.get('/api/master-codes/')
    recentCodes.value = response.data.slice(0, 10)
  } catch (error) {
    console.error('Failed to fetch codes:', error)
  }
}

const revokeCode = async (codeId) => {
  if (!confirm('Are you sure you want to revoke this code?')) return

  try {
    await api.delete(`/api/master-codes/${codeId}`)
    fetchRecentCodes()
  } catch (error) {
    console.error('Failed to revoke code:', error)
  }
}

const banPC = async (pcId) => {
  const reason = prompt('Enter reason for ban (optional):')
  
  try {
    await api.post(`/api/pcs/${pcId}/ban`, { reason })
    fetchPCStatuses()
    fetchAlerts()
  } catch (error) {
    console.error('Failed to ban PC:', error)
  }
}

const unbanPC = async (pcId) => {
  try {
    await api.post(`/api/pcs/${pcId}/unban`)
    fetchPCStatuses()
  } catch (error) {
    console.error('Failed to unban PC:', error)
  }
}

const resetAlarm = async (pcId) => {
  try {
    await api.post(`/api/pcs/${pcId}/reset-alarm`)
    fetchPCStatuses()
    fetchAlerts()
  } catch (error) {
    console.error('Failed to reset alarm:', error)
  }
}

const dismissAlert = async (alert) => {
  try {
    await api.post('/api/security/dismiss-alert', { alert_id: alert.id })
    fetchAlerts()
    if (alert.pc_id) {
      resetAlarm(alert.pc_id)
    }
  } catch (error) {
    console.error('Failed to dismiss alert:', error)
  }
}

const viewRecoveryCombo = (pc) => {
  selectedPCForRecovery.value = pc
  showRecoveryModal.value = true
}

const getStatusClass = (pc) => {
  if (pc.is_alarming) return 'bg-red-100 text-red-700'
  if (pc.is_banned) return 'bg-orange-100 text-orange-700'
  if (!pc.client_running) return 'bg-yellow-100 text-yellow-700'
  if (pc.has_active_session) return 'bg-green-100 text-green-700'
  return 'bg-gray-100 text-gray-700'
}

const getStatusText = (pc) => {
  if (pc.is_alarming) return 'ALARM'
  if (pc.is_banned) return 'BANNED'
  if (!pc.client_running) return 'APP NOT RUNNING'
  if (pc.has_active_session) return 'ACTIVE'
  return 'IDLE'
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleString()
}

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  return `${mins} min`
}

const formatAuditDetails = (details) => {
  if (!details) return ''
  if (typeof details === 'object') {
    return details.reason || details.method || JSON.stringify(details)
  }
  return String(details)
}

onMounted(() => {
  fetchPCs()
  fetchPCStatuses()
  fetchAlerts()
  fetchRecentCodes()
  loadAuditLogs()
})
</script>
