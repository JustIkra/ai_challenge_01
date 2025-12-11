"""OpenRouter API async client with retry logic."""
import logging
import time
from typing import Any, Optional

import httpx

from ..schemas.request import GenerationParameters
from ..schemas.response import TokenUsage
from ..utils.retry import LocationError, RateLimitError, with_rate_limit_retry

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Async client for OpenRouter API with retry logic."""

    def __init__(
        self,
        base_url: str = "https://openrouter.ai/api/v1",
        proxy_url: Optional[str] = None,
        site_url: Optional[str] = None,
        site_name: Optional[str] = None,
    ):
        """Initialize OpenRouter client.

        Args:
            base_url: OpenRouter API base URL
            proxy_url: Optional HTTP proxy URL
            site_url: Optional site URL for HTTP-Referer header
            site_name: Optional site name for X-Title header
        """
        self.base_url = base_url.rstrip("/")
        self.proxy_url = proxy_url
        self.site_url = site_url
        self.site_name = site_name

        # Create async HTTP client with timeout and proxy
        timeout = httpx.Timeout(
            connect=10.0,
            read=120.0,
            write=10.0,
            pool=10.0,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            proxy=proxy_url,
            follow_redirects=True,
        )

        logger.info(
            f"OpenRouterClient initialized "
            f"(base_url: {self.base_url}, "
            f"proxy: {'enabled' if proxy_url else 'disabled'})"
        )

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
        """Generate content using OpenRouter API.

        Args:
            api_key: OpenRouter API key to use
            prompt: User prompt
            model: Model name (e.g., "google/gemini-2.5-flash")
            parameters: Generation parameters
            request_id: Request ID for logging
            system_instruction: Optional system instruction for the model

        Returns:
            Tuple of (generated_text, token_usage)

        Raises:
            RateLimitError: When rate limit (429) is hit
            LocationError: When location is not supported
            ValueError: For invalid API key or other client errors
            Exception: For other API errors
        """
        start_time = time.time()

        try:
            # Build messages array
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            # Convert GenerationParameters to OpenRouter format
            # Note: top_k is not supported by OpenRouter API, will be ignored
            request_body = {
                "model": model,
                "messages": messages,
            }

            # Add optional parameters only if they are set
            if parameters.temperature is not None:
                request_body["temperature"] = parameters.temperature
            if parameters.top_p is not None:
                request_body["top_p"] = parameters.top_p
            if parameters.max_output_tokens is not None:
                request_body["max_tokens"] = parameters.max_output_tokens
            if parameters.stop_sequences:
                request_body["stop"] = parameters.stop_sequences

            # Build headers
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            if self.site_url:
                headers["HTTP-Referer"] = self.site_url
            if self.site_name:
                headers["X-Title"] = self.site_name

            logger.debug(
                f"[{request_id}] Generating content with model={model}, "
                f"temperature={parameters.temperature}, "
                f"max_tokens={parameters.max_output_tokens}"
            )

            # Make API request
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=request_body,
                headers=headers,
            )

            # Handle response status codes
            if response.status_code == 429:
                logger.warning(
                    f"[{request_id}] Rate limit hit "
                    f"(key: {api_key[:8]}..., status: 429)"
                )
                raise RateLimitError(
                    f"Rate limit exceeded: {response.text}"
                )

            if response.status_code == 401:
                logger.error(
                    f"[{request_id}] Invalid API key "
                    f"(key: {api_key[:8]}...)"
                )
                raise ValueError(
                    f"Invalid API key: {response.text}"
                )

            if response.status_code == 400:
                error_detail = response.text
                logger.error(
                    f"[{request_id}] Bad request: {error_detail}"
                )
                raise ValueError(
                    f"Bad request to OpenRouter API: {error_detail}"
                )

            if response.status_code >= 500:
                logger.error(
                    f"[{request_id}] Server error: {response.status_code}"
                )
                raise Exception(
                    f"OpenRouter server error ({response.status_code}): {response.text}"
                )

            if response.status_code != 200:
                logger.error(
                    f"[{request_id}] Unexpected status code: {response.status_code}"
                )
                raise Exception(
                    f"Unexpected response from OpenRouter ({response.status_code}): {response.text}"
                )

            # Parse response JSON
            response_data = response.json()

            # Extract generated text
            choices = response_data.get("choices", [])
            if not choices:
                logger.error(
                    f"[{request_id}] Empty choices in response"
                )
                raise ValueError("Empty choices in OpenRouter API response")

            first_choice = choices[0]
            message = first_choice.get("message", {})
            generated_text = message.get("content", "")
            finish_reason = first_choice.get("finish_reason")

            if not generated_text:
                detail_msg = f" (finish_reason={finish_reason})" if finish_reason else ""
                logger.error(
                    f"[{request_id}] Empty response from OpenRouter API{detail_msg}"
                )
                raise ValueError(f"Empty response from OpenRouter API{detail_msg}")

            # Log warning if response was truncated due to max tokens
            if finish_reason == "length":
                logger.warning(
                    f"[{request_id}] Response truncated due to max_tokens limit "
                    f"(limit: {parameters.max_output_tokens})"
                )

            # Extract token usage
            usage = response_data.get("usage", {})
            token_usage = TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

            elapsed_time = (time.time() - start_time) * 1000
            logger.info(
                f"[{request_id}] Content generated successfully | "
                f"model={model} | "
                f"prompt_tokens={token_usage.prompt_tokens} | "
                f"completion_tokens={token_usage.completion_tokens} | "
                f"total_tokens={token_usage.total_tokens} | "
                f"time_ms={elapsed_time:.2f}"
            )

            return generated_text, token_usage

        except (RateLimitError, LocationError, ValueError):
            # Re-raise known exceptions as-is
            raise

        except httpx.HTTPStatusError as e:
            elapsed_time = (time.time() - start_time) * 1000
            error_msg = str(e).lower()

            # Check for location errors
            if "location" in error_msg or "region" in error_msg:
                logger.warning(
                    f"[{request_id}] API blocked by location. "
                    f"Proxy may have failed, will retry... "
                    f"(proxy: {self.proxy_url or 'none'})"
                )
                raise LocationError(
                    "OpenRouter API rejected the request because the location is not supported. "
                    "Proxy connection may be unstable."
                ) from e

            logger.error(
                f"[{request_id}] HTTP error "
                f"(key: {api_key[:8]}..., time: {elapsed_time:.2f}ms): {e}"
            )
            raise

        except httpx.TimeoutException as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] Request timeout "
                f"(key: {api_key[:8]}..., time: {elapsed_time:.2f}ms): {e}"
            )
            raise Exception(f"Request timeout: {e}") from e

        except httpx.RequestError as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] Request error "
                f"(key: {api_key[:8]}..., time: {elapsed_time:.2f}ms): {e}"
            )
            raise Exception(f"Request error: {e}") from e

        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            error_msg = str(e).lower()

            # Check for rate limit errors in exception message
            if "429" in error_msg or "rate limit" in error_msg or "quota" in error_msg:
                logger.warning(
                    f"[{request_id}] Rate limit hit "
                    f"(key: {api_key[:8]}..., time: {elapsed_time:.2f}ms): {e}"
                )
                raise RateLimitError(f"Rate limit exceeded: {e}")

            # Check for location errors
            if "location" in error_msg or "region" in error_msg:
                logger.warning(
                    f"[{request_id}] API blocked by location. "
                    f"Proxy may have failed, will retry... "
                    f"(proxy: {self.proxy_url or 'none'})"
                )
                raise LocationError(
                    "OpenRouter API rejected the request because the location is not supported. "
                    "Proxy connection may be unstable."
                ) from e

            logger.error(
                f"[{request_id}] API error "
                f"(key: {api_key[:8]}..., time: {elapsed_time:.2f}ms): {e}"
            )
            raise

    async def close(self) -> None:
        """Cleanup client resources."""
        await self._client.aclose()
        logger.info("OpenRouterClient closed")


# Alias for backward compatibility
GeminiAsyncClient = OpenRouterClient
