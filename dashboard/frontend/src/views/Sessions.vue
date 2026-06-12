<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Session Management</h1>
      <div class="flex space-x-2">
        <select v-model="statusFilter" class="input w-auto">
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="completed">Completed</option>
          <option value="expired">Expired</option>
        </select>
      </div>
    </div>
    
    <!-- Active Sessions -->
    <div class="card mb-8">
      <h2 class="text-lg font-semibold mb-4">Active Sessions</h2>
      <table class="table">
        <thead>
          <tr>
            <th>PC</th>
            <th>User</th>
            <th>Start Time</th>
            <th>Duration</th>
            <th>Time Left</th>
            <th>Logins Left</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="session in activeSessions" :key="session.id">
            <td>PC #{{ session.pc_id }}</td>
            <td>Code: {{ session.code_id || 'N/A' }}</td>
            <td>{{ formatDate(session.start_time) }}</td>
            <td>{{ session.duration_minutes }} mins</td>
            <td>
              <span class="font-mono" :class="getTimeLeftClass(session)">
                {{ formatTimeLeft(session) }}
              </span>
            </td>
            <td>
              <span v-if="session.status === 'paused'">
                {{ loginQuotaLabel(session) }}
              </span>
              <span v-else class="text-gray-400">—</span>
            </td>
            <td>
              <span
                class="px-2 py-1 rounded-full text-xs"
                :class="getStatusClass(session.status)"
              >
                {{ session.status }}
              </span>
            </td>
            <td>
              <div class="flex space-x-2">
                <button
                  v-if="session.status === 'active'"
                  @click="pauseSession(session)"
                  class="text-sm px-3 py-1 rounded bg-warning-100 text-warning-600"
                >
                  Pause
                </button>
                <button
                  v-if="session.status === 'paused'"
                  @click="resumeSession(session)"
                  class="text-sm px-3 py-1 rounded bg-success-100 text-success-600"
                >
                  Resume
                </button>
                <button
                  @click="stopSession(session)"
                  class="text-sm px-3 py-1 rounded bg-danger-100 text-danger-600"
                >
                  Stop
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="activeSessions.length === 0">
            <td colspan="8" class="text-center text-gray-500 py-4">
              No active sessions
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Session History -->
    <div class="card">
      <h2 class="text-lg font-semibold mb-4">Session History</h2>
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>PC</th>
            <th>Start Time</th>
            <th>End Time</th>
            <th>Duration</th>
            <th>Status</th>
            <th>Revenue</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="session in sessions" :key="session.id">
            <td>{{ session.id }}</td>
            <td>PC #{{ session.pc_id }}</td>
            <td>{{ formatDate(session.start_time) }}</td>
            <td>{{ formatDate(session.end_time) }}</td>
            <td>{{ session.duration_minutes }} mins</td>
            <td>
              <span
                class="px-2 py-1 rounded-full text-xs"
                :class="getStatusClass(session.status)"
              >
                {{ session.status }}
              </span>
            </td>
            <td>₦{{ session.amount_charged }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '@/services/api'

const sessions = ref([])
const statusFilter = ref('')
let refreshInterval = null

const activeSessions = computed(() => {
  return sessions.value.filter(
    (s) => s.status === 'active' || s.status === 'paused'
  )
})

const fetchSessions = async () => {
  try {
    const params = statusFilter.value ? { status: statusFilter.value } : {}
    const response = await api.get('/api/sessions/', { params })
    sessions.value = response.data
  } catch (error) {
    console.error('Failed to fetch sessions:', error)
  }
}

const getStatusClass = (status) => {
  const classes = {
    active: 'bg-success-100 text-success-700',
    paused: 'bg-warning-100 text-warning-700',
    completed: 'bg-gray-100 text-gray-700',
    expired: 'bg-danger-100 text-danger-700',
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

const getTimeLeftClass = (session) => {
  const remaining = getRemainingSeconds(session)
  if (remaining < 300) return 'text-danger-600'
  if (remaining < 900) return 'text-warning-600'
  return 'text-success-600'
}

const getRemainingSeconds = (session) => {
  if (session.status === 'paused' && session.remaining_minutes != null) {
    return session.remaining_minutes * 60
  }
  if (!session.end_time) return 0
  const end = new Date(session.end_time)
  const now = new Date()
  return Math.max(0, (end - now) / 1000)
}

const loginQuotaLabel = (session) => {
  const max = Math.max(1, Math.ceil(session.duration_minutes / 30))
  const used = session.resume_count || 0
  const left = Math.max(0, max - used)
  return `${left} of ${max}`
}

const formatTimeLeft = (session) => {
  const seconds = getRemainingSeconds(session)
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleString()
}

const pauseSession = async (session) => {
  try {
    await api.post('/api/sessions/pause', null, {
      params: { session_id: session.id },
    })
    fetchSessions()
  } catch (error) {
    console.error('Failed to pause session:', error)
  }
}

const resumeSession = async (session) => {
  try {
    await api.post('/api/sessions/resume', null, {
      params: { session_id: session.id },
    })
    fetchSessions()
  } catch (error) {
    console.error('Failed to resume session:', error)
  }
}

const stopSession = async (session) => {
  if (!confirm('Are you sure you want to stop this session?')) return
  
  try {
    await api.post('/api/sessions/stop', null, {
      params: { session_id: session.id },
    })
    fetchSessions()
  } catch (error) {
    console.error('Failed to stop session:', error)
  }
}

onMounted(() => {
  fetchSessions()
  refreshInterval = setInterval(fetchSessions, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>
