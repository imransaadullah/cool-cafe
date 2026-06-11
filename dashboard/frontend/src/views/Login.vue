<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-900">
    <div class="card w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900">CyberCafe</h1>
        <p class="text-gray-500 mt-2">Management Dashboard</p>
      </div>
      
      <form @submit.prevent="handleLogin">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Username
          </label>
          <input
            v-model="username"
            type="text"
            class="input"
            placeholder="Enter username"
            required
          />
        </div>
        
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Password
          </label>
          <input
            v-model="password"
            type="password"
            class="input"
            placeholder="Enter password"
            required
          />
        </div>
        
        <div v-if="error" class="mb-4 text-danger-500 text-sm">
          {{ error }}
        </div>
        
        <button
          type="submit"
          class="w-full btn btn-primary"
          :disabled="loading"
        >
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const handleLogin = async () => {
  loading.value = true
  error.value = ''
  
  const success = await authStore.login(username.value, password.value)
  
  if (success) {
    router.push('/')
  } else {
    error.value = 'Invalid username or password'
  }
  
  loading.value = false
}
</script>
