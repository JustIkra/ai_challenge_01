---
description: Manage background jobs
argument-hint: [jobId] [action]
---

Manage background jobs.
Use MCP tools from docker-runner server:

If no arguments: use `job_list` to show all jobs.
If jobId provided without action: use `job_logs` to show output.
If jobId and "stop" action: use `job_stop` to terminate job.
