import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(null)
  const user = ref(null)

  const isAuthenticated = computed(() => !!token.value)

  function loadToken() {
    const savedToken = localStorage.getItem('token')
    if (savedToken) {
      token.value = savedToken
      fetchUser()
    }
  }

  async function login(username, password) {
    try {
      const response = await api.post('/api/auth/login', {
        username,
        password,
      })
      token.value = response.data.access_token
      localStorage.setItem('token', token.value)
      await fetchUser()
      return true
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }

  async function fetchUser() {
    try {
      const response = await api.get('/api/auth/me', {
        params: { username: 'admin' },
      })
      user.value = response.data
    } catch (error) {
      console.error('Failed to fetch user:', error)
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    isAuthenticated,
    loadToken,
    login,
    logout,
    fetchUser,
  }
})
