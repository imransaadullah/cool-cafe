<template>
  <div>
    <h1 class="text-2xl font-bold mb-6">Settings</h1>
    
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Server Settings -->
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">Server Configuration</h2>
        <form @submit.prevent="saveServerSettings">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Server URL
            </label>
            <input
              v-model="serverSettings.url"
              type="text"
              class="input"
              placeholder="http://localhost:8000"
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Heartbeat Interval (seconds)
            </label>
            <input
              v-model.number="serverSettings.heartbeat_interval"
              type="number"
              class="input"
              min="1"
              max="60"
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Deployment Mode
            </label>
            <select v-model="serverSettings.deployment_mode" class="input">
              <option value="local_only">Local Only</option>
              <option value="hybrid">Hybrid (with sync)</option>
              <option value="global_only">Global Server</option>
            </select>
          </div>
          
          <button type="submit" class="btn btn-primary">
            Save Server Settings
          </button>
        </form>
      </div>
      
      <!-- Filter Rules -->
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">Filter Rules</h2>
        <div class="space-y-4">
          <div v-for="rule in filterRules" :key="rule.id" class="flex items-center justify-between p-3 bg-gray-50 rounded">
            <div>
              <div class="font-medium">{{ rule.pattern }}</div>
              <div class="text-sm text-gray-500">
                {{ rule.rule_type }} - {{ rule.action }}
              </div>
            </div>
            <button
              @click="deleteRule(rule)"
              class="text-danger-500 hover:text-danger-700"
            >
              Delete
            </button>
          </div>
          
          <div v-if="filterRules.length === 0" class="text-center text-gray-500 py-4">
            No filter rules configured
          </div>
        </div>
        
        <div class="mt-4 pt-4 border-t">
          <h3 class="font-medium mb-2">Add New Rule</h3>
          <form @submit.prevent="addRule" class="flex space-x-2">
            <select v-model="newRule.rule_type" class="input w-auto">
              <option value="dns">DNS</option>
              <option value="process">Process</option>
              <option value="url">URL</option>
            </select>
            <input
              v-model="newRule.pattern"
              type="text"
              class="input"
              placeholder="Pattern"
              required
            />
            <select v-model="newRule.action" class="input w-auto">
              <option value="block">Block</option>
              <option value="allow">Allow</option>
              <option value="log">Log</option>
            </select>
            <button type="submit" class="btn btn-primary">
              Add
            </button>
          </form>
        </div>
      </div>
      
      <!-- Payment Settings -->
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">Payment Integration</h2>
        <form @submit.prevent="savePaymentSettings">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Paystack Secret Key
            </label>
            <input
              v-model="paymentSettings.paystack_secret"
              type="password"
              class="input"
              placeholder="sk_live_..."
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Paystack Public Key
            </label>
            <input
              v-model="paymentSettings.paystack_public"
              type="text"
              class="input"
              placeholder="pk_live_..."
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Konga Pay Merchant ID
            </label>
            <input
              v-model="paymentSettings.konga_merchant_id"
              type="text"
              class="input"
              placeholder="Merchant ID"
            />
          </div>
          
          <button type="submit" class="btn btn-primary">
            Save Payment Settings
          </button>
        </form>
      </div>
      
      <!-- Branch Settings -->
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">Branch Configuration</h2>
        <form @submit.prevent="saveBranchSettings">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Branch Name
            </label>
            <input
              v-model="branchSettings.name"
              type="text"
              class="input"
              placeholder="e.g., Main Branch"
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Branch Address
            </label>
            <input
              v-model="branchSettings.address"
              type="text"
              class="input"
              placeholder="123 Main Street"
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Contact Phone
            </label>
            <input
              v-model="branchSettings.phone"
              type="text"
              class="input"
              placeholder="+234 800 000 0000"
            />
          </div>

          <div class="mb-4 border-t pt-4">
            <h3 class="font-medium mb-3">Branch-wide App Policy</h3>
            <div class="mb-3">
              <label class="block text-sm font-medium text-gray-700 mb-2">Client mode</label>
              <select v-model="branchAppPolicy.client_mode" class="input">
                <option value="production">Production</option>
                <option value="dev">Development</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="block text-sm font-medium text-gray-700 mb-2">Policy mode</label>
              <select v-model="branchAppPolicy.mode" class="input">
                <option value="blocklist">Blocklist</option>
                <option value="allowlist">Allowlist</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="block text-sm font-medium text-gray-700 mb-2">Allowed apps (one per line)</label>
              <textarea v-model="branchAllowedApps" class="input" rows="3" />
            </div>
            <div class="mb-3">
              <label class="block text-sm font-medium text-gray-700 mb-2">Blocked apps (one per line)</label>
              <textarea v-model="branchBlockedApps" class="input" rows="3" />
            </div>
          </div>
          
          <button type="submit" class="btn btn-primary">
            Save Branch Settings
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const serverSettings = ref({
  url: 'http://localhost:8000',
  heartbeat_interval: 5,
  deployment_mode: 'local_only',
})

