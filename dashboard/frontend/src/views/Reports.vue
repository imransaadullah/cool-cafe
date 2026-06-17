<template>
  <div>
    <h1 class="text-2xl font-bold mb-6">Reports</h1>
    
    <!-- Report Type Selector -->
    <div class="card mb-6">
      <div class="flex space-x-4">
        <button
          v-for="type in reportTypes"
          :key="type.value"
          @click="selectedType = type.value"
          class="px-4 py-2 rounded-lg"
          :class="selectedType === type.value ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700'"
        >
          {{ type.label }}
        </button>
      </div>
    </div>
    
    <!-- Date Range -->
    <div class="card mb-6">
      <div class="flex items-center space-x-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Start Date
          </label>
          <input
            v-model="startDate"
            type="date"
            class="input"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            End Date
          </label>
          <input
            v-model="endDate"
            type="date"
            class="input"
          />
        </div>
        <button @click="fetchReports" class="btn btn-primary mt-6">
          Generate Report
        </button>
      </div>
    </div>
    
    <!-- Revenue Summary -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
      <div class="stat-card">
        <div class="stat-icon bg-success-100 text-success-600">
          💰
        </div>
        <div>
          <div class="stat-value">₦{{ formatNumber(totalRevenue) }}</div>
          <div class="stat-label">Total Revenue</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon bg-primary-100 text-primary-600">
          📊
        </div>
        <div>
          <div class="stat-value">{{ totalSessions }}</div>
          <div class="stat-label">Total Sessions</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon bg-warning-100 text-warning-600">
          ⏱️
        </div>
        <div>
          <div class="stat-value">{{ averageDuration }} mins</div>
          <div class="stat-label">Avg Duration</div>
        </div>
      </div>
    </div>
    
    <!-- Reports Table -->
    <div class="card">
      <h2 class="text-lg font-semibold mb-4">Revenue Reports</h2>
      <table class="table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Type</th>
            <th>Revenue</th>
            <th>Sessions</th>
            <th>Codes Used</th>
            <th>Avg Duration</th>
            <th>Generated</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="report in reports" :key="report.id">
            <td>{{ report.report_date }}</td>
            <td>
              <span class="px-2 py-1 rounded-full text-xs bg-primary-100 text-primary-700">
                {{ report.report_type }}
              </span>
            </td>
            <td class="font-semibold">₦{{ formatNumber(report.total_revenue) }}</td>
            <td>{{ report.total_sessions }}</td>
            <td>{{ report.total_codes_used }}</td>
            <td>{{ Math.round(report.average_session_duration) }} mins</td>
            <td>{{ formatDate(report.generated_at) }}</td>
          </tr>
          <tr v-if="reports.length === 0">
            <td colspan="7" class="text-center text-gray-500 py-4">
              No reports found
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'

const reports = ref([])
const selectedType = ref('daily')
const startDate = ref(new Date().toISOString().split('T')[0])
const endDate = ref(new Date().toISOString().split('T')[0])

const reportTypes = [
  { label: 'Daily', value: 'daily' },
  { label: 'Weekly', value: 'weekly' },
  { label: 'Monthly', value: 'monthly' },
]

const totalRevenue = computed(() => {
  return reports.value.reduce((sum, r) => sum + r.total_revenue, 0)
})

const totalSessions = computed(() => {
  return reports.value.reduce((sum, r) => sum + r.total_sessions, 0)
})

const averageDuration = computed(() => {
  if (reports.value.length === 0) return 0
  const total = reports.value.reduce((sum, r) => sum + r.average_session_duration, 0)
  return Math.round(total / reports.value.length)
})

const fetchReports = async () => {
  try {
    await api.post('/api/dashboard/revenue/generate', null, {
      params: {
        branch_id: 1,
        report_date: endDate.value,
      },
    })
    const response = await api.get('/api/dashboard/revenue', {
      params: {
        start_date: startDate.value,
        end_date: endDate.value,
      },
    })
    reports.value = response.data
  } catch (error) {
    console.error('Failed to fetch reports:', error)
  }
}

const formatNumber = (num) => {
  return num.toLocaleString()
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString()
}

onMounted(fetchReports)
</script>
