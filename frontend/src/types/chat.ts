export interface Chat {
  id: string
  user_id: string
  title: string | null
  system_prompt: string | null
  temperature: number | null
  created_at: string
}

export interface Message {
  id: string
  chat_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  request_id?: string
  status?: MessageStatus
}

export type MessageStatus = 'pending' | 'processing' | 'completed' | 'error'

export interface ChatWithMessages extends Chat {
  messages: Message[]
}

export interface ChatCreate {
  user_id: string
  title: string
  system_prompt?: string
}

export interface ChatUpdate {
  title?: string | null
  system_prompt?: string | null
  temperature?: number | null
}

export interface MessageSendResponse {
  message: Message
  request_id: string
}

export interface MessageStatusResponse {
  request_id: string
  status: MessageStatus
  message?: Message
  error?: string
}
