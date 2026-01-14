"""OpenRouter API client for LLM inference."""

import logging
import random
from typing import List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenRouter API client with key rotation."""

    def __init__(
        self,
        api_keys: List[str],
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "anthropic/claude-3-haiku",
        timeout: float = 60.0,
    ):
        """Initialize LLM client.

        Args:
            api_keys: List of OpenRouter API keys
            base_url: OpenRouter API base URL
            model: Model identifier
            timeout: Request timeout in seconds
        """
        self.api_keys = api_keys
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._current_key_index = 0

    def _get_next_key(self) -> str:
        """Get next API key (round-robin rotation)."""
        key = self.api_keys[self._current_key_index]
        self._current_key_index = (self._current_key_index + 1) % len(self.api_keys)
        return key

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 2000,
    ) -> Optional[str]:
        """Send chat completion request.

        Args:
            system_prompt: System prompt
            user_message: User message
            max_tokens: Maximum response tokens

        Returns:
            Response text or None on error
        """
        url = f"{self.base_url}/chat/completions"
        api_key = self._get_next_key()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/day1-app/support-bot",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            "LLM request failed: status=%d, body=%s",
                            response.status,
                            error_text,
                        )
                        return None

                    data = await response.json()
                    choices = data.get("choices", [])
                    if not choices:
                        logger.error("LLM response has no choices")
                        return None

                    message = choices[0].get("message", {})
                    return message.get("content")

        except aiohttp.ClientError as e:
            logger.error("LLM client error: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected LLM error: %s", e)
            return None
