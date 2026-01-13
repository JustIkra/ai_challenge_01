-- Migration: rag_chat_init.sql
-- Таблица для хранения истории диалогов RAG-чата

CREATE TABLE IF NOT EXISTS rag_chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB NULL,  -- для assistant: массив {file_path, similarity}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индекс для быстрого доступа к сообщениям сессии по времени
CREATE INDEX IF NOT EXISTS rag_chat_messages_session_idx 
ON rag_chat_messages (session_id, created_at);

-- Индекс для очистки старых сессий
CREATE INDEX IF NOT EXISTS rag_chat_messages_created_at_idx 
ON rag_chat_messages (created_at);

COMMENT ON TABLE rag_chat_messages IS 'История диалогов RAG-чата с памятью сессий';
COMMENT ON COLUMN rag_chat_messages.session_id IS 'Идентификатор сессии диалога';
COMMENT ON COLUMN rag_chat_messages.role IS 'Роль: user или assistant';
COMMENT ON COLUMN rag_chat_messages.content IS 'Содержимое сообщения';
COMMENT ON COLUMN rag_chat_messages.sources IS 'Источники для assistant: [{file_path, similarity}]';

