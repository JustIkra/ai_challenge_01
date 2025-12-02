<template>
  <div class="border-t border-gray-700 bg-gray-800 p-4">
    <form @submit.prevent="handleSubmit" class="flex items-end gap-2">
      <textarea
        v-model="inputValue"
        @keydown="handleKeyDown"
        placeholder="Type your message... (Shift+Enter for new line)"
        rows="1"
        class="flex-1 bg-gray-700 text-white rounded-lg px-4 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 max-h-32"
        :disabled="disabled"
        ref="textareaRef"
      ></textarea>

      <button
        type="submit"
        :disabled="!inputValue.trim() || disabled"
        class="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium py-2 px-6 rounded-lg transition"
      >
        Send
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

interface Props {
  disabled?: boolean
}

interface Emits {
  (e: 'send', content: string): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const inputValue = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function handleSubmit() {
  const content = inputValue.value.trim()
  if (!content) return

  emit('send', content)
  inputValue.value = ''

  // Reset textarea height
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
    }
  })
}

function handleKeyDown(event: KeyboardEvent) {
  // Submit on Enter (without Shift)
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSubmit()
  }
}

// Auto-resize textarea
watch(inputValue, () => {
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
      textareaRef.value.style.height = textareaRef.value.scrollHeight + 'px'
    }
  })
})
</script>
