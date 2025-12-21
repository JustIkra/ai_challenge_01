#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import {
  composeUp,
  composeDown,
  composePs,
  composeBuild,
  composeLogs,
  composeRestart,
  composeExec
} from "./lib/compose.mjs";
import { jobManager } from "./lib/jobs.mjs";

// Server setup
const server = new McpServer({
  name: "docker-runner-mcp",
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

// Tool: compose_up
server.registerTool(
  "compose_up",
  {
    description: "Start containers with docker compose up -d. Optionally specify a single service.",
    inputSchema: {
      service: z.string().optional().describe("Service name to start (optional, starts all if not specified)")
    }
  },
  async ({ service }) => {
    const result = composeUp(service);
    return formatResult(result);
  }
);

// Tool: compose_down
server.registerTool(
  "compose_down",
  {
    description: "Stop containers with docker compose down. Optionally remove volumes.",
    inputSchema: {
      volumes: z.boolean().optional().describe("Remove volumes (default: false)")
    }
  },
  async ({ volumes }) => {
    const result = composeDown(volumes);
    return formatResult(result);
  }
);

// Tool: compose_ps
server.registerTool(
  "compose_ps",
  {
    description: "List all containers with docker compose ps -a."
  },
  async () => {
    const result = composePs();
    return formatResult(result);
  }
);

// Tool: compose_build
server.registerTool(
  "compose_build",
  {
    description: "Build and start containers with docker compose up -d --build. Optionally specify a single service.",
    inputSchema: {
      service: z.string().optional().describe("Service name to build (optional, builds all if not specified)")
    }
  },
  async ({ service }) => {
    const result = composeBuild(service);
    return formatResult(result);
  }
);

// Tool: compose_logs
server.registerTool(
  "compose_logs",
  {
    description: "Get logs from a service with docker compose logs --tail=N.",
    inputSchema: {
      service: z.string().describe("Service name to get logs from"),
      lines: z.number().optional().describe("Number of lines to tail (default: 100)")
    }
  },
  async ({ service, lines }) => {
    const result = composeLogs(service, lines);
    return formatResult(result);
  }
);

// Tool: compose_restart
server.registerTool(
  "compose_restart",
  {
    description: "Restart a service with docker compose restart.",
    inputSchema: {
      service: z.string().describe("Service name to restart")
    }
  },
  async ({ service }) => {
    const result = composeRestart(service);
    return formatResult(result);
  }
);

// Tool: compose_exec
server.registerTool(
  "compose_exec",
  {
    description: "Execute a command in a running container with docker compose exec -T.",
    inputSchema: {
      service: z.string().describe("Service name"),
      command: z.string().describe("Command to execute in the container"),
      workdir: z.string().optional().describe("Working directory inside the container (optional)")
    }
  },
  async ({ service, command, workdir }) => {
    const result = composeExec(service, command, workdir);
    return formatResult(result);
  }
);

// ============================================================================
// Job Tools - Background job management
// ============================================================================

// Tool: job_start
server.registerTool(
  "job_start",
  {
    description: "Start a long-running command in the background (e.g., docker compose logs -f).",
    inputSchema: {
      command: z.string().describe("Command to run in background"),
      name: z.string().optional().describe("Friendly name for the job (optional)")
    }
  },
  async ({ command, name }) => {
    const result = jobManager.start(command, name);
    return {
      content: [{
        type: "text",
        text: `Job started:\n- ID: ${result.jobId}\n- Name: ${result.name}\n- PID: ${result.pid}`
      }]
    };
  }
);

// Tool: job_list
server.registerTool(
  "job_list",
  {
    description: "List all background jobs with their status."
  },
  async () => {
    const jobs = jobManager.list();
    if (jobs.length === 0) {
      return {
        content: [{ type: "text", text: "No jobs running." }]
      };
    }
    const lines = jobs.map(j =>
      `[${j.status}] ${j.jobId}: ${j.name} (PID: ${j.pid}, started: ${j.startedAt})`
    );
    return {
      content: [{ type: "text", text: lines.join("\n") }]
    };
  }
);

// Tool: job_logs
server.registerTool(
  "job_logs",
  {
    description: "Get output from a background job.",
    inputSchema: {
      job_id: z.string().describe("Job ID"),
      lines: z.number().optional().describe("Number of lines to return (default: 50)")
    }
  },
  async ({ job_id, lines }) => {
    const output = jobManager.getOutput(job_id, lines);
    if (!output) {
      return {
        content: [{ type: "text", text: `Job ${job_id} not found.` }]
      };
    }
    const parts = [`Status: ${output.status}`];
    if (output.exitCode !== undefined) {
      parts.push(`Exit code: ${output.exitCode}`);
    }
    if (output.stdout.length > 0) {
      parts.push(`\n--- stdout ---\n${output.stdout.join("\n")}`);
    }
    if (output.stderr.length > 0) {
      parts.push(`\n--- stderr ---\n${output.stderr.join("\n")}`);
    }
    return {
      content: [{ type: "text", text: parts.join("\n") }]
    };
  }
);

// Tool: job_stop
server.registerTool(
  "job_stop",
  {
    description: "Stop a running background job.",
    inputSchema: {
      job_id: z.string().describe("Job ID to stop")
    }
  },
  async ({ job_id }) => {
    const result = jobManager.stop(job_id);
    return {
      content: [{ type: "text", text: result.message }]
    };
  }
);

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(error => {
  console.error("Server error:", error);
  process.exit(1);
});
