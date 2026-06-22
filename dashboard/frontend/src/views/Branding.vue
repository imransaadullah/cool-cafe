<template>
  <div>
    <h1 class="text-2xl font-bold mb-2">Branding</h1>
    <p class="text-gray-600 mb-6">
      Customize how your café appears on client lock screens and this dashboard.
    </p>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div class="card space-y-5">
        <h2 class="text-lg font-semibold">Identity</h2>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Display name</label>
          <input v-model="form.display_name" type="text" class="input" placeholder="NISS E-LIBRARY" />
          <p class="text-xs text-gray-500 mt-1">Shown on client lock screens instead of a generic title.</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Tagline (optional)</label>
          <input v-model="form.tagline" type="text" class="input" placeholder="Play. Connect. Win." />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Accent color</label>
          <div class="flex items-center gap-3">
            <input v-model="form.accent_color" type="color" class="h-10 w-16 border rounded" />
            <input v-model="form.accent_color" type="text" class="input flex-1" />
          </div>
        </div>

        <div class="border-t pt-4">
          <h3 class="font-medium mb-3">Background</h3>
          <div class="mb-3">
            <label class="block text-sm font-medium text-gray-700 mb-2">Type</label>
            <select v-model="form.background.type" class="input">
              <option value="color">Solid color</option>
              <option value="image">Image</option>
            </select>
          </div>

          <div v-if="form.background.type === 'color'" class="mb-3">
            <label class="block text-sm font-medium text-gray-700 mb-2">Background color</label>
            <div class="flex items-center gap-3">
              <input v-model="form.background.color" type="color" class="h-10 w-16 border rounded" />
              <input v-model="form.background.color" type="text" class="input flex-1" />
            </div>
          </div>

          <div v-else class="mb-3">
            <label class="block text-sm font-medium text-gray-700 mb-2">Overlay opacity</label>
            <input
              v-model.number="form.background.overlay_opacity"
              type="range"
              min="0"
              max="1"
              step="0.05"
              class="w-full"
            />
            <p class="text-xs text-gray-500 mt-1">
              Darkens the background image so text stays readable ({{ form.background.overlay_opacity }}).
            </p>
          </div>
        </div>

        <button class="btn btn-primary" :disabled="saving" @click="saveBranding">
          {{ saving ? 'Saving…' : 'Save branding' }}
        </button>
      </div>

      <div class="card space-y-5">
        <h2 class="text-lg font-semibold">Assets</h2>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Dashboard logo</label>
          <div class="flex items-center gap-4">
            <img
              v-if="brandingStore.branding.logo_url"
              :src="brandingStore.branding.logo_url"
              alt="Logo"
              class="h-16 max-w-[200px] object-contain bg-gray-100 rounded p-2"
            />
            <span v-else class="text-sm text-gray-500">No logo uploaded</span>
          </div>
          <div class="flex gap-2 mt-2">
            <label class="btn btn-primary cursor-pointer">
              Upload logo
              <input type="file" accept="image/*" class="hidden" @change="onLogoUpload" />
            </label>
            <button
              v-if="brandingStore.branding.logo_url"
              class="btn btn-danger"
              type="button"
              @click="removeLogo(false)"
            >
              Remove
            </button>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Client lock screen logo</label>
          <div class="flex items-center gap-4">
            <img
              v-if="brandingStore.branding.logo_client_url"
              :src="brandingStore.branding.logo_client_url"
              alt="Client logo"
              class="h-16 max-w-[200px] object-contain bg-gray-900 rounded p-2"
            />
            <span v-else class="text-sm text-gray-500">
              Uses dashboard logo if not set separately
            </span>
          </div>
          <div class="flex gap-2 mt-2">
            <label class="btn btn-primary cursor-pointer">
              Upload client logo
              <input type="file" accept="image/*" class="hidden" @change="onClientLogoUpload" />
            </label>
            <button
              v-if="brandingStore.branding.logo_client_url"
              class="btn btn-danger"
              type="button"
              @click="removeLogo(true)"
            >
              Remove
            </button>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Client background image</label>
          <div v-if="brandingStore.branding.background?.image_url" class="mb-2">
            <img
              :src="brandingStore.branding.background.image_url"
              alt="Background"
              class="w-full max-h-40 object-cover rounded border"
            />
          </div>
          <div class="flex gap-2">
            <label class="btn btn-primary cursor-pointer">
              Upload background
              <input type="file" accept="image/*" class="hidden" @change="onBackgroundUpload" />
            </label>
            <button
              v-if="brandingStore.branding.background?.image_url"
              class="btn btn-danger"
              type="button"
              @click="removeBackground"
            >
              Remove
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="card mt-6">
      <h2 class="text-lg font-semibold mb-4">Client preview</h2>
      <div
        class="rounded-lg overflow-hidden border relative min-h-[280px] flex flex-col items-center justify-center p-8 text-center"
        :style="previewStyle"
      >
        <img
          v-if="previewLogo"
          :src="previewLogo"
          alt="Preview logo"
          class="max-h-20 mb-4 object-contain"
        />
        <h3 class="text-3xl font-bold" :style="{ color: form.accent_color }">
          {{ form.display_name || 'NISS E-LIBRARY' }}
        </h3>
        <p v-if="form.tagline" class="text-gray-300 mt-2">{{ form.tagline }}</p>
        <p class="text-gray-400 mt-6 text-sm">Enter Access Code</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useBrandingStore } from '@/stores/branding'

