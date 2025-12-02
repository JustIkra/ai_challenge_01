<template>
  <div class="flex flex-col h-full bg-gray-800">
    <!-- Header -->
    <div class="border-b border-gray-700 bg-gray-900 p-4">
      <div v-if="chatStore.currentChat" class="flex items-center justify-between">
        <h2 class="text-xl font-semibold text-white">
          {{ chatStore.currentChat.title }}
        </h2>
        <button
          @click="showSettings = true"
          class="p-2 text-gray-400 hover:text-white transition-colors"
          title="Chat settings"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
      <div v-else class="text-gray-400">
        Select a chat or create a new one
      </div>
    </div>

    <!-- Messages Area -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4 space-y-2"
    >
      <div v-if="chatStore.isLoading && chatStore.messages.length === 0" class="flex justify-center py-8">
        <LoadingSpinner />
      </div>

      <div v-else-if="!chatStore.currentChat" class="flex items-center justify-center h-full">
        <div class="text-center text-gray-400">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mx-auto mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p class="text-lg">No chat selected</p>
          <p class="text-sm mt-2">Choose a chat from the sidebar to start messaging</p>
        </div>
      </div>

      <div v-else-if="chatStore.messages.length === 0" class="flex items-center justify-center h-full">
        <div class="text-center text-gray-400">
          <p class="text-lg">No messages yet</p>
          <p class="text-sm mt-2">Start the conversation by sending a message</p>
        </div>
      </div>

      <div v-else>
        <MessageBubble
          v-for="message in chatStore.messages.filter(m => m?.id)"
          :key="message.id"
          :message="message"
        />

        <!-- Loading indicator for pending response -->
        <div v-if="chatStore.pendingRequestId" class="flex justify-start mb-4">
          <div class="bg-gray-700 rounded-lg px-4 py-2">
            <LoadingSpinner size="sm" />
          </div>
        </div>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="chatStore.error" class="bg-red-900/50 text-red-200 px-4 py-2 text-sm">
      {{ chatStore.error }}
    </div>

    <!-- Input Area -->
    <MessageInput
      v-if="chatStore.currentChat"
      :disabled="!!chatStore.pendingRequestId"
      @send="handleSendMessage"
    />

    <!-- Settings Modal -->
    <ChatSettingsModal
      :is-open="showSettings"
      :chat="chatStore.currentChat"
      @close="showSettings = false"
      @saved="handleSettingsSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import MessageBubble from './MessageBubble.vue'
import MessageInput from './MessageInput.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ChatSettingsModal from './ChatSettingsModal.vue'
import type { Chat } from '@/types/chat'

const chatStore = useChatStore()
const messagesContainer = ref<HTMLElement | null>(null)
const showSettings = ref(false)

async function handleSendMessage(content: string) {
  try {
    await chatStore.sendMessage(content)
    scrollToBottom()
  } catch (error) {
    console.error('Failed to send message:', error)
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function handleSettingsSaved(updatedChat: Chat) {
  chatStore.updateCurrentChat(updatedChat)
}

// Auto-scroll when messages change
watch(
  () => chatStore.messages.length,
  () => {
    scrollToBottom()
  }
)

// Auto-scroll when chat changes
watch(
  () => chatStore.currentChat?.id,
  () => {
    scrollToBottom()
  }
)
</script>
