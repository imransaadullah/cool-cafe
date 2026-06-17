<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Code Management</h1>
      <button @click="showGenerateModal = true" class="btn btn-primary">
        + Generate Codes
      </button>
    </div>

    <!-- Counter checkout: sell time → code → print -->
    <div class="card mb-8">
      <h2 class="text-lg font-semibold mb-4">Sell Time at Counter</h2>
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Duration (mins)</label>
          <select v-model.number="sellForm.duration_minutes" class="input w-full">
            <option :value="30">30</option>
            <option :value="60">60</option>
            <option :value="90">90</option>
            <option :value="120">120</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Amount (₦)</label>
          <input v-model.number="sellForm.amount" type="number" min="0" class="input w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Payment</label>
          <select v-model="sellForm.method" class="input w-full">
            <option value="cash">Cash</option>
            <option value="transfer">Transfer</option>
            <option value="card">Card</option>
          </select>
        </div>
        <div>
          <button @click="sellTime" class="btn btn-primary w-full" :disabled="selling">
            {{ selling ? 'Processing…' : 'Sell & Issue Code' }}
          </button>
        </div>
        <div v-if="lastSoldCode" class="md:col-span-5 bg-green-50 border border-green-200 rounded p-4 flex justify-between items-center">
          <div>
            <p class="text-sm text-green-700">Code issued — {{ lastSoldCode.duration_minutes }} mins · ₦{{ lastSoldCode.amount }}</p>
            <p class="text-2xl font-mono font-bold text-green-900">{{ lastSoldCode.code }}</p>
            <p class="text-xs text-green-600">Ref: {{ lastSoldCode.payment_reference }}</p>
          </div>
          <button @click="printSoldCode" class="btn btn-secondary">Print Ticket</button>
        </div>
      </div>
    </div>
    
    <!-- Code Batches -->
    <div class="card mb-8">
      <h2 class="text-lg font-semibold mb-4">Code Batches</h2>
      <table class="table">
        <thead>
          <tr>
            <th>Batch ID</th>
            <th>Duration</th>
            <th>Count</th>
            <th>Value</th>
            <th>Printed</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="batch in batches" :key="batch.id">
            <td>{{ batch.id }}</td>
            <td>{{ batch.duration_minutes }} mins</td>
            <td>{{ batch.count }}</td>
            <td>₦{{ batch.value_per_code }}</td>
            <td>
              <span
                class="px-2 py-1 rounded-full text-xs"
                :class="batch.printed ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-700'"
              >
                {{ batch.printed ? 'Yes' : 'No' }}
              </span>
            </td>
            <td>{{ formatDate(batch.created_at) }}</td>
            <td>
              <div class="flex space-x-2">
                <button
                  @click="viewBatchCodes(batch)"
                  class="text-sm px-3 py-1 rounded bg-primary-100 text-primary-600"
                >
                  View Codes
                </button>
                <button
                  v-if="!batch.printed"
                  @click="printBatch(batch)"
                  class="text-sm px-3 py-1 rounded bg-success-100 text-success-600"
                >
                  Print
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="batches.length === 0">
            <td colspan="7" class="text-center text-gray-500 py-4">
              No code batches yet
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Generate Modal -->
    <div
      v-if="showGenerateModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="card w-full max-w-md">
        <h2 class="text-xl font-semibold mb-4">Generate Code Batch</h2>
        
        <form @submit.prevent="generateBatch">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Duration (minutes)
            </label>
            <select v-model="formData.duration_minutes" class="input" required>
              <option :value="30">30 minutes</option>
              <option :value="45">45 minutes</option>
              <option :value="60">1 hour</option>
              <option :value="90">1.5 hours</option>
              <option :value="120">2 hours</option>
              <option :value="180">3 hours</option>
            </select>
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Number of Codes
            </label>
            <input
              v-model.number="formData.count"
              type="number"
              class="input"
              min="1"
              max="1000"
              placeholder="e.g., 50"
              required
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Value per Code (₦)
            </label>
            <input
              v-model.number="formData.value_per_code"
              type="number"
              class="input"
              min="0"
              placeholder="e.g., 100"
              required
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Batch Name (Optional)
            </label>
            <input
              v-model="formData.batch_name"
              type="text"
              class="input"
              placeholder="e.g., Morning Batch"
            />
          </div>
          
          <div class="flex justify-end space-x-2">
            <button
              type="button"
              @click="showGenerateModal = false"
              class="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button type="submit" class="btn btn-primary">
              Generate
            </button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- View Codes Modal -->
    <div
      v-if="selectedBatch"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="card w-full max-w-2xl max-h-[80vh] overflow-hidden">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-semibold">
            Batch #{{ selectedBatch.id }} - Codes
          </h2>
          <button @click="selectedBatch = null" class="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>
        
        <div class="overflow-y-auto max-h-[60vh]">
          <table class="table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Duration</th>
                <th>Status</th>
                <th>Used At</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="code in batchCodes" :key="code.id">
                <td class="font-mono">{{ code.code }}</td>
                <td>{{ code.duration_minutes }} mins</td>
                <td>
                  <span
                    class="px-2 py-1 rounded-full text-xs"
                    :class="code.is_used ? 'bg-gray-100 text-gray-700' : 'bg-success-100 text-success-700'"
                  >
                    {{ code.is_used ? 'Used' : 'Available' }}
                  </span>
                </td>
                <td>{{ code.used_at ? formatDate(code.used_at) : 'N/A' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const batches = ref([])
const batchCodes = ref([])
const selectedBatch = ref(null)
const showGenerateModal = ref(false)
const selling = ref(false)
const lastSoldCode = ref(null)

const sellForm = ref({
  branch_id: 1,
  duration_minutes: 60,
  amount: 500,
  method: 'cash',
})

const formData = ref({
  duration_minutes: 60,
  count: 50,
  value_per_code: 0,
  branch_id: 1,
  batch_name: '',
})

const fetchBatches = async () => {
  try {
    const response = await api.get('/api/codes/batches')
    batches.value = response.data
  } catch (error) {
    console.error('Failed to fetch batches:', error)
  }
}

const sellTime = async () => {
  if (!sellForm.value.amount || sellForm.value.amount <= 0) {
    alert('Enter a valid amount')
    return
  }
  selling.value = true
  try {
    const response = await api.post('/api/codes/sell', sellForm.value)
    lastSoldCode.value = response.data
    fetchBatches()
  } catch (error) {
    console.error('Failed to sell time:', error)
    alert(error.response?.data?.detail || 'Sale failed')
  } finally {
    selling.value = false
  }
}

const printSoldCode = () => {
  if (!lastSoldCode.value) return
  const c = lastSoldCode.value
  const html = `
    <html><head><title>Time Code</title>
    <style>body{font-family:sans-serif;text-align:center;padding:40px}
    .code{font-size:28px;font-weight:bold;letter-spacing:2px;margin:16px 0}
    </style></head><body>
    <h2>Cyber Café Time Ticket</h2>
    <div class="code">${c.code}</div>
    <p>${c.duration_minutes} minutes · ₦${c.amount}</p>
    <p style="font-size:12px;color:#666">Enter this code at any PC</p>
    </body></html>`
  const w = window.open('', '_blank')
  w.document.write(html)
  w.document.close()
  w.print()
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString()
}

const generateBatch = async () => {
  try {
    await api.post('/api/codes/batches', formData.value)
    showGenerateModal.value = false
    formData.value = {
      duration_minutes: 60,
      count: 50,
      value_per_code: 0,
      branch_id: 1,
      batch_name: '',
    }
    fetchBatches()
  } catch (error) {
    console.error('Failed to generate batch:', error)
  }
}

const viewBatchCodes = async (batch) => {
  try {
    selectedBatch.value = batch
    const response = await api.get(`/api/codes/batches/${batch.id}/codes`)
    batchCodes.value = response.data
  } catch (error) {
    console.error('Failed to fetch batch codes:', error)
  }
}

const printBatch = async (batch) => {
  // Generate printable code sheet
  try {
    const response = await api.get(`/api/codes/batches/${batch.id}/codes`)
    const codes = response.data
    
    // Create print content
    let printContent = `
      <html>
      <head>
        <title>Code Batch #${batch.id}</title>
        <style>
          body { font-family: monospace; }
          .code-box { 
            border: 1px solid #000; 
            padding: 10px; 
            margin: 5px; 
            display: inline-block;
            width: 200px;
          }
          .code { font-size: 16px; font-weight: bold; }
          .info { font-size: 12px; color: #666; }
        </style>
      </head>
      <body>
        <h1>Code Batch #${batch.id}</h1>
        <p>Duration: ${batch.duration_minutes} minutes</p>
        <hr/>
    `
    
    codes.forEach((code) => {
      printContent += `
        <div class="code-box">
          <div class="code">${code.code}</div>
          <div class="info">${batch.duration_minutes} mins - ₦${code.value}</div>
        </div>
      `
    })
    
    printContent += `
      </body>
      </html>
    `
    
    // Open print window
    const printWindow = window.open('', '_blank')
    printWindow.document.write(printContent)
    printWindow.document.close()
    printWindow.print()
    
    // Mark as printed
    await api.post(`/api/codes/batches/${batch.id}/print`)
    fetchBatches()
  } catch (error) {
    console.error('Failed to print batch:', error)
  }
}

onMounted(fetchBatches)
</script>
