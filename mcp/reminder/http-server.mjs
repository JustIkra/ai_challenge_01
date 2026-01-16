#!/usr/bin/env node

import http from 'node:http';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { randomUUID } from 'crypto';

const PORT = process.env.REMINDER_HTTP_PORT || 8802;
const REMINDERS_FILE = process.env.REMINDERS_FILE || '/app/data/reminders.json';

// Helper functions
function loadReminders() {
  if (!existsSync(REMINDERS_FILE)) {
    return { reminders: [] };
  }
  try {
    const data = readFileSync(REMINDERS_FILE, 'utf-8');
    return JSON.parse(data);
  } catch {
    return { reminders: [] };
  }
}

function saveReminders(data) {
  writeFileSync(REMINDERS_FILE, JSON.stringify(data, null, 2), 'utf-8');
}

function isOverdue(dueDate) {
  if (!dueDate) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return new Date(dueDate) < today;
}

/**
 * Parse JSON body from incoming request
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
 * GET /api/list - List reminders
 */
async function handleList(req, res) {
  try {
    const url = new URL(req.url, `http://localhost:${PORT}`);
    const showCompleted = url.searchParams.get('show_completed') === 'true';

    const data = loadReminders();
    let reminders = data.reminders;

    if (!showCompleted) {
      reminders = reminders.filter(r => !r.completed);
    }

    // Add overdue flag
    reminders = reminders.map(r => ({
      ...r,
      is_overdue: !r.completed && isOverdue(r.due_date)
    }));

    sendJson(res, 200, { reminders });
  } catch (err) {
    console.error('[http] List error:', err.message);
    sendJson(res, 500, { error: err.message });
  }
}

/**
 * POST /api/add - Add a reminder
 */
async function handleAdd(req, res) {
  try {
    const body = await parseBody(req);
    const { text, due_date } = body;

    if (!text || typeof text !== 'string') {
      return sendJson(res, 400, { error: 'Missing or invalid "text" field' });
    }

    const data = loadReminders();

    const reminder = {
      id: randomUUID().slice(0, 8),
      text: text.trim(),
      created_at: new Date().toISOString(),
      due_date: due_date || null,
      completed: false,
      completed_at: null
    };

    data.reminders.push(reminder);
    saveReminders(data);

    sendJson(res, 201, { id: reminder.id, text: reminder.text });
  } catch (err) {
    console.error('[http] Add error:', err.message);
    sendJson(res, 500, { error: err.message });
  }
}

/**
 * POST /api/complete - Complete a reminder
 */
async function handleComplete(req, res) {
  try {
    const body = await parseBody(req);
    const { id } = body;

    if (!id || typeof id !== 'string') {
      return sendJson(res, 400, { error: 'Missing or invalid "id" field' });
    }

    const data = loadReminders();
    const reminder = data.reminders.find(r => r.id === id);

    if (!reminder) {
      return sendJson(res, 404, { error: `Reminder with ID "${id}" not found` });
    }

    if (reminder.completed) {
      return sendJson(res, 200, { success: true, already_completed: true });
    }

    reminder.completed = true;
    reminder.completed_at = new Date().toISOString();
    saveReminders(data);

    sendJson(res, 200, { success: true });
  } catch (err) {
    console.error('[http] Complete error:', err.message);
    sendJson(res, 500, { error: err.message });
  }
}

/**
 * GET /api/summary - Get summary
 */
async function handleSummary(req, res) {
  try {
    const data = loadReminders();
    const reminders = data.reminders;

    const active = reminders.filter(r => !r.completed);
    const overdue = active.filter(r => isOverdue(r.due_date));

    const today = new Date().toDateString();
    const completedToday = reminders.filter(r =>
      r.completed && r.completed_at && new Date(r.completed_at).toDateString() === today
    );

    sendJson(res, 200, {
      active: active.length,
      overdue: overdue.length,
      completed_today: completedToday.length
    });
  } catch (err) {
    console.error('[http] Summary error:', err.message);
    sendJson(res, 500, { error: err.message });
  }
}

/**
 * POST /api/delete - Delete a reminder
 */
async function handleDelete(req, res) {
  try {
    const body = await parseBody(req);
    const { id } = body;

    if (!id || typeof id !== 'string') {
      return sendJson(res, 400, { error: 'Missing or invalid "id" field' });
    }

    const data = loadReminders();
    const index = data.reminders.findIndex(r => r.id === id);

    if (index === -1) {
      return sendJson(res, 404, { error: `Reminder with ID "${id}" not found` });
    }

    data.reminders.splice(index, 1);
    saveReminders(data);

    sendJson(res, 200, { success: true });
  } catch (err) {
    console.error('[http] Delete error:', err.message);
    sendJson(res, 500, { error: err.message });
  }
}

/**
 * Main request handler
 */
async function requestHandler(req, res) {
  const { method, url } = req;
  const pathname = new URL(url, `http://localhost:${PORT}`).pathname;

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
  if (method === 'GET' && pathname === '/api/list') {
    return handleList(req, res);
  }

  if (method === 'POST' && pathname === '/api/add') {
    return handleAdd(req, res);
  }

  if (method === 'POST' && pathname === '/api/complete') {
    return handleComplete(req, res);
  }

  if (method === 'GET' && pathname === '/api/summary') {
    return handleSummary(req, res);
  }

  if (method === 'POST' && pathname === '/api/delete') {
    return handleDelete(req, res);
  }

  // Health check
  if (method === 'GET' && pathname === '/health') {
    return sendJson(res, 200, { status: 'ok' });
  }

  // 404 for unknown routes
  sendJson(res, 404, { error: 'Not found' });
}

/**
 * Start the HTTP server
 */
async function main() {
  const server = http.createServer(requestHandler);

  server.listen(PORT, () => {
    console.error(`[http] Reminder HTTP server listening on port ${PORT}`);
    console.error(`[http] Data file: ${REMINDERS_FILE}`);
    console.error(`[http] Endpoints:`);
    console.error(`[http]   GET  /api/list?show_completed=true - List reminders`);
    console.error(`[http]   POST /api/add - Add reminder`);
    console.error(`[http]   POST /api/complete - Complete reminder`);
    console.error(`[http]   POST /api/delete - Delete reminder`);
    console.error(`[http]   GET  /api/summary - Get summary`);
    console.error(`[http]   GET  /health - Health check`);
  });
}

main().catch(err => {
  console.error('[http] Fatal error:', err);
  process.exit(1);
});
