"""Tests for OpenRouterClient (GeminiAsyncClient)."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from src.client.gemini import GeminiAsyncClient, OpenRouterClient
from src.schemas.request import GenerationParameters
from src.schemas.response import TokenUsage
from src.utils.retry import LocationError, RateLimitError


@pytest.fixture
def generation_params():
    """Fixture for generation parameters."""
    return GenerationParameters(
        temperature=0.7,
        top_p=0.95,
        top_k=40,
        max_output_tokens=2048,
    )


@pytest.fixture
def client():
    """Fixture for OpenRouter client."""
    return GeminiAsyncClient(
        base_url="https://openrouter.ai/api/v1",
        proxy_url=None,
    )


@pytest.fixture
def client_with_proxy():
    """Fixture for OpenRouter client with proxy."""
    return GeminiAsyncClient(
        base_url="https://openrouter.ai/api/v1",
        proxy_url="http://localhost:8080",
    )


@pytest.mark.asyncio
async def test_client_initialization(client):
    """Test client initialization without proxy."""
    assert client.proxy_url is None
    assert client.base_url == "https://openrouter.ai/api/v1"


@pytest.mark.asyncio
async def test_client_initialization_with_proxy(client_with_proxy):
    """Test client initialization with proxy."""
    assert client_with_proxy.proxy_url == "http://localhost:8080"


@pytest.mark.asyncio
async def test_generate_content_success(client, generation_params):
    """Test successful content generation."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"

    # Mock OpenRouter API response
    mock_response_data = {
        "id": "test-id",
        "model": "google/gemini-2.5-flash",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Python is a high-level programming language...",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 150,
            "total_tokens": 160,
        },
    }

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        # Setup mock response (use MagicMock because response.json() is sync in httpx)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        # Call generate_content
        content, usage = await client.generate_content(
            api_key=api_key,
            prompt=prompt,
            model=model,
            parameters=generation_params,
            request_id=request_id,
        )

        # Verify results
        assert content == "Python is a high-level programming language..."
        assert isinstance(usage, TokenUsage)
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 150
        assert usage.total_tokens == 160

        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openrouter.ai/api/v1/chat/completions"
        assert call_args[1]["json"]["model"] == model
        assert call_args[1]["json"]["messages"][0]["role"] == "user"
        assert call_args[1]["json"]["messages"][0]["content"] == prompt


@pytest.mark.asyncio
async def test_generate_content_with_system_instruction(client, generation_params):
    """Test content generation with system instruction."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"
    system_instruction = "You are a helpful assistant."

    mock_response_data = {
        "id": "test-id",
        "model": "google/gemini-2.5-flash",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Python is a programming language.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 50,
            "total_tokens": 65,
        },
    }

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        await client.generate_content(
            api_key=api_key,
            prompt=prompt,
            model=model,
            parameters=generation_params,
            request_id=request_id,
            system_instruction=system_instruction,
        )

        # Verify system message is included
        call_args = mock_post.call_args
        messages = call_args[1]["json"]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == system_instruction
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == prompt


@pytest.mark.asyncio
async def test_generate_content_rate_limit(client, generation_params):
    """Test rate limit error handling (429 status)."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        # Simulate 429 error
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_post.return_value = mock_response

        # Should raise RateLimitError
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )


@pytest.mark.asyncio
async def test_generate_content_invalid_api_key(client, generation_params):
    """Test invalid API key error handling (401 status)."""
    request_id = str(uuid4())
    api_key = "invalid_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        # Simulate 401 error
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_post.return_value = mock_response

        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid API key"):
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )


@pytest.mark.asyncio
async def test_generate_content_bad_request(client, generation_params):
    """Test bad request error handling (400 status)."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "invalid-model"

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        # Simulate 400 error
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid model specified"
        mock_post.return_value = mock_response

        # Should raise ValueError
        with pytest.raises(ValueError, match="Bad request to OpenRouter API"):
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )


@pytest.mark.asyncio
async def test_generate_content_server_error(client, generation_params):
    """Test server error handling (500 status)."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        # Simulate 500 error
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        # Should raise Exception
        with pytest.raises(Exception, match="OpenRouter server error"):
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )


@pytest.mark.asyncio
async def test_generate_content_empty_response(client, generation_params):
    """Test handling of empty response content."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"

    # Mock empty response (no content in message)
    mock_response_data = {
        "id": "test-id",
        "model": "google/gemini-2.5-flash",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",  # Empty content
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 0,
            "total_tokens": 10,
        },
    }

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        # Should raise ValueError for empty response
        with pytest.raises(ValueError, match="Empty response from OpenRouter API"):
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )


@pytest.mark.asyncio
async def test_generate_content_empty_choices(client, generation_params):
    """Test handling of empty choices array."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"

    # Mock response with empty choices
    mock_response_data = {
        "id": "test-id",
        "model": "google/gemini-2.5-flash",
        "choices": [],  # Empty choices
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 0,
            "total_tokens": 10,
        },
    }

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        # Should raise ValueError for empty choices
        with pytest.raises(ValueError, match="Empty choices in OpenRouter API response"):
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )


