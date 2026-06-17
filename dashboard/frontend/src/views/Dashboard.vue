<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Dashboard</h1>
      <div class="flex items-center space-x-2">
        <span
          class="w-3 h-3 rounded-full"
          :class="isConnected ? 'bg-success-500' : 'bg-danger-500'"
        ></span>
        <span class="text-sm text-gray-500">
          {{ isConnected ? 'Live' : 'Reconnecting…' }}
        </span>
      </div>
    </div>

    <div
      v-if="floorAlert"
      class="mb-4 p-3 rounded-lg bg-red-100 border border-red-400 text-red-800 flex justify-between items-center"
    >
      <span>{{ floorAlert }}</span>
      <button class="text-sm underline" @click="floorAlert = ''">Dismiss</button>
    </div>
    
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="stat-card">
        <div class="stat-icon bg-primary-100 text-primary-600">
          🖥️
        </div>
        <div>
          <div class="stat-value">{{ stats.total_pcs }}</div>
          <div class="stat-label">Total PCs</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon bg-success-100 text-success-600">
          🟢
        </div>
        <div>
          <div class="stat-value">{{ stats.online_pcs }}</div>
          <div class="stat-label">Online PCs</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon bg-warning-100 text-warning-600">
          ⏰
        </div>
        <div>
          <div class="stat-value">{{ stats.active_sessions }}</div>
          <div class="stat-label">Active Sessions</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon bg-purple-100 text-purple-600">
          💰
        </div>
        <div>
          <div class="stat-value">₦{{ formatNumber(stats.total_revenue_today) }}</div>
          <div class="stat-label">Revenue Today</div>
        </div>
      </div>
    </div>
    
    <!-- PC Status Grid -->
    <div class="card mb-8">
      <h2 class="text-lg font-semibold mb-4">Live Floor Map</h2>
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        <div
          v-for="pc in pcs"
          :key="pc.id"
          class="p-4 rounded-lg text-center cursor-pointer transition-all relative"
          :class="getPCStatusClass(pc)"
          @click="selectPC(pc)"
        >
          <div v-if="pc.is_alarming" class="absolute top-1 right-1 text-red-600 animate-pulse">🚨</div>
          <div class="text-2xl mb-2">🖥️</div>
          <div class="font-medium">{{ pc.name || `PC #${pc.pc_number}` }}</div>
          <div class="text-xs mt-1">{{ getPCStatusText(pc) }}</div>
          <div v-if="pc.time_left != null" class="text-xs mt-1 font-mono" :class="getTimeLeftClass(pc)">
            {{ formatTime(pc.time_left) }}
          </div>
          <div v-if="!pc.client_running && pc.status !== 'offline'" class="text-xs text-yellow-700 mt-1">
            Client down
          </div>
        </div>
      </div>
    </div>
    
    <!-- Recent Sessions -->
    <div class="card">
      <h2 class="text-lg font-semibold mb-4">Recent Sessions</h2>
      <table class="table">
        <thead>
          <tr>
            <th>PC</th>
            <th>Start Time</th>
            <th>Duration</th>
            <th>Status</th>
            <th>Revenue</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="session in recentSessions" :key="session.id">
            <td>PC #{{ session.pc_id }}</td>
            <td>{{ formatDate(session.start_time) }}</td>
            <td>{{ session.duration_minutes }} mins</td>
            <td>
              <span
                class="px-2 py-1 rounded-full text-xs"
                :class="getSessionStatusClass(session.status)"
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
import { ref, watch, onMounted } from 'vue'
import api from '@/services/api'
import { useWebSocket } from '@/composables/useWebSocket'

const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const wsUrl = `${wsProtocol}//${window.location.host}/ws`
const { isConnected, lastMessage, subscribeToPC } = useWebSocket(wsUrl)

const stats = ref({
  total_pcs: 0,
  online_pcs: 0,
  active_sessions: 0,
  total_revenue_today: 0,
})

const pcs = ref([])
const recentSessions = ref([])
const floorAlert = ref('')
const branchId = ref(1)

