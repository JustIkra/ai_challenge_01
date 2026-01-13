#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { initDb, upsertDocument, getDocumentByPath, searchSimilar, getStats, clearAll, getAllPaths, deleteByPaths, closeDb, getChatHistory, appendChatMessage, resetChatHistory, getChatSessionStats } from "./lib/db.mjs";
import { loadAllFiles, loadSingleFile } from "./lib/loader.mjs";
import { generateEmbeddingsBatched, generateQueryEmbedding } from "./lib/embeddings.mjs";

// Progress tracking state
let indexingProgress = {
  active: false,
  total: 0,
  current: 0,
  phase: 'idle', // idle, loading, embedding, storing, cleanup
  startTime: null,
  lastFile: null
};

// Server setup
const server = new McpServer({
  name: "rag-server-mcp",
  version: "0.1.0"
});

/**
 * Format result for MCP response
 * @param {{ success: boolean, output?: string, error?: string }} result
 * @returns {{ content: Array<{ type: string, text: string }> }}
 */
function formatResult(result) {
  if (result.success) {
    return {
      content: [{ type: "text", text: result.output || "Command executed successfully." }]
    };
  }
  return {
    content: [{ type: "text", text: `Error: ${result.error}` }]
  };
}

// Tool: rag_index
server.registerTool(
  "rag_index",
  {
    description: "Index project files for semantic search. Use force=true to reindex all files, file=path to index single file.",
    inputSchema: {
      force: z.boolean().optional().describe("Force reindex all files (default: false)"),
      file: z.string().optional().describe("Index single file by path (relative or absolute)")
    }
  },
  async ({ force = false, file = null }) => {
    try {
      // Single file indexing
      if (file) {
        console.error(`[rag_index] Indexing single file: ${file}`);

        await initDb();

        const fileData = await loadSingleFile(file);
        if (!fileData) {
          return formatResult({ success: false, error: `Failed to load file: ${file}` });
        }

        // Check if needs update (unless force)
        if (!force) {
          const existing = await getDocumentByPath(fileData.path);
          if (existing && existing.file_hash === fileData.hash) {
            return formatResult({
              success: true,
              output: `File unchanged: ${fileData.path}`
            });
          }
        }

        // Generate embedding
        const embeddings = await generateEmbeddingsBatched([fileData.content]);

        await upsertDocument(
          fileData.path,
          fileData.type,
          fileData.content,
          embeddings[0],
          fileData.hash,
          fileData.language,
          fileData.linesCount
        );

        return formatResult({
          success: true,
          output: `Indexed: ${fileData.path} (${fileData.language || fileData.type}, ${fileData.linesCount} lines)`
        });
      }

      // Full indexation with progress tracking
      console.error(`[rag_index] Starting indexation (force=${force})`);

      indexingProgress = {
        active: true,
        total: 0,
        current: 0,
        phase: 'loading',
        startTime: Date.now(),
        lastFile: null
      };

      await initDb();

      // Load all files
      const files = await loadAllFiles();
      indexingProgress.phase = 'filtering';

      if (files.length === 0) {
        indexingProgress = { ...indexingProgress, active: false, phase: 'idle' };
        return formatResult({ success: true, output: "No files found to index." });
      }

      // Filter files that need indexing
      let filesToIndex = [];
      let skippedCount = 0;

      if (force) {
        filesToIndex = files;
      } else {
        // Check which files need updating
        for (const file of files) {
          const existing = await getDocumentByPath(file.path);

          if (!existing || existing.file_hash !== file.hash) {
            filesToIndex.push(file);
          } else {
            skippedCount++;
          }
        }
      }

      console.error(`[rag_index] Files to index: ${filesToIndex.length}, skipped (unchanged): ${skippedCount}`);

      if (filesToIndex.length === 0) {
        indexingProgress = { ...indexingProgress, active: false, phase: 'idle' };
        return formatResult({
          success: true,
          output: `Index is up to date. ${skippedCount} files unchanged.`
        });
      }

      indexingProgress.total = filesToIndex.length;
      indexingProgress.phase = 'embedding';

      // Generate embeddings in batches
      const texts = filesToIndex.map(f => f.content);
      const embeddings = await generateEmbeddingsBatched(texts);

      indexingProgress.phase = 'storing';

      // Store in database
      let indexedCount = 0;
      for (let i = 0; i < filesToIndex.length; i++) {
        const file = filesToIndex[i];
        const embedding = embeddings[i];

        indexingProgress.current = i + 1;
        indexingProgress.lastFile = file.path;

        await upsertDocument(
          file.path,
          file.type,
          file.content,
          embedding,
          file.hash,
          file.language,
          file.linesCount
        );

        indexedCount++;

        if (indexedCount % 10 === 0) {
          console.error(`[rag_index] Indexed ${indexedCount}/${filesToIndex.length} files`);
        }
      }

      indexingProgress.phase = 'cleanup';

      // Clean up deleted files
      const currentPaths = new Set(files.map(f => f.path));
      const indexedPaths = await getAllPaths();
      const deletedPaths = indexedPaths.filter(p => !currentPaths.has(p));

      if (deletedPaths.length > 0) {
        await deleteByPaths(deletedPaths);
        console.error(`[rag_index] Removed ${deletedPaths.length} deleted files from index`);
      }

      const stats = await getStats();
      const elapsed = ((Date.now() - indexingProgress.startTime) / 1000).toFixed(1);

      indexingProgress = { ...indexingProgress, active: false, phase: 'idle' };

      return formatResult({
        success: true,
        output: `Indexation complete in ${elapsed}s.\n` +
          `- Indexed: ${indexedCount} files\n` +
          `- Skipped (unchanged): ${skippedCount} files\n` +
          `- Removed (deleted): ${deletedPaths.length} files\n` +
          `- Total in index: ${stats.total} files\n` +
          `- By type: code=${stats.by_type.code}, docs=${stats.by_type.docs}`
      });

    } catch (error) {
      indexingProgress = { ...indexingProgress, active: false, phase: 'error' };
      console.error(`[rag_index] Error: ${error.message}`);
      return formatResult({ success: false, error: error.message });
    }
  }
);

