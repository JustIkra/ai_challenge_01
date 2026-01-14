"""HTTP client for RAG server."""

import logging
from typing import List, Optional
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """Single RAG search result."""

    rank: int
    file_path: str
    file_type: str
    language: str
    similarity: float
    lines_count: int
    content: str

    @property
    def file_name(self) -> str:
        """Extract file name from path."""
        return self.file_path.split("/")[-1]


@dataclass
class RAGSearchResponse:
    """RAG search response."""

    results: List[RAGResult]
    count: int


class RAGClient:
    """HTTP client for RAG server API."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize RAG client.

        Args:
            base_url: RAG server base URL (e.g., http://rag-server:8801)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def search(
        self, query: str, limit: int = 5
    ) -> Optional[RAGSearchResponse]:
        """Search for relevant documents.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            RAGSearchResponse or None on error
        """
        url = f"{self.base_url}/api/search"
        payload = {
            "query": query,
            "limit": limit,
            "format": "json",
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        logger.error(
                            "RAG search failed: status=%d, body=%s",
                            response.status,
                            await response.text(),
                        )
                        return None

                    data = await response.json()
                    results = [
                        RAGResult(
                            rank=r.get("rank", 0),
                            file_path=r.get("file_path", ""),
                            file_type=r.get("file_type", ""),
                            language=r.get("language", ""),
                            similarity=r.get("similarity", 0.0),
                            lines_count=r.get("lines_count", 0),
                            content=r.get("content", ""),
                        )
                        for r in data.get("results", [])
                    ]
                    return RAGSearchResponse(
                        results=results,
                        count=data.get("count", len(results)),
                    )

        except aiohttp.ClientError as e:
            logger.error("RAG client error: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected RAG error: %s", e)
            return None

    async def status(self) -> Optional[dict]:
        """Get RAG server status.

        Returns:
            Status dict or None on error
        """
        url = f"{self.base_url}/api/status"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error("RAG status failed: status=%d", response.status)
                        return None
                    return await response.json()

        except Exception as e:
            logger.error("RAG status error: %s", e)
            return None
