import { pipeline } from '@xenova/transformers';
import { CONFIG } from '../config.mjs';

let extractor = null;

/**
 * Initialize the embedding model (lazy loading)
 * @returns {Promise<Function>} Feature extraction pipeline
 */
async function getExtractor() {
  if (!extractor) {
    const model = CONFIG.embeddings.model;
    console.error(`[embeddings] Loading local model: ${model}`);
    extractor = await pipeline('feature-extraction', model, {
      quantized: true // Use quantized model for faster inference
    });
    console.error(`[embeddings] Model loaded successfully`);
  }
  return extractor;
}

/**
 * Generate embeddings for a batch of texts using local model
 * @param {string[]} texts - Array of texts to embed
 * @returns {Promise<number[][]>} Array of embedding vectors
 */
export async function generateEmbeddings(texts) {
  const extractor = await getExtractor();
  const embeddings = [];

  for (const text of texts) {
    // For E5 models, add "query: " or "passage: " prefix for better results
    const input = CONFIG.embeddings.model.includes('e5')
      ? `passage: ${text}`
      : text;

    const output = await extractor(input, {
      pooling: 'mean',
      normalize: true
    });

    embeddings.push(Array.from(output.data));
  }

  return embeddings;
}

/**
 * Generate embeddings for texts in batches
 * @param {string[]} texts - Array of texts to embed
 * @param {function} onProgress - Optional progress callback (current, total)
 * @returns {Promise<number[][]>} Array of embedding vectors
 */
export async function generateEmbeddingsBatched(texts, onProgress = null) {
  const { batchSize } = CONFIG.embeddings;
  const allEmbeddings = [];

  // Pre-load model before batch processing
  await getExtractor();

  for (let i = 0; i < texts.length; i += batchSize) {
    const batch = texts.slice(i, i + batchSize);
    const batchNum = Math.floor(i / batchSize) + 1;
    const totalBatches = Math.ceil(texts.length / batchSize);

    console.error(`[embeddings] Processing batch ${batchNum}/${totalBatches} (${batch.length} texts)`);

    const embeddings = await generateEmbeddings(batch);
    allEmbeddings.push(...embeddings);

    if (onProgress) {
      onProgress(Math.min(i + batchSize, texts.length), texts.length);
    }
  }

  return allEmbeddings;
}

/**
 * Generate a single embedding for a query
 * @param {string} text - Text to embed
 * @returns {Promise<number[]>} Embedding vector
 */
export async function generateQueryEmbedding(text) {
  const extractor = await getExtractor();

  // For E5 models, use "query: " prefix for search queries
  const input = CONFIG.embeddings.model.includes('e5')
    ? `query: ${text}`
    : text;

  const output = await extractor(input, {
    pooling: 'mean',
    normalize: true
  });

  return Array.from(output.data);
}