const fetchDashboardData = async () => {
  try {
    const [statsRes, pcsRes, sessionsRes] = await Promise.all([
      api.get('/api/dashboard/overview', { params: { branch_id: branchId.value } }),
      api.get('/api/pcs/status'),
      api.get('/api/sessions/', { params: { status: 'active' } }),
    ])
    
    stats.value = statsRes.data
    pcs.value = pcsRes.data
    recentSessions.value = sessionsRes.data.slice(0, 10)
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  }
}

const showFloorToast = (message) => {
  floorAlert.value = message
  try {
    const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIGWi77+efTRAMUKfj8LZjHAY4kdfyzHksBSR3x/DdkEAKFF606euoVRQKRp/g8r5sIQUrgc7y2Yk2CBlou+/nn00QDFCn4/C2YxwGOJHX8sx5LAUkd8fw3ZBAC')
    audio.volume = 0.3
    audio.play().catch(() => {})
  } catch (_) {}
}

watch(lastMessage, (newMessage) => {
  if (!newMessage) return
  
  if (newMessage.type === 'pc_status') {
    const pcIndex = pcs.value.findIndex(pc => pc.id === newMessage.pc_id)
    const merged = {
      ...(pcIndex !== -1 ? pcs.value[pcIndex] : { id: newMessage.pc_id }),
      ...newMessage.data,
      status: newMessage.data.status,
      time_left: newMessage.data.time_left,
    }
    if (pcIndex !== -1) {
      const prev = pcs.value[pcIndex]
      if (newMessage.data.is_alarming && !prev.is_alarming) {
        showFloorToast(`Alarm on ${prev.name || 'PC #' + prev.pc_number}`)
      }
      if (newMessage.data.time_left != null && newMessage.data.time_left <= 300 && (prev.time_left == null || prev.time_left > 300)) {
        showFloorToast(`Low time on ${prev.name || 'PC #' + prev.pc_number} (5 min left)`)
      }
      pcs.value[pcIndex] = merged
    } else {
      pcs.value.push(merged)
    }
  } else if (newMessage.type === 'session_update') {
    fetchDashboardData()
  } else if (newMessage.type === 'stats_update') {
    stats.value = { ...stats.value, ...newMessage.data }
  } else if (newMessage.type === 'alarm') {
    showFloorToast(newMessage.message || 'Security alarm triggered')
  }
})

const getPCStatusClass = (pc) => {
  if (pc.is_alarming) return 'bg-red-200 border-2 border-red-600'
  if (!pc.client_running || pc.status === 'offline') return 'bg-gray-200 border-2 border-gray-400'
  if (pc.time_left != null && pc.time_left <= 300) return 'bg-amber-100 border-2 border-amber-500'
  if (pc.status === 'in_use' || pc.has_active_session) return 'bg-warning-100 border-2 border-warning-500'
  if (pc.status === 'online') return 'bg-success-100 border-2 border-success-500'
  return 'bg-gray-100 border-2 border-gray-300'
}

const getPCStatusText = (pc) => {
  if (pc.is_alarming) return 'ALARM'
  if (pc.status === 'offline' || !pc.client_running) return 'Offline'
  if (pc.status === 'in_use' || pc.has_active_session) return 'In Use'
  if (pc.status === 'online') return 'Available'
  return 'Idle'
}

const getTimeLeftClass = (pc) => {
  if (pc.time_left <= 60) return 'text-red-700 font-bold'
  if (pc.time_left <= 300) return 'text-amber-700 font-semibold'
  return 'text-gray-700'
}

const getSessionStatusClass = (status) => {
  const classes = {
    active: 'bg-success-100 text-success-700',
    paused: 'bg-warning-100 text-warning-700',
    completed: 'bg-gray-100 text-gray-700',
    expired: 'bg-danger-100 text-danger-700',
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

const formatNumber = (num) => {
  return (num || 0).toLocaleString()
}

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString()
}

const selectPC = (pc) => {
  subscribeToPC(pc.id)
}

onMounted(() => {
  fetchDashboardData()
})
</script>
