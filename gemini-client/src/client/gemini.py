"""Gemini API async client with retry logic."""
import logging
import os
import time
from typing import Any, Optional

from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig

from ..schemas.request import GenerationParameters
from ..schemas.response import TokenUsage
from ..utils.retry import LocationError, RateLimitError, with_rate_limit_retry

logger = logging.getLogger(__name__)


class GeminiAsyncClient:
    """Async client for Gemini API with retry logic."""

    def __init__(self, proxy_url: Optional[str] = None):
        """Initialize Gemini client.

        Args:
            proxy_url: Optional HTTP proxy URL
        """
        self.proxy_url = proxy_url
        self._setup_proxy()

        logger.info(
            f"GeminiAsyncClient initialized "
            f"(proxy: {'enabled' if proxy_url else 'disabled'})"
        )

    def _setup_proxy(self) -> None:
        """Setup HTTP proxy environment variables if configured."""
        if self.proxy_url:
            os.environ["HTTP_PROXY"] = self.proxy_url
            os.environ["HTTPS_PROXY"] = self.proxy_url
            os.environ["http_proxy"] = self.proxy_url
            os.environ["https_proxy"] = self.proxy_url
            logger.info(f"HTTP proxy configured: {self.proxy_url}")

    @with_rate_limit_retry(max_retries=3, base_delay=5.0, max_delay=60.0)
    async def generate_content(
        self,
        api_key: str,
        prompt: str,
        model: str,
        parameters: GenerationParameters,
        request_id: str,
        system_instruction: str | None = None,
    ) -> tuple[str, TokenUsage]:
        """Generate content using Gemini API.

        Args:
            api_key: Gemini API key to use
            prompt: User prompt
            model: Model name (e.g., "gemini-pro")
            parameters: Generation parameters
            request_id: Request ID for logging
            system_instruction: Optional system instruction for the model

        Returns:
            Tuple of (generated_text, token_usage)

        Raises:
            RateLimitError: When rate limit (429) is hit
            Exception: For other API errors
        """
        start_time = time.time()

        try:
            # Create client with API key
            http_options = (
                types.HttpOptions(
                    client_args={"proxy": self.proxy_url},
                    async_client_args={"proxy": self.proxy_url},
                )
                if self.proxy_url
                else None
            )
            client = genai.Client(api_key=api_key, http_options=http_options)

            # Prepare generation config
            config = GenerateContentConfig(
                temperature=parameters.temperature,
                top_p=parameters.top_p,
                top_k=parameters.top_k,
                max_output_tokens=parameters.max_output_tokens,
                candidate_count=parameters.candidate_count,
                stop_sequences=parameters.stop_sequences,
                system_instruction=system_instruction,
            )

            logger.debug(
                f"[{request_id}] Generating content with model={model}, "
                f"temperature={parameters.temperature}, "
                f"max_tokens={parameters.max_output_tokens}"
            )

            # Generate content
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )

            # Extract text from response
            generated_text = self._extract_text_from_response(response)
            finish_reason = self._get_finish_reason(response)
            usage_metadata = getattr(response, "usage_metadata", None)

            if not generated_text:
                details = []
                if finish_reason:
                    details.append(f"finish_reason={finish_reason}")
                detail_msg = f" ({'; '.join(details)})" if details else ""
                logger.error(
                    f"[{request_id}] Empty response from Gemini API{detail_msg}"
                )
                raise ValueError(f"Empty response from Gemini API{detail_msg}")

            # Log warning if response was truncated due to max tokens
            if finish_reason and "MAX_TOKENS" in str(finish_reason):
                logger.warning(
                    f"[{request_id}] Response truncated due to max_output_tokens limit "
                    f"(limit: {parameters.max_output_tokens})"
                )

            # Extract token usage (already captured from streaming)
            if usage_metadata:
                token_usage = TokenUsage(
                    prompt_tokens=getattr(usage_metadata, "prompt_token_count", 0),
                    completion_tokens=getattr(usage_metadata, "candidates_token_count", 0),
                    total_tokens=getattr(usage_metadata, "total_token_count", 0),
                )
            else:
                # Fallback if usage metadata not available
                token_usage = TokenUsage(
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                )

            elapsed_time = (time.time() - start_time) * 1000
            logger.info(
                f"[{request_id}] Content generated successfully "
                f"(tokens: {token_usage.total_tokens}, time: {elapsed_time:.2f}ms)"
            )

            return generated_text, token_usage

        except Exception as e:
            error_msg = str(e).lower()
            elapsed_time = (time.time() - start_time) * 1000

            if "user location is not supported for the api use" in error_msg:
                logger.warning(
                    f"[{request_id}] Gemini API blocked by location. "
                    f"Proxy may have failed, will retry... "
                    f"(proxy: {self.proxy_url or 'none'})"
                )
                raise LocationError(
                    "Gemini API rejected the request because the location is not supported. "
                    "Proxy connection may be unstable."
                ) from e

            # Check for rate limit errors
            if "429" in error_msg or "rate limit" in error_msg or "quota" in error_msg:
                logger.warning(
                    f"[{request_id}] Rate limit hit "
                    f"(key: {api_key[:8]}..., time: {elapsed_time:.2f}ms): {e}"
                )
                raise RateLimitError(f"Rate limit exceeded: {e}")

            # Check for other errors
            logger.error(
                f"[{request_id}] API error "
                f"(key: {api_key[:8]}..., time: {elapsed_time:.2f}ms): {e}"
            )
            raise

    async def close(self) -> None:
        """Cleanup client resources."""
        # Clean up proxy environment variables if set
        if self.proxy_url:
            os.environ.pop("HTTP_PROXY", None)
            os.environ.pop("HTTPS_PROXY", None)
            os.environ.pop("http_proxy", None)
            os.environ.pop("https_proxy", None)

        logger.info("GeminiAsyncClient closed")

    def _extract_text_from_response(self, response: Any) -> str | None:
        """Extract text from Gemini response, handling various response formats.

        The SDK's response.text property may return None when finish_reason is
        MAX_TOKENS, but the content might still be in candidates[0].content.parts.
        """
        # First try the simple text property
        text = getattr(response, "text", None)
        if text:
            return text

        # Fallback: extract from candidates directly
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None

        first_candidate = candidates[0]
        content = getattr(first_candidate, "content", None)
        if not content:
            return None

        parts = getattr(content, "parts", None) or []
        if not parts:
            return None

        # Concatenate text from all parts
        text_parts = []
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                text_parts.append(part_text)

        return "".join(text_parts) if text_parts else None

    def _get_finish_reason(self, response: Any) -> Any:
        """Extract finish_reason from response candidates."""
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            return getattr(candidates[0], "finish_reason", None)
        return None

    def _format_empty_response_details(self, response: Any) -> str:
        """Build human-readable details when API returns no text."""
        details: list[str] = []

        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback:
            block_reason = getattr(prompt_feedback, "block_reason", None)
            if block_reason:
                details.append(f"block_reason={block_reason}")
            safety_ratings = getattr(prompt_feedback, "safety_ratings", None) or []
            safety_summary = self._format_safety_ratings(safety_ratings)
            if safety_summary:
                details.append(f"prompt_safety={safety_summary}")

        candidates = getattr(response, "candidates", None) or []
        if candidates:
            first_candidate = candidates[0]
            finish_reason = getattr(first_candidate, "finish_reason", None)
            if finish_reason:
                details.append(f"finish_reason={finish_reason}")
            safety_ratings = getattr(first_candidate, "safety_ratings", None) or []
            safety_summary = self._format_safety_ratings(safety_ratings)
            if safety_summary:
                details.append(f"candidate_safety={safety_summary}")

        return f" ({'; '.join(details)})" if details else ""

    @staticmethod
    def _format_safety_ratings(ratings: Any) -> str:
        """Format safety ratings list into a readable string."""
        formatted = []
        for rating in ratings or []:
            category = getattr(rating, "category", "unknown")
            probability = getattr(rating, "probability", "unknown")
            formatted.append(f"{category}:{probability}")
        return ", ".join(formatted)
