<template>
  <div
    class="flex mb-4"
    :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <div
      class="max-w-[70%] rounded-lg px-4 py-2"
      :class="[
        message.role === 'user'
          ? 'bg-blue-600 text-white'
          : 'bg-gray-700 text-gray-100'
      ]"
    >
      <div class="whitespace-pre-wrap break-words">{{ message.content }}</div>
      <div
        class="text-xs mt-1"
        :class="message.role === 'user' ? 'text-blue-200' : 'text-gray-400'"
      >
        {{ formatTime(message.created_at) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Message } from '@/types/chat'

interface Props {
  message: Message
}

defineProps<Props>()

function formatTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>
