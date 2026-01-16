"""HTTP client for Reminder MCP server."""

import logging
from dataclasses import dataclass
from typing import List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class Reminder:
    """Single reminder item."""

    id: str
    text: str
    due_date: Optional[str]
    completed: bool
    is_overdue: bool


@dataclass
class ReminderSummary:
    """Reminder statistics summary."""

    active: int
    overdue: int
    completed_today: int


class ReminderClient:
    """HTTP client for Reminder MCP server API."""

    def __init__(self, base_url: str):
        """Initialize Reminder client.

        Args:
            base_url: Reminder server base URL (e.g., http://localhost:3001)
        """
        self.base_url = base_url.rstrip("/")

    async def list(self, show_completed: bool = False) -> List[Reminder]:
        """Get list of reminders.

        Args:
            show_completed: Include completed reminders

        Returns:
            List of Reminder objects
        """
        url = f"{self.base_url}/api/list"
        if show_completed:
            url += "?show_completed=true"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        logger.error("Reminder list failed: %s", resp.status)
                        return []
                    data = await resp.json()
                    return [
                        Reminder(
                            id=r["id"],
                            text=r["text"],
                            due_date=r.get("due_date"),
                            completed=r.get("completed", False),
                            is_overdue=r.get("is_overdue", False),
                        )
                        for r in data.get("reminders", [])
                    ]
        except Exception as e:
            logger.error("Reminder list error: %s", e)
            return []

    async def add(self, text: str, due_date: Optional[str] = None) -> Optional[dict]:
        """Add a new reminder.

        Args:
            text: Reminder text
            due_date: Optional due date (ISO format)

        Returns:
            Created reminder dict or None on error
        """
        url = f"{self.base_url}/api/add"
        payload = {"text": text}
        if due_date:
            payload["due_date"] = due_date

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status not in (200, 201):
                        logger.error("Reminder add failed: %s", resp.status)
                        return None
                    return await resp.json()
        except Exception as e:
            logger.error("Reminder add error: %s", e)
            return None

    async def complete(self, reminder_id: str) -> bool:
        """Mark reminder as completed.

        Args:
            reminder_id: ID of the reminder to complete

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/api/complete"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"id": reminder_id},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error("Reminder complete error: %s", e)
            return False

    async def summary(self) -> Optional[ReminderSummary]:
        """Get reminder summary statistics.

        Returns:
            ReminderSummary or None on error
        """
        url = f"{self.base_url}/api/summary"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    return ReminderSummary(
                        active=data.get("active", 0),
                        overdue=data.get("overdue", 0),
                        completed_today=data.get("completed_today", 0),
                    )
        except Exception as e:
            logger.error("Reminder summary error: %s", e)
            return None
