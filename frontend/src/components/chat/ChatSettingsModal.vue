<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/50" @click="close"></div>

      <!-- Modal -->
      <div class="relative bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4 p-6">
        <h2 class="text-xl font-semibold text-white mb-4">Chat Settings</h2>

        <form @submit.prevent="save">
          <!-- Title -->
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-300 mb-2">
              Chat Title
            </label>
            <input
              v-model="formData.title"
              type="text"
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter chat title"
            />
          </div>

          <!-- System Prompt -->
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-300 mb-2">
              System Prompt
            </label>
            <textarea
              v-model="formData.system_prompt"
              rows="6"
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Enter system instructions for the AI assistant..."
            ></textarea>
            <p class="mt-1 text-xs text-gray-400">
              System prompt defines the AI assistant's behavior and context.
            </p>
          </div>

          <!-- Temperature -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-300 mb-2">
              Temperature: {{ formData.temperature }}
            </label>
            <input
              v-model.number="formData.temperature"
              type="range"
              min="0.1"
              max="1.5"
              step="0.1"
              class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div class="flex justify-between text-xs text-gray-500 mt-1">
              <span>0.1</span>
              <span>1.5</span>
            </div>
            <p class="mt-1 text-xs text-gray-400">
              Lower values produce more stable and deterministic responses. Higher values increase creativity and variability.
            </p>
          </div>

          <!-- History Compression -->
          <div class="mb-6 p-4 bg-gray-700/50 rounded-lg">
            <div class="flex items-center justify-between mb-3">
              <label class="text-sm font-medium text-gray-300">
                History Compression
              </label>
              <button
                type="button"
                @click="formData.history_compression_enabled = !formData.history_compression_enabled"
                :class="[
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  formData.history_compression_enabled ? 'bg-blue-600' : 'bg-gray-600'
                ]"
              >
                <span
                  :class="[
                    'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                    formData.history_compression_enabled ? 'translate-x-6' : 'translate-x-1'
                  ]"
                />
              </button>
            </div>
            <p class="text-xs text-gray-400 mb-3">
              Automatically summarize old messages to reduce token usage while preserving context.
            </p>

            <div v-if="formData.history_compression_enabled" class="mt-3">
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Compress after {{ formData.history_compression_message_limit }} messages
              </label>
              <input
                v-model.number="formData.history_compression_message_limit"
                type="range"
                min="5"
                max="50"
                step="5"
                class="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <div class="flex justify-between text-xs text-gray-500 mt-1">
                <span>5</span>
                <span>50</span>
              </div>
            </div>
          </div>

          <!-- Buttons -->
          <div class="flex justify-end gap-3">
            <button
              type="button"
              @click="close"
              class="px-4 py-2 text-gray-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isSaving"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {{ isSaving ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { chatApi } from '@/api/chat'
import type { Chat, ChatUpdate } from '@/types/chat'

const props = defineProps<{
  isOpen: boolean
  chat: Chat | null
}>()

const emit = defineEmits<{
  close: []
  saved: [chat: Chat]
}>()

const formData = ref<ChatUpdate>({
  title: '',
  system_prompt: '',
  temperature: 0.7,
  history_compression_enabled: false,
  history_compression_message_limit: 10
})

const isSaving = ref(false)

watch(() => props.chat, (newChat) => {
  if (newChat) {
    formData.value = {
      title: newChat.title || '',
      system_prompt: newChat.system_prompt || '',
      temperature: newChat.temperature ?? 0.7,
      history_compression_enabled: newChat.history_compression_enabled ?? false,
      history_compression_message_limit: newChat.history_compression_message_limit ?? 10
    }
  }
}, { immediate: true })

function close() {
  emit('close')
}

async function save() {
  if (!props.chat) return

  isSaving.value = true
  try {
    const response = await chatApi.update(props.chat.id, formData.value)
    emit('saved', response.data)
    close()
  } catch (error) {
    console.error('Failed to save chat settings:', error)
  } finally {
    isSaving.value = false
  }
}
</script>