const brandingStore = useBrandingStore()
const saving = ref(false)

const form = reactive({
  display_name: '',
  tagline: '',
  accent_color: '#1B7F3A',
  background: {
    type: 'color',
    color: '#0f1a14',
    overlay_opacity: 0.45,
  },
})

const syncForm = () => {
  const b = brandingStore.branding
  form.display_name = b.display_name || ''
  form.tagline = b.tagline || ''
  form.accent_color = b.accent_color || '#1B7F3A'
  form.background.type = b.background?.type || 'color'
  form.background.color = b.background?.color || '#0f1a14'
  form.background.overlay_opacity = b.background?.overlay_opacity ?? 0.45
}

const previewLogo = computed(
  () => brandingStore.branding.logo_client_url || brandingStore.branding.logo_url
)

const previewStyle = computed(() => {
  const bg = form.background
  if (bg.type === 'image' && brandingStore.branding.background?.image_url) {
    const overlay = bg.overlay_opacity ?? 0.45
    return {
      backgroundImage: `linear-gradient(rgba(0,0,0,${overlay}), rgba(0,0,0,${overlay})), url(${brandingStore.branding.background.image_url})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      color: '#fff',
    }
  }
  return {
    backgroundColor: bg.color || '#0f1a14',
    color: '#fff',
  }
})

const saveBranding = async () => {
  saving.value = true
  try {
    await brandingStore.saveSettings({
      display_name: form.display_name,
      tagline: form.tagline,
      accent_color: form.accent_color,
      background: {
        type: form.background.type,
        color: form.background.color,
        overlay_opacity: form.background.overlay_opacity,
      },
    })
    alert('Branding saved. Clients will update on next heartbeat.')
  } catch (error) {
    alert('Failed to save branding')
  } finally {
    saving.value = false
  }
}

const onLogoUpload = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  await brandingStore.uploadLogo(file, false)
  syncForm()
  event.target.value = ''
}

const onClientLogoUpload = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  await brandingStore.uploadLogo(file, true)
  syncForm()
  event.target.value = ''
}

const onBackgroundUpload = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  await brandingStore.uploadBackground(file)
  form.background.type = 'image'
  syncForm()
  event.target.value = ''
}

const removeLogo = async (clientVariant) => {
  await brandingStore.removeLogo(clientVariant)
  syncForm()
}

const removeBackground = async () => {
  await brandingStore.removeBackground()
  form.background.type = 'color'
  syncForm()
}

onMounted(async () => {
  await brandingStore.fetchBranch(1)
  syncForm()
})
</script>