// Tool: rag_search
server.registerTool(
  "rag_search",
  {
    description: "Semantic search across indexed project files. Returns most relevant files for the query.",
    inputSchema: {
      query: z.string().describe("Search query"),
      limit: z.number().optional().describe("Maximum number of results (default: 5)"),
      format: z.enum(['text', 'json']).optional().describe("Output format: 'text' (default, human-readable) or 'json' (structured data)")
    }
  },
  async ({ query, limit = 5, format = 'text' }) => {
    try {
      if (!query || query.trim().length === 0) {
        return formatResult({ success: false, error: "Query cannot be empty" });
      }

      console.error(`[rag_search] Searching for: "${query}" (limit=${limit}, format=${format})`);

      await initDb();

      // Generate query embedding
      const queryEmbedding = await generateQueryEmbedding(query);

      // Search for similar documents
      const results = await searchSimilar(queryEmbedding, limit);

      if (results.length === 0) {
        return formatResult({ success: true, output: "No results found. Try running rag_index first." });
      }

      // Return JSON format if requested
      if (format === 'json') {
        const jsonResults = results.map((r, i) => ({
          rank: i + 1,
          file_path: r.file_path,
          file_type: r.file_type,
          language: r.language || r.file_type,
          similarity: r.similarity,
          lines_count: r.lines_count,
          content: r.content
        }));

        return formatResult({
          success: true,
          output: JSON.stringify({ results: jsonResults, count: results.length }, null, 2)
        });
      }

      // Format results as text (existing behavior)
      const output = results.map((r, i) => {
        const similarity = (r.similarity * 100).toFixed(1);
        const preview = r.content.slice(0, 200).replace(/\n/g, ' ').trim();
        return `${i + 1}. [${similarity}%] ${r.file_path} (${r.language || r.file_type})\n   ${preview}${r.content.length > 200 ? '...' : ''}`;
      }).join('\n\n');

      return formatResult({
        success: true,
        output: `Found ${results.length} results:\n\n${output}`
      });

    } catch (error) {
      console.error(`[rag_search] Error: ${error.message}`);
      return formatResult({ success: false, error: error.message });
    }
  }
);

// Tool: rag_status
server.registerTool(
  "rag_status",
  {
    description: "Get statistics about the RAG index."
  },
  async () => {
    try {
      await initDb();

      const stats = await getStats();

      const languageList = Object.entries(stats.by_language)
        .map(([lang, count]) => `  ${lang}: ${count}`)
        .join('\n');

      return formatResult({
        success: true,
        output: `RAG Index Statistics:\n` +
          `- Total documents: ${stats.total}\n` +
          `- Code files: ${stats.by_type.code}\n` +
          `- Documentation files: ${stats.by_type.docs}\n` +
          `\nBy language:\n${languageList || '  (none)'}`
      });

    } catch (error) {
      console.error(`[rag_status] Error: ${error.message}`);
      return formatResult({ success: false, error: error.message });
    }
  }
);

// Tool: rag_clear
server.registerTool(
  "rag_clear",
  {
    description: "Clear the RAG index. This will remove all indexed documents."
  },
  async () => {
    try {
      await initDb();

      await clearAll();

      return formatResult({
        success: true,
        output: "RAG index cleared successfully."
      });

    } catch (error) {
      console.error(`[rag_clear] Error: ${error.message}`);
      return formatResult({ success: false, error: error.message });
    }
  }
);

