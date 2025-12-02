import { api } from './client'
import type {
  Chat,
  ChatCreate,
  ChatUpdate,
  ChatWithMessages,
  MessageSendResponse,
  MessageStatusResponse
} from '@/types/chat'

export const chatApi = {
  list: (userId: string) =>
    api.get<Chat[]>('/chats', { params: { user_id: userId } }),

  create: (data: ChatCreate) =>
    api.post<Chat>('/chats', data),

  get: (id: string) =>
    api.get<ChatWithMessages>(`/chats/${id}`),

  update: (id: string, data: ChatUpdate) =>
    api.patch<Chat>(`/chats/${id}`, data),

  delete: (id: string) =>
    api.delete(`/chats/${id}`),

  sendMessage: (chatId: string, content: string) =>
    api.post<MessageSendResponse>(`/chats/${chatId}/messages`, { content }),

  getMessageStatus: (requestId: string) =>
    api.get<MessageStatusResponse>(`/messages/${requestId}/status`)
}
