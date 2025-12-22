import pg from 'pg';
import { CONFIG } from '../config.mjs';

const { Pool } = pg;

let pool = null;

/**
 * Initialize database connection pool and test connection
 * @returns {Promise<pg.Pool>}
 */
export async function initDb() {
  if (pool) {
    return pool;
  }

  pool = new Pool({
    connectionString: CONFIG.db.connectionString
  });

  // Test connection
  const client = await pool.connect();
  try {
    await client.query('SELECT 1');
    console.error('[db] Connection established');
  } finally {
    client.release();
  }

  return pool;
}

/**
 * Get the database pool (must call initDb first)
 * @returns {pg.Pool}
 */
export function getPool() {
  if (!pool) {
    throw new Error('Database not initialized. Call initDb() first.');
  }
  return pool;
}

/**
 * Upsert a document into the rag_documents table
 * @param {string} filePath - Path to the file
 * @param {string} fileType - 'code' or 'docs'
 * @param {string} content - File content
 * @param {number[]} embedding - Embedding vector
 * @param {string} fileHash - SHA256 hash of file content
 * @param {string|null} language - Programming language
 * @param {number} linesCount - Number of lines in file
 * @returns {Promise<void>}
 */
export async function upsertDocument(filePath, fileType, content, embedding, fileHash, language, linesCount) {
  const db = getPool();

  // Convert embedding array to pgvector format
  const embeddingStr = `[${embedding.join(',')}]`;

  const query = `
    INSERT INTO rag_documents (file_path, file_type, content, embedding, file_hash, language, lines_count, indexed_at)
    VALUES ($1, $2, $3, $4::vector, $5, $6, $7, NOW())
    ON CONFLICT (file_path) DO UPDATE SET
      file_type = EXCLUDED.file_type,
      content = EXCLUDED.content,
      embedding = EXCLUDED.embedding,
      file_hash = EXCLUDED.file_hash,
      language = EXCLUDED.language,
      lines_count = EXCLUDED.lines_count,
      indexed_at = NOW()
  `;

  await db.query(query, [filePath, fileType, content, embeddingStr, fileHash, language, linesCount]);
}

/**
 * Get document by file path
 * @param {string} filePath - Path to the file
 * @returns {Promise<{file_path: string, file_hash: string, indexed_at: Date}|null>}
 */
export async function getDocumentByPath(filePath) {
  const db = getPool();

  const result = await db.query(
    'SELECT file_path, file_hash, indexed_at FROM rag_documents WHERE file_path = $1',
    [filePath]
  );

  return result.rows[0] || null;
}

/**
 * Search for similar documents using vector similarity
 * @param {number[]} embedding - Query embedding vector
 * @param {number} limit - Maximum number of results
 * @returns {Promise<Array<{file_path: string, file_type: string, content: string, language: string, similarity: number}>>}
 */
export async function searchSimilar(embedding, limit = 10) {
  const db = getPool();

  // Convert embedding array to pgvector format
  const embeddingStr = `[${embedding.join(',')}]`;

  const query = `
    SELECT
      file_path,
      file_type,
      content,
      language,
      lines_count,
      1 - (embedding <=> $1::vector) as similarity
    FROM rag_documents
    ORDER BY embedding <=> $1::vector
    LIMIT $2
  `;

  const result = await db.query(query, [embeddingStr, limit]);
  return result.rows;
}

/**
 * Get statistics about indexed documents
 * @returns {Promise<{total: number, by_type: {code: number, docs: number}, by_language: Object}>}
 */
export async function getStats() {
  const db = getPool();

  const totalResult = await db.query('SELECT COUNT(*) as count FROM rag_documents');
  const byTypeResult = await db.query(
    'SELECT file_type, COUNT(*) as count FROM rag_documents GROUP BY file_type'
  );
  const byLanguageResult = await db.query(
    'SELECT language, COUNT(*) as count FROM rag_documents WHERE language IS NOT NULL GROUP BY language ORDER BY count DESC'
  );

  const byType = { code: 0, docs: 0 };
  for (const row of byTypeResult.rows) {
    byType[row.file_type] = parseInt(row.count, 10);
  }

  const byLanguage = {};
  for (const row of byLanguageResult.rows) {
    byLanguage[row.language] = parseInt(row.count, 10);
  }

  return {
    total: parseInt(totalResult.rows[0].count, 10),
    by_type: byType,
    by_language: byLanguage
  };
}

/**
 * Clear all documents from the index
 * @returns {Promise<number>} Number of deleted rows
 */
export async function clearAll() {
  const db = getPool();

  const result = await db.query('TRUNCATE TABLE rag_documents RESTART IDENTITY');
  console.error('[db] Index cleared');

  return 0; // TRUNCATE doesn't return row count
}

/**
 * Delete documents by file paths (for cleanup of deleted files)
 * @param {string[]} filePaths - Array of file paths to delete
 * @returns {Promise<number>} Number of deleted rows
 */
export async function deleteByPaths(filePaths) {
  if (filePaths.length === 0) return 0;

  const db = getPool();

  const result = await db.query(
    'DELETE FROM rag_documents WHERE file_path = ANY($1)',
    [filePaths]
  );

  return result.rowCount;
}

/**
 * Get all indexed file paths
 * @returns {Promise<string[]>}
 */
export async function getAllPaths() {
  const db = getPool();

  const result = await db.query('SELECT file_path FROM rag_documents');
  return result.rows.map(row => row.file_path);
}

/**
 * Close the database pool
 * @returns {Promise<void>}
 */
export async function closeDb() {
  if (pool) {
    await pool.end();
    pool = null;
    console.error('[db] Connection pool closed');
  }
}
