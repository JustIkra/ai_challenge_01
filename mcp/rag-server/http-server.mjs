import http from 'node:http';
import { initDb, searchSimilar, getStats } from './lib/db.mjs';
import { generateQueryEmbedding } from './lib/embeddings.mjs';

const PORT = process.env.RAG_HTTP_PORT || 8801;

/**
 * Parse JSON body from incoming request
 * @param {http.IncomingMessage} req
 * @returns {Promise<object>}
 */
function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        reject(new Error('Invalid JSON'));
      }
    });
    req.on('error', reject);
  });
}

/**
 * Send JSON response with CORS headers
 * @param {http.ServerResponse} res
 * @param {number} statusCode
 * @param {object} data
 */
function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  });
  res.end(JSON.stringify(data));
}

/**
 * Handle POST /api/search
 * @param {http.IncomingMessage} req
 * @param {http.ServerResponse} res
 */
async function handleSearch(req, res) {
  try {
    const body = await parseBody(req);
    const { query, limit = 5 } = body;

    if (!query || typeof query !== 'string') {
      return sendJson(res, 400, { error: 'Missing or invalid "query" field' });
    }

    const queryLimit = Math.min(Math.max(1, parseInt(limit, 10) || 5), 50);

    // Generate embedding for the query
    const embedding = await generateQueryEmbedding(query);

    // Search for similar documents
    const rows = await searchSimilar(embedding, queryLimit);

    // Format results
    const results = rows.map((row, index) => ({
      rank: index + 1,
      file_path: row.file_path,
      file_type: row.file_type,
      language: row.language,
      similarity: parseFloat(row.similarity.toFixed(4)),
      lines_count: row.lines_count,
      content: row.content
    }));

    sendJson(res, 200, { results, count: results.length });
  } catch (err) {
    console.error('[http] Search error:', err.message);
    sendJson(res, 500, { error: err.message });
  }
}

/**
 * Handle GET /api/status
 * @param {http.IncomingMessage} req
 * @param {http.ServerResponse} res
 */
async function handleStatus(req, res) {
  try {
    const stats = await getStats();
    sendJson(res, 200, stats);
  } catch (err) {
    console.error('[http] Status error:', err.message);
    sendJson(res, 500, { error: err.message });
  }
}

/**
 * Main request handler
 * @param {http.IncomingMessage} req
 * @param {http.ServerResponse} res
 */
async function requestHandler(req, res) {
  const { method, url } = req;

  // Handle CORS preflight
  if (method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    return res.end();
  }

  // Route requests
  if (method === 'POST' && url === '/api/search') {
    return handleSearch(req, res);
  }

  if (method === 'GET' && url === '/api/status') {
    return handleStatus(req, res);
  }

  // 404 for unknown routes
  sendJson(res, 404, { error: 'Not found' });
}

/**
 * Start the HTTP server
 */
async function main() {
  console.error('[http] Initializing database...');
  await initDb();

  const server = http.createServer(requestHandler);

  server.listen(PORT, () => {
    console.error(`[http] RAG HTTP server listening on port ${PORT}`);
    console.error(`[http] Endpoints:`);
    console.error(`[http]   POST /api/search - Search documents`);
    console.error(`[http]   GET  /api/status - Get index statistics`);
  });
}

main().catch(err => {
  console.error('[http] Fatal error:', err);
  process.exit(1);
});
