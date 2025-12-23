import { config as dotenvConfig } from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

// Load .env from project root
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = process.env.PROJECT_ROOT || resolve(__dirname, '../..');
dotenvConfig({ path: resolve(projectRoot, '.env') });

export const CONFIG = {
  code: {
    patterns: ['**/*.py', '**/*.js', '**/*.ts', '**/*.vue'],
    ignore: ['**/node_modules/**', '**/__pycache__/**', '**/dist/**', '**/.git/**', '**/venv/**', '**/.venv/**']
  },
  docs: {
    patterns: ['**/*.md', '.memory-base/**/*'],
    ignore: ['**/node_modules/**']
  },
  embeddings: {
    // Local model via @xenova/transformers (runs on CPU/Metal)
    model: process.env.EMBEDDING_MODEL || 'Xenova/multilingual-e5-small',
    batchSize: 20 // Smaller batches for local processing
  },
  limits: {
    maxFileSize: 100 * 1024,
    maxTokens: 8191
  },
  db: {
    connectionString: process.env.RAG_DATABASE_URL || process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/chatapp'
  },
  projectRoot: process.env.PROJECT_ROOT || process.cwd()
};
