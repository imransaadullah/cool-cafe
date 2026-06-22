import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

const DEFAULTS = {
  display_name: 'Cyber Cafe',
  tagline: '',
  accent_color: '#e94560',
  background: {
    type: 'color',
    color: '#1a1a2e',
    overlay_opacity: 0.45,
    image_url: null,
  },
  logo_url: null,
  logo_client_url: null,
}

export const useBrandingStore = defineStore('branding', () => {
  const branding = ref({ ...DEFAULTS })
  const branchId = ref(1)
  const loaded = ref(false)

  function applyCssVariables() {
    const root = document.documentElement
    const accent = branding.value.accent_color || DEFAULTS.accent_color
    root.style.setProperty('--brand-accent', accent)
    root.style.setProperty('--brand-bg', branding.value.background?.color || DEFAULTS.background.color)
    root.style.setProperty('--brand-name', `"${branding.value.display_name || DEFAULTS.display_name}"`)
  }

  async function fetchPublic() {
    try {
      const response = await api.get('/api/branches/public/branding')
      branding.value = { ...DEFAULTS, ...response.data }
      applyCssVariables()
      loaded.value = true
    } catch (error) {
      console.error('Failed to load public branding:', error)
      branding.value = { ...DEFAULTS }
      applyCssVariables()
    }
  }

  async function fetchBranch(id = branchId.value) {
    branchId.value = id
    try {
      const response = await api.get(`/api/branches/${id}/branding`)
      branding.value = { ...DEFAULTS, ...response.data }
      applyCssVariables()
      loaded.value = true
      return branding.value
    } catch (error) {
      console.error('Failed to load branch branding:', error)
      throw error
    }
  }

  async function saveSettings(payload) {
    const response = await api.put(`/api/branches/${branchId.value}/branding`, payload)
    branding.value = { ...DEFAULTS, ...response.data }
    applyCssVariables()
    return branding.value
  }

  async function uploadLogo(file, clientVariant = false) {
    const form = new FormData()
    form.append('file', file)
    const path = clientVariant
      ? `/api/branches/${branchId.value}/branding/logo-client`
      : `/api/branches/${branchId.value}/branding/logo`
    const response = await api.post(path, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await fetchBranch(branchId.value)
    return response.data
  }

  async function uploadBackground(file) {
    const form = new FormData()
    form.append('file', file)
    await api.post(`/api/branches/${branchId.value}/branding/background`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await fetchBranch(branchId.value)
  }

  async function removeLogo(clientVariant = false) {
    const path = clientVariant
      ? `/api/branches/${branchId.value}/branding/logo-client`
      : `/api/branches/${branchId.value}/branding/logo`
    await api.delete(path)
    await fetchBranch(branchId.value)
  }

  async function removeBackground() {
    await api.delete(`/api/branches/${branchId.value}/branding/background`)
    await fetchBranch(branchId.value)
  }

  return {
    branding,
    branchId,
    loaded,
    fetchPublic,
    fetchBranch,
    saveSettings,
    uploadLogo,
    uploadBackground,
    removeLogo,
    removeBackground,
    applyCssVariables,
  }
})