// Tool: rag_progress
server.registerTool(
  "rag_progress",
  {
    description: "Get current indexation progress. Returns status of ongoing indexation or 'idle' if not running."
  },
  async () => {
    try {
      if (!indexingProgress.active) {
        return formatResult({
          success: true,
          output: "No indexation in progress."
        });
      }

      const elapsed = ((Date.now() - indexingProgress.startTime) / 1000).toFixed(1);
      const percent = indexingProgress.total > 0
        ? ((indexingProgress.current / indexingProgress.total) * 100).toFixed(0)
        : 0;

      const progressBar = indexingProgress.total > 0
        ? `[${'█'.repeat(Math.floor(percent / 5))}${'░'.repeat(20 - Math.floor(percent / 5))}]`
        : '[loading...]';

      return formatResult({
        success: true,
        output: `Indexation in progress:\n` +
          `${progressBar} ${percent}%\n` +
          `- Phase: ${indexingProgress.phase}\n` +
          `- Progress: ${indexingProgress.current}/${indexingProgress.total} files\n` +
          `- Elapsed: ${elapsed}s\n` +
          `- Current file: ${indexingProgress.lastFile || '(starting)'}`
      });

    } catch (error) {
      return formatResult({ success: false, error: error.message });
    }
  }
);

// ============================================
// RAG Chat Tools
// ============================================

// Tool: rag_chat_history
server.registerTool(
  "rag_chat_history",
  {
    description: "Get chat history for a session. Returns last N messages in chronological order.",
    inputSchema: {
      session_id: z.string().optional().describe("Session identifier (default: 'default')"),
      limit: z.number().optional().describe("Maximum number of messages to return (default: 10)")
    }
  },
  async ({ session_id = 'default', limit = 10 }) => {
    try {
      console.error(`[rag_chat_history] Getting history for session: ${session_id} (limit=${limit})`);
      
      await initDb();
      
      const messages = await getChatHistory(session_id, limit);
      const stats = await getChatSessionStats(session_id);
      
      if (messages.length === 0) {
        return formatResult({
          success: true,
          output: JSON.stringify({
            session_id,
            messages: [],
            total_in_session: 0
          }, null, 2)
        });
      }
      
      const formattedMessages = messages.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        sources: m.sources,
        created_at: m.created_at
      }));
      
      return formatResult({
        success: true,
        output: JSON.stringify({
          session_id,
          messages: formattedMessages,
          total_in_session: stats.message_count,
          first_message: stats.first_message,
          last_message: stats.last_message
        }, null, 2)
      });
      
    } catch (error) {
      console.error(`[rag_chat_history] Error: ${error.message}`);
      return formatResult({ success: false, error: error.message });
    }
  }
);

// Tool: rag_chat_append
server.registerTool(
  "rag_chat_append",
  {
    description: "Append a message to chat history. Used to save user questions and assistant responses.",
    inputSchema: {
      session_id: z.string().optional().describe("Session identifier (default: 'default')"),
      role: z.enum(['user', 'assistant']).describe("Message role: 'user' or 'assistant'"),
      content: z.string().describe("Message content"),
      sources: z.array(z.object({
        file_path: z.string(),
        similarity: z.number()
      })).optional().describe("Sources for assistant messages (array of {file_path, similarity})")
    }
  },
  async ({ session_id = 'default', role, content, sources = null }) => {
    try {
      console.error(`[rag_chat_append] Appending ${role} message to session: ${session_id}`);
      
      await initDb();
      
      const result = await appendChatMessage(session_id, role, content, sources);
      
      return formatResult({
        success: true,
        output: JSON.stringify({
          id: result.id,
          session_id,
          role,
          created_at: result.created_at,
          sources_count: sources ? sources.length : 0
        }, null, 2)
      });
      
    } catch (error) {
      console.error(`[rag_chat_append] Error: ${error.message}`);
      return formatResult({ success: false, error: error.message });
    }
  }
);

// Tool: rag_chat_reset
server.registerTool(
  "rag_chat_reset",
  {
    description: "Reset (delete) chat history for a session. Use to start a fresh conversation.",
    inputSchema: {
      session_id: z.string().optional().describe("Session identifier (default: 'default')")
    }
  },
  async ({ session_id = 'default' }) => {
    try {
      console.error(`[rag_chat_reset] Resetting session: ${session_id}`);
      
      await initDb();
      
      const deletedCount = await resetChatHistory(session_id);
      
      return formatResult({
        success: true,
        output: `Session "${session_id}" reset. Deleted ${deletedCount} messages.`
      });
      
    } catch (error) {
      console.error(`[rag_chat_reset] Error: ${error.message}`);
      return formatResult({ success: false, error: error.message });
    }
  }
);

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('[rag-server] MCP server started');
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
  console.error('[rag-server] Shutting down...');
  await closeDb();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.error('[rag-server] Shutting down...');
  await closeDb();
  process.exit(0);
});

main().catch(error => {
  console.error("Server error:", error);
  process.exit(1);
});
