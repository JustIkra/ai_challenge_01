"""Client for Docker Compose container status."""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class ContainerStatus:
    """Docker container status."""

    name: str
    state: str
    status: str


class DockerClient:
    """Client for querying Docker Compose container status."""

    async def get_status(self) -> List[ContainerStatus]:
        """Get Docker Compose container statuses.

        Returns:
            List of ContainerStatus objects
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "compose",
                "ps",
                "--format",
                "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

            if proc.returncode != 0:
                logger.error("docker compose ps failed: %s", stderr.decode())
                return []

            output = stdout.decode().strip()
            if not output:
                return []

            # Docker outputs one JSON object per line
            containers = []
            for line in output.split("\n"):
                if line.strip():
                    try:
                        data = json.loads(line)
                        containers.append(
                            ContainerStatus(
                                name=data.get("Name", data.get("Service", "unknown")),
                                state=data.get("State", "unknown"),
                                status=data.get("Status", "unknown"),
                            )
                        )
                    except json.JSONDecodeError:
                        continue

            return containers
        except asyncio.TimeoutError:
            logger.error("Docker status timeout")
            return []
        except FileNotFoundError:
            logger.error("Docker not found")
            return []
        except Exception as e:
            logger.error("Docker status error: %s", e)
            return []
