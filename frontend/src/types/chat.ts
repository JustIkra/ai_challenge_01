export interface Chat {
  id: string
  user_id: string
  title: string | null
  system_prompt: string | null
  temperature: number | null
  created_at: string
  history_compression_enabled: boolean
  history_compression_message_limit: number | null
  compressed_history_summary: string | null
}

export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
}

export interface Message {
  id: string
  chat_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  request_id?: string
  status?: MessageStatus
  token_usage?: TokenUsage
  is_compressed?: boolean
}

export type MessageStatus = 'pending' | 'processing' | 'completed' | 'error'

export interface ChatWithMessages extends Chat {
  messages: Message[]
}

export interface ChatCreate {
  user_id: string
  title: string
  system_prompt?: string
  history_compression_enabled?: boolean
  history_compression_message_limit?: number
}

export interface ChatUpdate {
  title?: string | null
  system_prompt?: string | null
  temperature?: number | null
  history_compression_enabled?: boolean
  history_compression_message_limit?: number | null
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
