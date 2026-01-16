"""Configuration from environment variables."""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Bot configuration."""

    # Telegram
    telegram_bot_token: str

    # RAG Server
    rag_server_url: str
    rag_top_k: int

    # Reminder MCP Server
    reminder_server_url: str

    # OpenRouter
    openrouter_api_keys: List[str]
    openrouter_base_url: str
    openrouter_model: str

    # Limits
    max_input_length: int
    max_output_length: int

    # Timeouts
    agent_timeout: float

    # Paths
    system_prompt_path: Path

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        openrouter_keys_str = os.getenv("OPENROUTER_API_KEYS", "")
        openrouter_keys = [k.strip() for k in openrouter_keys_str.split(",") if k.strip()]
        if not openrouter_keys:
            raise ValueError("OPENROUTER_API_KEYS is required")

        return cls(
            telegram_bot_token=telegram_token,
            rag_server_url=os.getenv("RAG_SERVER_URL", "http://rag-server:8801"),
            rag_top_k=int(os.getenv("RAG_TOP_K", "5")),
            reminder_server_url=os.getenv("REMINDER_SERVER_URL", ""),
            openrouter_api_keys=openrouter_keys,
            openrouter_base_url=os.getenv(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ),
            openrouter_model=os.getenv(
                "OPENROUTER_MODEL", "anthropic/claude-3-haiku"
            ),
            max_input_length=int(os.getenv("MAX_INPUT_LENGTH", "1000")),
            max_output_length=int(os.getenv("MAX_OUTPUT_LENGTH", "4000")),
            agent_timeout=float(os.getenv("AGENT_TIMEOUT", "30.0")),
            system_prompt_path=Path(__file__).parent / "prompts" / "system.txt",
        )

    def get_system_prompt(self) -> str:
        """Load system prompt from file."""
        return self.system_prompt_path.read_text(encoding="utf-8")


# Global config instance
config = Config.from_env() if os.getenv("TELEGRAM_BOT_TOKEN") else None


def get_config() -> Config:
    """Get or create config instance."""
    global config
    if config is None:
        config = Config.from_env()
    return config
