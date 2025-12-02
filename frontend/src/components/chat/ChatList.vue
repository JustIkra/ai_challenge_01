<template>
  <div class="flex flex-col h-full">
    <div class="p-4">
      <button
        @click="handleNewChat"
        class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition"
        :disabled="chatStore.isLoading"
      >
        + New Chat
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-2">
      <div v-if="chatStore.isLoading && chatStore.chats.length === 0" class="flex justify-center py-8">
        <LoadingSpinner />
      </div>

      <div v-else-if="chatStore.chats.length === 0" class="text-gray-400 text-center py-8 px-4">
        No chats yet. Create one to get started!
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="chat in chatStore.chats"
          :key="chat.id"
          @click="selectChat(chat.id)"
          class="p-3 rounded cursor-pointer transition group relative"
          :class="[
            chatStore.currentChat?.id === chat.id
              ? 'bg-gray-700'
              : 'hover:bg-gray-800'
          ]"
        >
          <div class="flex items-center justify-between">
            <div class="flex-1 truncate">
              <p class="text-sm font-medium truncate">{{ chat.title }}</p>
              <p class="text-xs text-gray-400">{{ formatDate(chat.created_at) }}</p>
            </div>

            <button
              @click.stop="handleDelete(chat.id)"
              class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1 transition"
              title="Delete chat"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="chatStore.error" class="p-4 bg-red-900/50 text-red-200 text-sm">
      {{ chatStore.error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const chatStore = useChatStore()

onMounted(() => {
  chatStore.fetchChats()
})

async function handleNewChat() {
  try {
    await chatStore.createChat()
  } catch (error) {
    console.error('Failed to create chat:', error)
  }
}

async function selectChat(chatId: string) {
  try {
    await chatStore.selectChat(chatId)
  } catch (error) {
    console.error('Failed to select chat:', error)
  }
}

async function handleDelete(chatId: string) {
  if (!confirm('Are you sure you want to delete this chat?')) {
    return
  }

  try {
    await chatStore.deleteChat(chatId)
  } catch (error) {
    console.error('Failed to delete chat:', error)
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return 'Today'
  } else if (days === 1) {
    return 'Yesterday'
  } else if (days < 7) {
    return `${days} days ago`
  } else {
    return date.toLocaleDateString()
  }
}
</script>
