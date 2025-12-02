import { ref, onUnmounted } from 'vue'
import { chatApi } from '@/api/chat'
import type { MessageStatus, Message } from '@/types/chat'

export function usePolling(requestId: string, onComplete: (message: Message) => void, onError: (error: string) => void) {
  const status = ref<MessageStatus>('pending')
  const isPolling = ref(false)
  let intervalId: number | null = null

  const startPolling = () => {
    if (isPolling.value) return

    isPolling.value = true

    const poll = async () => {
      try {
        const response = await chatApi.getMessageStatus(requestId)
        const data = response.data

        status.value = data.status

        // Stop polling when status is final
        if (data.status === 'completed' && data.message) {
          stopPolling()
          onComplete(data.message)
        } else if (data.status === 'error') {
          stopPolling()
          onError(data.error || 'Unknown error occurred')
        }
      } catch (error) {
        console.error('Polling error:', error)
        // Continue polling on network errors
      }
    }

    // Initial poll
    poll()

    // Poll every second
    intervalId = window.setInterval(poll, 1000)
  }

  const stopPolling = () => {
    if (intervalId !== null) {
      clearInterval(intervalId)
      intervalId = null
    }
    isPolling.value = false
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stopPolling()
  })

  return {
    status,
    isPolling,
    startPolling,
    stopPolling
  }
}
