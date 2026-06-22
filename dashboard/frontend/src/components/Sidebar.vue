<template>
  <div class="sidebar">
    <div class="p-4">
      <img
        v-if="brandingStore.branding.logo_url"
        :src="brandingStore.branding.logo_url"
        :alt="brandingStore.branding.display_name"
        class="h-10 max-w-[180px] object-contain mb-2"
      />
      <h1 class="text-xl font-bold text-white">{{ brandingStore.branding.display_name }}</h1>
      <p class="text-xs text-gray-400">{{ brandingStore.branding.tagline || 'Management System' }}</p>
    </div>
    
    <nav class="mt-4">
      <router-link
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="sidebar-link"
        :class="{ active: $route.path === item.path }"
      >
        <span class="mr-3">{{ item.icon }}</span>
        {{ item.name }}
      </router-link>
    </nav>
    
    <div class="absolute bottom-0 w-full p-4">
      <button
        @click="handleLogout"
        class="w-full px-4 py-2 text-gray-400 hover:text-white transition-colors"
      >
        Logout
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useBrandingStore } from '@/stores/branding'

const router = useRouter()
const authStore = useAuthStore()
const brandingStore = useBrandingStore()

const menuItems = [
  { name: 'Dashboard', path: '/', icon: '📊' },
  { name: 'PCs', path: '/pcs', icon: '🖥️' },
  { name: 'Sessions', path: '/sessions', icon: '⏰' },
  { name: 'Codes', path: '/codes', icon: '🔑' },
  { name: 'Security', path: '/security', icon: '🛡️' },
  { name: 'Reports', path: '/reports', icon: '📈' },
  { name: 'Branches', path: '/branches', icon: '🏢' },
  { name: 'Branding', path: '/branding', icon: '🎨' },
  { name: 'Settings', path: '/settings', icon: '⚙️' },
]

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(async () => {
  try {
    await brandingStore.fetchBranch(1)
  } catch (error) {
    console.error(error)
  }
})
</script>
