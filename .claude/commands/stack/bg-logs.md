---
description: Start background log viewer
argument-hint: <service>
---

Start following logs for service $1 in background.
Use MCP tool `job_start` from docker-runner server.
Command: "docker compose logs -f $1"
Name: "logs-$1"

Return the jobId so user can check with /stack-jobs or stop it.
