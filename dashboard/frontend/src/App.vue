<template>
  <div class="min-h-screen bg-gray-100">
    <template v-if="authStore.isAuthenticated">
      <Sidebar />
      <div class="ml-64 p-8">
        <router-view />
      </div>
    </template>
    <template v-else>
      <router-view />
    </template>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Sidebar from '@/components/Sidebar.vue'

const authStore = useAuthStore()

onMounted(() => {
  authStore.loadToken()
})
</script>
