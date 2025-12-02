import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatApi } from '@/api/chat'
import type { Chat, Message } from '@/types/chat'

const HARDCODED_USER_ID = '00000000-0000-0000-0000-000000000001'

export const useChatStore = defineStore('chat', () => {
  const chats = ref<Chat[]>([])
  const currentChat = ref<Chat | null>(null)
  const messages = ref<Message[]>([])
  const pendingRequestId = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  let pollingIntervalId: number | null = null

  async function fetchChats() {
    try {
      isLoading.value = true
      error.value = null
      const response = await chatApi.list(HARDCODED_USER_ID)
      chats.value = response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch chats'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createChat(title: string = 'New Chat') {
    try {
      isLoading.value = true
      error.value = null
      const response = await chatApi.create({
        user_id: HARDCODED_USER_ID,
        title
      })
      const newChat = response.data
      chats.value.unshift(newChat)
      await selectChat(newChat.id)
      return newChat
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create chat'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function selectChat(chatId: string) {
    stopPolling() // Stop any pending polling from previous chat
    pendingRequestId.value = null
    try {
      isLoading.value = true
      error.value = null
      const response = await chatApi.get(chatId)
      const data = response.data
      // Backend returns flat structure with messages included
      currentChat.value = {
        id: data.id,
        user_id: data.user_id,
        title: data.title,
        system_prompt: data.system_prompt,
        created_at: data.created_at
      }
      messages.value = (data.messages || []).filter((m): m is Message => m != null)

      // Resume polling if there's a pending assistant message
      const pendingMessage = messages.value.find(
        m => m.role === 'assistant' && m.status === 'pending' && m.request_id
      )
      if (pendingMessage?.request_id) {
        pendingRequestId.value = pendingMessage.request_id
        startPolling(pendingMessage.request_id)
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to load chat'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function deleteChat(chatId: string) {
    try {
      await chatApi.delete(chatId)
      chats.value = chats.value.filter(c => c.id !== chatId)
      if (currentChat.value?.id === chatId) {
        currentChat.value = null
        messages.value = []
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to delete chat'
      throw err
    }
  }

  async function sendMessage(content: string) {
    if (!currentChat.value) {
      throw new Error('No chat selected')
    }

    try {
      error.value = null

      // Optimistic UI: add user message immediately
      const optimisticMessage: Message = {
        id: `temp-${Date.now()}`,
        chat_id: currentChat.value.id,
        role: 'user',
        content,
        created_at: new Date().toISOString()
      }
      messages.value.push(optimisticMessage)

      // Send message to backend
      const response = await chatApi.sendMessage(currentChat.value.id, content)
      const { message, request_id } = response.data

      // Replace optimistic message with real one
      const index = messages.value.findIndex(m => m?.id === optimisticMessage.id)
      if (index !== -1 && message?.id) {
        messages.value[index] = message
      }

      // Start polling for assistant response
      pendingRequestId.value = request_id
      startPolling(request_id)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to send message'
      throw err
    }
  }

  function stopPolling() {
    if (pollingIntervalId !== null) {
      clearInterval(pollingIntervalId)
      pollingIntervalId = null
    }
  }

  function startPolling(requestId: string) {
    stopPolling() // Clear any existing polling

    const poll = async () => {
      try {
        const response = await chatApi.getMessageStatus(requestId)
        const data = response.data

        if (data.status === 'completed' && data.message?.id) {
          stopPolling()
          messages.value.push(data.message)
          pendingRequestId.value = null
        } else if (data.status === 'error') {
          stopPolling()
          error.value = data.error || 'Unknown error occurred'
          pendingRequestId.value = null
        }
      } catch (err) {
        console.error('Polling error:', err)
        // Continue polling on network errors
      }
    }

    // Initial poll
    poll()

    // Poll every second
    pollingIntervalId = window.setInterval(poll, 1000)
  }

  function updateCurrentChat(chat: Chat) {
    if (currentChat.value && currentChat.value.id === chat.id) {
      currentChat.value = chat
    }
    // Update in chats list too
    const index = chats.value.findIndex(c => c.id === chat.id)
    if (index !== -1) {
      chats.value[index] = chat
    }
  }

  return {
    chats,
    currentChat,
    messages,
    pendingRequestId,
    isLoading,
    error,
    fetchChats,
    createChat,
    selectChat,
    deleteChat,
    sendMessage,
    stopPolling,
    updateCurrentChat
  }
})