const paymentSettings = ref({
  paystack_secret: '',
  paystack_public: '',
  konga_merchant_id: '',
})

const branchSettings = ref({
  name: '',
  address: '',
  phone: '',
})

const branchAppPolicy = ref({
  client_mode: 'production',
  mode: 'blocklist',
  allowed_apps: [],
  blocked_apps: [],
})
const branchAllowedApps = ref('')
const branchBlockedApps = ref('')
const branchId = ref(1)

const filterRules = ref([])
const newRule = ref({
  rule_type: 'dns',
  pattern: '',
  action: 'block',
})

const fetchFilterRules = async () => {
  try {
    const response = await api.get('/api/filters/')
    filterRules.value = response.data
  } catch (error) {
    console.error('Failed to fetch filter rules:', error)
  }
}

const addRule = async () => {
  try {
    await api.post('/api/filters/', newRule.value)
    newRule.value = {
      rule_type: 'dns',
      pattern: '',
      action: 'block',
    }
    fetchFilterRules()
  } catch (error) {
    console.error('Failed to add rule:', error)
  }
}

const deleteRule = async (rule) => {
  if (!confirm('Are you sure you want to delete this rule?')) return
  
  try {
    await api.delete(`/api/filters/${rule.id}`)
    fetchFilterRules()
  } catch (error) {
    console.error('Failed to delete rule:', error)
  }
}

const saveServerSettings = () => {
  localStorage.setItem('serverSettings', JSON.stringify(serverSettings.value))
  alert('Server settings saved!')
}

const savePaymentSettings = () => {
  localStorage.setItem('paymentSettings', JSON.stringify(paymentSettings.value))
  alert('Payment settings saved!')
}

const saveBranchSettings = async () => {
  try {
    await api.put(`/api/branches/${branchId.value}`, branchSettings.value)
    await api.put(`/api/branches/${branchId.value}/app-policy`, {
      client_mode: branchAppPolicy.value.client_mode,
      app_policy: {
        mode: branchAppPolicy.value.mode,
        allowed_apps: branchAllowedApps.value.split('\n').map((s) => s.trim()).filter(Boolean),
        blocked_apps: branchBlockedApps.value.split('\n').map((s) => s.trim()).filter(Boolean),
      },
    })
    alert('Branch settings saved!')
  } catch (error) {
    console.error('Failed to save branch settings:', error)
    alert('Failed to save branch settings')
  }
}

const fetchBranchPolicy = async () => {
  try {
    const response = await api.get(`/api/branches/${branchId.value}/app-policy`)
    const policy = response.data.app_policy || {}
    branchAppPolicy.value = {
      client_mode: response.data.client_mode || 'production',
      mode: policy.mode || 'blocklist',
      allowed_apps: policy.allowed_apps || [],
      blocked_apps: policy.blocked_apps || [],
    }
    branchAllowedApps.value = branchAppPolicy.value.allowed_apps.join('\n')
    branchBlockedApps.value = branchAppPolicy.value.blocked_apps.join('\n')
  } catch (error) {
    console.error('Failed to fetch branch policy:', error)
  }
}

onMounted(() => {
  // Load saved settings
  const savedServer = localStorage.getItem('serverSettings')
  if (savedServer) serverSettings.value = JSON.parse(savedServer)
  
  const savedPayment = localStorage.getItem('paymentSettings')
  if (savedPayment) paymentSettings.value = JSON.parse(savedPayment)
  
  const savedBranch = localStorage.getItem('branchSettings')
  if (savedBranch) branchSettings.value = JSON.parse(savedBranch)
  
  fetchFilterRules()
  fetchBranchPolicy()
})
</script>
