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
            :class="getStatusClass(pc.status)"
          >
            {{ pc.status }}
          </span>
        </div>
        
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">IP Address:</span>
            <span>{{ pc.ip_address || 'N/A' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Last Heartbeat:</span>
            <span>{{ formatDate(pc.last_heartbeat_at) }}</span>
          </div>
        </div>
        
        <div class="mt-4 pt-4 border-t flex justify-end space-x-2">
          <button
            @click.stop="toggleStatus(pc)"
            class="text-sm px-3 py-1 rounded"
            :class="pc.is_active ? 'bg-danger-100 text-danger-600' : 'bg-success-100 text-success-600'"
          >
            {{ pc.is_active ? 'Disable' : 'Enable' }}
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const pcs = ref([])
const showAddModal = ref(false)
const editingPC = ref(null)

const formData = ref({
  name: '',
  pc_number: 1,
  branch_id: 1,
  ip_address: '',
  mac_address: '',
})

const fetchPCs = async () => {
  try {
    const response = await api.get('/api/pcs/')
    pcs.value = response.data
  } catch (error) {
    console.error('Failed to fetch PCs:', error)
  }
}

const getStatusClass = (status) => {
  const classes = {
    online: 'bg-success-100 text-success-700',
    in_use: 'bg-warning-100 text-warning-700',
    offline: 'bg-gray-100 text-gray-700',
    maintenance: 'bg-danger-100 text-danger-700',
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
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

const toggleStatus = async (pc) => {
  try {
    await api.put(`/api/pcs/${pc.id}`, { is_active: !pc.is_active })
    fetchPCs()
  } catch (error) {
    console.error('Failed to toggle PC status:', error)
  }
}

onMounted(fetchPCs)
</script>
