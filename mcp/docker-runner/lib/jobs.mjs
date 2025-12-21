// jobs.mjs - Background job manager using child_process.spawn

import { spawn } from 'child_process';
import { randomUUID } from 'crypto';

class JobManager {
  constructor() {
    this.jobs = new Map(); // jobId -> { process, name, stdout[], stderr[], status, startedAt, exitCode }
    this.MAX_BUFFER_LINES = 10000;
  }

  /**
   * Start a background job
   * @param {string} command - Command to execute (e.g., "docker compose logs -f backend")
   * @param {string|null} name - Optional friendly name
   * @returns {{ jobId: string, name: string, pid: number }}
   */
  start(command, name = null) {
    const jobId = randomUUID().slice(0, 8);

    // Use shell: true with the full command string to avoid deprecation warning
    // about passing args with shell option
    const proc = spawn(command, {
      shell: true,
      cwd: process.env.PROJECT_DIR || process.cwd()
    });

    const job = {
      process: proc,
      name: name || command,
      stdout: [],
      stderr: [],
      status: 'running',
      startedAt: new Date().toISOString(),
      exitCode: null
    };

    // Handle stdout data
    proc.stdout.on('data', (data) => {
      const lines = data.toString().split('\n').filter(line => line.length > 0);
      for (const line of lines) {
        job.stdout.push(line);
        // Trim buffer if it exceeds max lines
        if (job.stdout.length > this.MAX_BUFFER_LINES) {
          job.stdout.shift();
        }
      }
    });

    // Handle stderr data
    proc.stderr.on('data', (data) => {
      const lines = data.toString().split('\n').filter(line => line.length > 0);
      for (const line of lines) {
        job.stderr.push(line);
        // Trim buffer if it exceeds max lines
        if (job.stderr.length > this.MAX_BUFFER_LINES) {
          job.stderr.shift();
        }
      }
    });

    // Handle process close
    proc.on('close', (code) => {
      job.exitCode = code;
      job.status = code === 0 ? 'completed' : 'failed';
    });

    // Handle process error
    proc.on('error', (err) => {
      job.stderr.push(`Process error: ${err.message}`);
      job.status = 'failed';
    });

    this.jobs.set(jobId, job);

    return {
      jobId,
      name: job.name,
      pid: proc.pid
    };
  }

  /**
   * Stop a job by killing the process
   * @param {string} jobId - Job ID to stop
   * @returns {{ success: boolean, message: string }}
   */
  stop(jobId) {
    const job = this.jobs.get(jobId);

    if (!job) {
      return {
        success: false,
        message: `Job ${jobId} not found`
      };
    }

    if (job.status !== 'running') {
      return {
        success: false,
        message: `Job ${jobId} is not running (status: ${job.status})`
      };
    }

    try {
      job.process.kill('SIGTERM');
      job.status = 'stopped';
      return {
        success: true,
        message: `Job ${jobId} stopped`
      };
    } catch (err) {
      return {
        success: false,
        message: `Failed to stop job ${jobId}: ${err.message}`
      };
    }
  }

  /**
   * Get output from a job
   * @param {string} jobId - Job ID
   * @param {number} lines - Number of last lines to return (default 50)
   * @returns {{ jobId: string, status: string, stdout: string[], stderr: string[], exitCode?: number }|null}
   */
  getOutput(jobId, lines = 50) {
    const job = this.jobs.get(jobId);

    if (!job) {
      return null;
    }

    return {
      jobId,
      status: job.status,
      stdout: job.stdout.slice(-lines),
      stderr: job.stderr.slice(-lines),
      ...(job.exitCode !== null && { exitCode: job.exitCode })
    };
  }

  /**
   * List all jobs
   * @returns {Array<{ jobId: string, name: string, status: string, pid: number, startedAt: string }>}
   */
  list() {
    const result = [];

    for (const [jobId, job] of this.jobs) {
      result.push({
        jobId,
        name: job.name,
        status: job.status,
        pid: job.process.pid,
        startedAt: job.startedAt
      });
    }

    return result;
  }
}

// Singleton instance
export const jobManager = new JobManager();
