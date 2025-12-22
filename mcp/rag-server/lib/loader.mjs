import { glob } from 'glob';
import { readFile, stat } from 'fs/promises';
import { createHash } from 'crypto';
import path from 'path';
import { CONFIG } from '../config.mjs';

/**
 * Language detection map by file extension
 */
const LANGUAGE_MAP = {
  '.py': 'python',
  '.js': 'javascript',
  '.mjs': 'javascript',
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.vue': 'vue',
  '.md': 'markdown',
  '.json': 'json',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.sql': 'sql',
  '.html': 'html',
  '.css': 'css',
  '.sh': 'shell',
  '.bash': 'shell'
};

/**
 * Detect programming language from file extension
 * @param {string} filePath - Path to the file
 * @returns {string|null} Language name or null
 */
export function getLanguage(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return LANGUAGE_MAP[ext] || null;
}

/**
 * Calculate SHA256 hash of file content
 * @param {string} content - File content
 * @returns {string} SHA256 hash
 */
export function getFileHash(content) {
  return createHash('sha256').update(content, 'utf8').digest('hex');
}

/**
 * Load files based on type (code or docs)
 * @param {'code' | 'docs'} type - Type of files to load
 * @returns {Promise<Array<{path: string, content: string, hash: string, language: string|null, linesCount: number}>>}
 */
export async function loadFiles(type) {
  const config = type === 'code' ? CONFIG.code : CONFIG.docs;
  const projectRoot = CONFIG.projectRoot;

  const files = [];

  for (const pattern of config.patterns) {
    const matches = await glob(pattern, {
      cwd: projectRoot,
      ignore: config.ignore,
      nodir: true,
      absolute: false
    });

    for (const relativePath of matches) {
      const absolutePath = path.join(projectRoot, relativePath);

      try {
        // Check file size
        const fileStat = await stat(absolutePath);
        if (fileStat.size > CONFIG.limits.maxFileSize) {
          console.error(`[loader] Skipping ${relativePath}: file too large (${fileStat.size} bytes)`);
          continue;
        }

        // Read file content
        const content = await readFile(absolutePath, 'utf8');

        // Skip empty files
        if (!content.trim()) {
          console.error(`[loader] Skipping ${relativePath}: empty file`);
          continue;
        }

        const hash = getFileHash(content);
        const language = getLanguage(relativePath);
        const linesCount = content.split('\n').length;

        files.push({
          path: relativePath,
          content,
          hash,
          language,
          linesCount
        });
      } catch (error) {
        console.error(`[loader] Error reading ${relativePath}: ${error.message}`);
      }
    }
  }

  console.error(`[loader] Loaded ${files.length} ${type} files`);
  return files;
}

/**
 * Load a single file by path
 * @param {string} filePath - Relative or absolute path to file
 * @returns {Promise<{path: string, content: string, hash: string, language: string|null, linesCount: number, type: string}|null>}
 */
export async function loadSingleFile(filePath) {
  const projectRoot = CONFIG.projectRoot;

  // Normalize path - convert absolute to relative if needed
  let relativePath = filePath;
  if (path.isAbsolute(filePath)) {
    relativePath = path.relative(projectRoot, filePath);
  }

  const absolutePath = path.join(projectRoot, relativePath);

  try {
    const fileStat = await stat(absolutePath);
    if (fileStat.size > CONFIG.limits.maxFileSize) {
      console.error(`[loader] File too large: ${relativePath} (${fileStat.size} bytes)`);
      return null;
    }

    const content = await readFile(absolutePath, 'utf8');

    if (!content.trim()) {
      console.error(`[loader] Empty file: ${relativePath}`);
      return null;
    }

    const hash = getFileHash(content);
    const language = getLanguage(relativePath);
    const linesCount = content.split('\n').length;

    // Determine type based on extension
    const ext = path.extname(relativePath).toLowerCase();
    const isDoc = ['.md', '.txt', '.rst'].includes(ext);

    return {
      path: relativePath,
      content,
      hash,
      language,
      linesCount,
      type: isDoc ? 'docs' : 'code'
    };
  } catch (error) {
    console.error(`[loader] Error reading ${relativePath}: ${error.message}`);
    return null;
  }
}

/**
 * Load all files (code and docs)
 * @returns {Promise<Array<{path: string, content: string, hash: string, language: string|null, linesCount: number, type: string}>>}
 */
export async function loadAllFiles() {
  const codeFiles = await loadFiles('code');
  const docsFiles = await loadFiles('docs');

  const allFiles = [
    ...codeFiles.map(f => ({ ...f, type: 'code' })),
    ...docsFiles.map(f => ({ ...f, type: 'docs' }))
  ];

  // Deduplicate by path (in case patterns overlap)
  const seen = new Set();
  const deduped = [];

  for (const file of allFiles) {
    if (!seen.has(file.path)) {
      seen.add(file.path);
      deduped.push(file);
    }
  }

  console.error(`[loader] Total unique files: ${deduped.length}`);
  return deduped;
}