@pytest.mark.asyncio
async def test_generate_content_no_usage_metadata(client, generation_params):
    """Test handling when usage metadata is not available."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"

    # Mock response without usage metadata
    mock_response_data = {
        "id": "test-id",
        "model": "google/gemini-2.5-flash",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Python is great!",
                },
                "finish_reason": "stop",
            }
        ],
        # No usage field
    }

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        # Call generate_content
        content, usage = await client.generate_content(
            api_key=api_key,
            prompt=prompt,
            model=model,
            parameters=generation_params,
            request_id=request_id,
        )

        # Should return zero usage when metadata not available
        assert content == "Python is great!"
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


@pytest.mark.asyncio
async def test_generate_content_truncated_by_length(client, generation_params):
    """Test warning when response is truncated due to max tokens."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"

    # Mock response with finish_reason="length"
    mock_response_data = {
        "id": "test-id",
        "model": "google/gemini-2.5-flash",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Python is a high-level...",
                },
                "finish_reason": "length",  # Truncated
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 2048,
            "total_tokens": 2058,
        },
    }

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        # Should succeed but log warning
        content, usage = await client.generate_content(
            api_key=api_key,
            prompt=prompt,
            model=model,
            parameters=generation_params,
            request_id=request_id,
        )

        assert content == "Python is a high-level..."
        assert usage.completion_tokens == 2048


@pytest.mark.asyncio
async def test_client_close(client):
    """Test client cleanup."""
    with patch.object(client._client, "aclose", new_callable=AsyncMock) as mock_aclose:
        await client.close()
        mock_aclose.assert_called_once()


@pytest.mark.asyncio
async def test_authorization_header_is_set(client, generation_params):
    """Test that Authorization header is properly set."""
    request_id = str(uuid4())
    api_key = "sk-test-api-key-12345"
    prompt = "Test prompt"
    model = "google/gemini-2.5-flash"

    mock_response_data = {
        "id": "test-id",
        "model": "google/gemini-2.5-flash",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Test response"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
    }

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        await client.generate_content(
            api_key=api_key,
            prompt=prompt,
            model=model,
            parameters=generation_params,
            request_id=request_id,
        )

        # Verify Authorization header
        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {api_key}"
        assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_site_headers_are_set():
    """Test that site URL and name headers are properly set."""
    client = OpenRouterClient(
        base_url="https://openrouter.ai/api/v1",
        proxy_url=None,
        site_url="https://example.com",
        site_name="Example App",
    )

    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Test prompt"
    model = "google/gemini-2.5-flash"
    generation_params = GenerationParameters(temperature=0.7)

    mock_response_data = {
        "id": "test-id",
        "model": "google/gemini-2.5-flash",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Test response"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
    }

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        await client.generate_content(
            api_key=api_key,
            prompt=prompt,
            model=model,
            parameters=generation_params,
            request_id=request_id,
        )

        # Verify site headers
        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert headers["HTTP-Referer"] == "https://example.com"
        assert headers["X-Title"] == "Example App"


@pytest.mark.asyncio
async def test_generate_content_location_error_in_exception_message(
    client, generation_params
):
    """Test location error detection from exception message."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "test"
    model = "google/gemini-2.5-flash"

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        # Simulate exception with location error message
        mock_post.side_effect = Exception(
            "User location is not supported for the API use."
        )

        with pytest.raises(LocationError) as exc_info:
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )

        msg = str(exc_info.value)
        assert "location is not supported" in msg
        assert "Proxy" in msg


@pytest.mark.asyncio
async def test_generate_content_empty_response_with_finish_reason(
    client, generation_params
):
    """Test that finish_reason is included in error message for empty response."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "google/gemini-2.5-flash"

    mock_response_data = {
        "id": "test-id",
        "model": "google/gemini-2.5-flash",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",  # Empty content
                },
                "finish_reason": "content_filter",  # Blocked by filter
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 0,
            "total_tokens": 10,
        },
    }

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )

        message = str(exc_info.value)
        assert "Empty response from OpenRouter API" in message
        assert "finish_reason=content_filter" in message


@pytest.mark.asyncio
async def test_rate_limit_detection_variations(client, generation_params):
    """Test various rate limit error message formats."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "test"
    model = "google/gemini-2.5-flash"

    error_messages = [
        "429 Too Many Requests",
        "Rate limit exceeded",
        "Quota exceeded",
    ]

    for error_msg in error_messages:
        with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
            # Simulate exception with rate limit message
            mock_post.side_effect = Exception(error_msg)

            with pytest.raises(RateLimitError):
                await client.generate_content(
                    api_key=api_key,
                    prompt=prompt,
                    model=model,
                    parameters=generation_params,
                    request_id=request_id,
                )


@pytest.mark.asyncio
async def test_timeout_exception_handling(client, generation_params):
    """Test handling of request timeout."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "test"
    model = "google/gemini-2.5-flash"

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        # Simulate timeout
        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        with pytest.raises(Exception, match="Request timeout"):
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )


@pytest.mark.asyncio
async def test_request_error_handling(client, generation_params):
    """Test handling of general request errors."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "test"
    model = "google/gemini-2.5-flash"

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        # Simulate request error
        mock_post.side_effect = httpx.RequestError("Connection refused")

        with pytest.raises(Exception, match="Request error"):
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )


@pytest.mark.asyncio
async def test_backward_compatibility_alias():
    """Test that GeminiAsyncClient is an alias for OpenRouterClient."""
    assert GeminiAsyncClient is OpenRouterClient
