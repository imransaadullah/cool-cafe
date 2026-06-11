<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Branch Management</h1>
      <button @click="showAddModal = true" class="btn btn-primary">
        + Add Branch
      </button>
    </div>
    
    <!-- Branch Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
      <div
        v-for="branch in branches"
        :key="branch.id"
        class="card cursor-pointer hover:shadow-lg transition-shadow"
        @click="selectBranch(branch)"
      >
        <div class="flex justify-between items-start mb-4">
          <div>
            <h3 class="font-semibold text-lg">{{ branch.name }}</h3>
            <p class="text-sm text-gray-500">{{ branch.address || 'No address' }}</p>
          </div>
          <span
            class="px-2 py-1 rounded-full text-xs"
            :class="branch.is_active ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-700'"
          >
            {{ branch.is_active ? 'Active' : 'Inactive' }}
          </span>
        </div>
        
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">Phone:</span>
            <span>{{ branch.phone || 'N/A' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Email:</span>
            <span>{{ branch.email || 'N/A' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Last Sync:</span>
            <span>{{ formatDate(branch.last_sync_at) }}</span>
          </div>
        </div>
        
        <div class="mt-4 pt-4 border-t flex justify-end space-x-2">
          <button
            @click.stop="editBranch(branch)"
            class="text-sm px-3 py-1 rounded bg-primary-100 text-primary-600"
          >
            Edit
          </button>
          <button
            @click.stop="manageBranchAdmins(branch)"
            class="text-sm px-3 py-1 rounded bg-warning-100 text-warning-600"
          >
            Admins
          </button>
          <button
            @click.stop="toggleBranchStatus(branch)"
            class="text-sm px-3 py-1 rounded"
            :class="branch.is_active ? 'bg-danger-100 text-danger-600' : 'bg-success-100 text-success-600'"
          >
            {{ branch.is_active ? 'Disable' : 'Enable' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- Add/Edit Branch Modal -->
    <div
      v-if="showAddModal || editingBranch"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="card w-full max-w-md">
        <h2 class="text-xl font-semibold mb-4">
          {{ editingBranch ? 'Edit Branch' : 'Add New Branch' }}
        </h2>
        
        <form @submit.prevent="saveBranch">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Branch Name
            </label>
            <input
              v-model="formData.name"
              type="text"
              class="input"
              placeholder="e.g., Main Branch"
              required
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Address
            </label>
            <input
              v-model="formData.address"
              type="text"
              class="input"
              placeholder="123 Main Street"
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Phone
            </label>
            <input
              v-model="formData.phone"
              type="text"
              class="input"
              placeholder="+234 800 000 0000"
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              v-model="formData.email"
              type="email"
              class="input"
              placeholder="branch@example.com"
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
              {{ editingBranch ? 'Update' : 'Add' }}
            </button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- Admins Modal -->
    <div
      v-if="selectedBranch"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="card w-full max-w-lg max-h-[80vh] overflow-hidden">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-semibold">
            {{ selectedBranch.name }} - Admins
          </h2>
          <button @click="selectedBranch = null" class="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>
        
        <div class="overflow-y-auto max-h-[40vh] mb-4">
          <table class="table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="admin in branchAdmins" :key="admin.id">
                <td>{{ admin.username }}</td>
                <td>{{ admin.email || 'N/A' }}</td>
                <td>
                  <span class="px-2 py-1 rounded-full text-xs bg-primary-100 text-primary-700">
                    {{ admin.role }}
                  </span>
                </td>
                <td>
                  <span
                    class="px-2 py-1 rounded-full text-xs"
                    :class="admin.is_active ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-700'"
                  >
                    {{ admin.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div class="border-t pt-4">
          <h3 class="font-medium mb-2">Add New Admin</h3>
          <form @submit.prevent="createBranchAdmin" class="flex space-x-2">
            <input
              v-model="newAdmin.username"
              type="text"
              class="input"
              placeholder="Username"
              required
            />
            <input
              v-model="newAdmin.email"
              type="email"
              class="input"
              placeholder="Email"
            />
            <input
              v-model="newAdmin.password"
              type="password"
              class="input"
              placeholder="Password"
              required
            />
            <button type="submit" class="btn btn-primary">
              Add
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const branches = ref([])
const branchAdmins = ref([])
const selectedBranch = ref(null)
const showAddModal = ref(false)
const editingBranch = ref(null)

const formData = ref({
  name: '',
  address: '',
  phone: '',
  email: '',
})

const newAdmin = ref({
  username: '',
  email: '',
  password: '',
})

const fetchBranches = async () => {
  try {
    const response = await api.get('/api/branches/')
    branches.value = response.data
  } catch (error) {
    console.error('Failed to fetch branches:', error)
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
}

const selectBranch = (branch) => {
  selectedBranch.value = branch
  fetchBranchAdmins(branch.id)
}

const editBranch = (branch) => {
  editingBranch.value = branch
  formData.value = {
    name: branch.name,
    address: branch.address || '',
    phone: branch.phone || '',
    email: branch.email || '',
  }
}

const closeModal = () => {
  showAddModal.value = false
  editingBranch.value = null
  formData.value = {
    name: '',
    address: '',
    phone: '',
    email: '',
  }
}

const saveBranch = async () => {
  try {
    if (editingBranch.value) {
      await api.put(`/api/branches/${editingBranch.value.id}`, formData.value)
    } else {
      await api.post('/api/branches/', formData.value)
    }
    closeModal()
    fetchBranches()
  } catch (error) {
    console.error('Failed to save branch:', error)
  }
}

const toggleBranchStatus = async (branch) => {
  try {
    await api.put(`/api/branches/${branch.id}`, { is_active: !branch.is_active })
    fetchBranches()
  } catch (error) {
    console.error('Failed to toggle branch status:', error)
  }
}

const fetchBranchAdmins = async (branchId) => {
  try {
    const response = await api.get(`/api/branches/${branchId}/admins`)
    branchAdmins.value = response.data
  } catch (error) {
    console.error('Failed to fetch branch admins:', error)
  }
}

const manageBranchAdmins = (branch) => {
  selectedBranch.value = branch
  fetchBranchAdmins(branch.id)
}

const createBranchAdmin = async () => {
  try {
    await api.post(`/api/branches/${selectedBranch.value.id}/admins`, newAdmin.value)
    newAdmin.value = { username: '', email: '', password: '' }
    fetchBranchAdmins(selectedBranch.value.id)
  } catch (error) {
    console.error('Failed to create admin:', error)
  }
}

onMounted(fetchBranches)
</script>
