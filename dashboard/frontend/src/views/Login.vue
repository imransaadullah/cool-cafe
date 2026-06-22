<template>
  <div
    class="min-h-screen flex items-center justify-center"
    :style="pageStyle"
  >
    <div class="card w-full max-w-md">
      <div class="text-center mb-8">
        <img
          v-if="brandingStore.branding.logo_url"
          :src="brandingStore.branding.logo_url"
          :alt="brandingStore.branding.display_name"
          class="h-14 mx-auto mb-4 object-contain"
        />
        <h1 class="text-3xl font-bold text-gray-900">{{ brandingStore.branding.display_name }}</h1>
        <p class="text-gray-500 mt-2">
          {{ brandingStore.branding.tagline || 'Management Dashboard' }}
        </p>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useBrandingStore } from '@/stores/branding'

const router = useRouter()
const authStore = useAuthStore()
const brandingStore = useBrandingStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const pageStyle = computed(() => {
  const bg = brandingStore.branding.background
  if (bg?.type === 'image' && bg.image_url) {
    return {
      backgroundImage: `linear-gradient(rgba(0,0,0,0.55), rgba(0,0,0,0.55)), url(${bg.image_url})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }
  }
  return {
    backgroundColor: bg?.color || '#111827',
  }
})

onMounted(() => {
  brandingStore.fetchPublic()
})

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
