CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_documents (
    id SERIAL PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    file_type TEXT NOT NULL,              -- 'code' | 'docs'
    content TEXT NOT NULL,
    embedding vector(384),  -- multilingual-e5-small dimension
    file_hash TEXT NOT NULL,
    indexed_at TIMESTAMP DEFAULT NOW(),
    language TEXT,
    lines_count INTEGER
);

CREATE INDEX IF NOT EXISTS rag_documents_embedding_idx
ON rag_documents USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS rag_documents_file_path_idx
ON rag_documents (file_path);
