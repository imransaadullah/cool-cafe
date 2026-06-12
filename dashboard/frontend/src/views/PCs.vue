<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">PC Management</h1>
      <button @click="showAddModal = true" class="btn btn-primary">
        + Add PC
      </button>
    </div>
    
    <!-- PC Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div
        v-for="pc in pcs"
        :key="pc.id"
        class="card cursor-pointer hover:shadow-lg transition-shadow"
        @click="editPC(pc)"
      >
        <div class="flex justify-between items-start mb-4">
          <div>
            <h3 class="font-semibold text-lg">{{ pc.name }}</h3>
            <p class="text-sm text-gray-500">PC #{{ pc.pc_number }}</p>
          </div>
          <span
            class="px-2 py-1 rounded-full text-xs"
            :class="getStatusClass(pc)"
          >
            {{ getStatusText(pc) }}
          </span>
        </div>
        
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">IP Address:</span>
            <span>{{ pc.ip_address || 'N/A' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Client Running:</span>
            <span :class="pc.client_running ? 'text-green-600' : 'text-red-600'">
              {{ pc.client_running ? 'Yes' : 'No' }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Ticket:</span>
            <span v-if="pc.session_code" class="font-mono text-sm">
              {{ pc.session_code }}
            </span>
            <span v-else class="text-gray-500">—</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Session:</span>
            <span v-if="pc.has_active_session" :class="sessionClass(pc)">
              {{ sessionLabel(pc) }} ({{ formatTime(pc.time_left) }} left)
            </span>
            <span v-else class="text-gray-500">None</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Banned:</span>
            <span :class="pc.is_banned ? 'text-red-600 font-bold' : 'text-gray-500'">
              {{ pc.is_banned ? 'YES' : 'No' }}
            </span>
          </div>
        </div>
        
        <div class="mt-4 pt-4 border-t flex justify-end space-x-2">
          <button
            v-if="!pc.is_banned"
            @click.stop="banPC(pc)"
            class="text-sm px-3 py-1 rounded bg-red-100 text-red-600"
          >
            Ban
          </button>
          <button
            v-else
            @click.stop="unbanPC(pc)"
            class="text-sm px-3 py-1 rounded bg-green-100 text-green-600"
          >
            Unban
          </button>
          <button
            @click.stop="generateMasterCode(pc)"
            class="text-sm px-3 py-1 rounded bg-blue-100 text-blue-600"
          >
            Generate Code
          </button>
        </div>
      </div>
    </div>
    
    <!-- Add/Edit Modal -->
    <div
      v-if="showAddModal || editingPC"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="card w-full max-w-md">
        <h2 class="text-xl font-semibold mb-4">
          {{ editingPC ? 'Edit PC' : 'Add New PC' }}
        </h2>
        
        <form @submit.prevent="savePC">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              PC Name
            </label>
            <input
              v-model="formData.name"
              type="text"
              class="input"
              placeholder="e.g., PC-01"
              required
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              PC Number
            </label>
            <input
              v-model.number="formData.pc_number"
              type="number"
              class="input"
              placeholder="e.g., 1"
              required
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              IP Address
            </label>
            <input
              v-model="formData.ip_address"
              type="text"
              class="input"
              placeholder="e.g., 192.168.1.100"
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              MAC Address
            </label>
            <input
              v-model="formData.mac_address"
              type="text"
              class="input"
              placeholder="e.g., AA:BB:CC:DD:EE:FF"
            />
          </div>
          
          <div class="flex justify-end space-x-2">
            <button
              type="button"
              @click="closeModal"
              class="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button type="submit" class="btn btn-primary">
              {{ editingPC ? 'Update' : 'Add' }}
            </button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- Master Code Modal -->
    <div
      v-if="showMasterCodeModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="card w-full max-w-md">
        <h2 class="text-xl font-semibold mb-4">Generate Master Code</h2>
        
        <div class="mb-4">
          <p class="text-gray-600 mb-2">PC #{{ selectedPCForCode?.pc_number }} - {{ selectedPCForCode?.name }}</p>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Duration (minutes)
          </label>
          <input
            v-model.number="codeDuration"
            type="number"
            class="input"
            min="1"
            max="480"
          />
        </div>
        
        <div v-if="generatedCode" class="bg-green-50 border border-green-200 p-4 rounded mb-4">
          <p class="text-sm text-green-700">Generated Code:</p>
          <p class="text-2xl font-mono font-bold text-green-800">{{ generatedCode }}</p>
          <p class="text-xs text-green-600">Expires in {{ codeDuration }} minutes</p>
        </div>
        
        <div class="flex justify-end space-x-2">
          <button
            type="button"
            @click="showMasterCodeModal = false"
            class="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            Close
          </button>
          <button
            v-if="!generatedCode"
            @click="generateCode"
            class="btn btn-primary"
          >
            Generate
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
const showAddModal = ref(false)
const editingPC = ref(null)
const showMasterCodeModal = ref(false)
const selectedPCForCode = ref(null)
const codeDuration = ref(60)
const generatedCode = ref('')

const formData = ref({
  name: '',
  pc_number: 1,
  branch_id: 1,
  ip_address: '',
  mac_address: '',
})

const fetchPCs = async () => {
  try {
    const response = await api.get('/api/pcs/status')
    pcs.value = response.data
  } catch (error) {
    console.error('Failed to fetch PCs:', error)
  }
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
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
}

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  return `${mins} min`
}

const sessionLabel = (pc) => {
  if (pc.session_status === 'paused') return 'Paused'
  return 'Active'
}

const sessionClass = (pc) => {
  if (pc.session_status === 'paused') return 'text-amber-600'
  return 'text-green-600'
}

const editPC = (pc) => {
  editingPC.value = pc
  formData.value = { ...pc }
}

const closeModal = () => {
  showAddModal.value = false
  editingPC.value = null
  formData.value = {
    name: '',
    pc_number: 1,
    branch_id: 1,
    ip_address: '',
    mac_address: '',
  }
}

const savePC = async () => {
  try {
    if (editingPC.value) {
      await api.put(`/api/pcs/${editingPC.value.id}`, formData.value)
    } else {
      await api.post('/api/pcs/', formData.value)
    }
    closeModal()
    fetchPCs()
  } catch (error) {
    console.error('Failed to save PC:', error)
  }
}

const banPC = async (pc) => {
  const reason = prompt('Enter reason for ban (optional):')
  
  try {
    await api.post(`/api/pcs/${pc.id}/ban`, { reason })
    fetchPCs()
  } catch (error) {
    console.error('Failed to ban PC:', error)
  }
}

const unbanPC = async (pc) => {
  try {
    await api.post(`/api/pcs/${pc.id}/unban`)
    fetchPCs()
  } catch (error) {
    console.error('Failed to unban PC:', error)
  }
}

const generateMasterCode = (pc) => {
  selectedPCForCode.value = pc
  codeDuration.value = 60
  generatedCode.value = ''
  showMasterCodeModal.value = true
}

const generateCode = async () => {
  try {
    const response = await api.post('/api/master-codes/generate', {
      pc_id: selectedPCForCode.value.id,
      duration_minutes: codeDuration.value,
    })
    generatedCode.value = response.data.code
  } catch (error) {
    console.error('Failed to generate code:', error)
  }
}

onMounted(fetchPCs)
</script>
