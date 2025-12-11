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
        class="text-xs mt-1 flex items-center gap-2"
        :class="message.role === 'user' ? 'text-blue-200' : 'text-gray-400'"
      >
        <span>{{ formatTime(message.created_at) }}</span>
        <span v-if="message.role === 'assistant' && message.token_usage" class="text-gray-500">
          · Запрос: {{ message.token_usage.prompt_tokens }} · Ответ: {{ message.token_usage.completion_tokens }}
        </span>
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
