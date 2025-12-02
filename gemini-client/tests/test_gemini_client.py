"""Tests for GeminiAsyncClient."""
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from src.client.gemini import GeminiAsyncClient
from src.schemas.request import GenerationParameters
from src.schemas.response import TokenUsage
from src.utils.retry import RateLimitError


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
    """Fixture for GeminiAsyncClient."""
    return GeminiAsyncClient(proxy_url=None)


@pytest.fixture
def client_with_proxy():
    """Fixture for GeminiAsyncClient with proxy."""
    return GeminiAsyncClient(proxy_url="http://localhost:8080")


@pytest.mark.asyncio
async def test_client_initialization(client):
    """Test client initialization without proxy."""
    assert client.proxy_url is None


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
    model = "gemini-pro"

    # Mock Gemini API response
    mock_response = Mock()
    mock_response.text = "Python is a high-level programming language..."

    # Mock usage metadata
    mock_usage = Mock()
    mock_usage.prompt_token_count = 10
    mock_usage.candidates_token_count = 150
    mock_usage.total_token_count = 160
    mock_response.usage_metadata = mock_usage

    with patch("src.client.gemini.genai.Client") as mock_client_class:
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Setup mock generate_content method
        mock_client.models.generate_content.return_value = mock_response

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
        mock_client.models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_generate_content_rate_limit(client, generation_params):
    """Test rate limit error handling."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "gemini-pro"

    with patch("src.client.gemini.genai.Client") as mock_client_class:
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Simulate 429 error
        mock_client.models.generate_content.side_effect = Exception(
            "429 Rate limit exceeded"
        )

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
async def test_generate_content_api_error(client, generation_params):
    """Test general API error handling."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "gemini-pro"

    with patch("src.client.gemini.genai.Client") as mock_client_class:
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Simulate general API error
        mock_client.models.generate_content.side_effect = Exception("Invalid API key")

        # Should raise the exception
        with pytest.raises(Exception, match="Invalid API key"):
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )


@pytest.mark.asyncio
async def test_generate_content_empty_response(client, generation_params):
    """Test handling of empty response."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "gemini-pro"

    # Mock empty response
    mock_response = Mock()
    mock_response.text = None

    with patch("src.client.gemini.genai.Client") as mock_client_class:
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        # Should raise ValueError for empty response
        with pytest.raises(ValueError, match="Empty response from Gemini API"):
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
    model = "gemini-pro"

    # Mock response without usage metadata
    mock_response = Mock()
    mock_response.text = "Python is great!"
    mock_response.usage_metadata = None

    with patch("src.client.gemini.genai.Client") as mock_client_class:
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

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
async def test_client_close(client):
    """Test client cleanup."""
    await client.close()
    # Should complete without errors


@pytest.mark.asyncio
async def test_client_close_with_proxy():
    """Test client cleanup with proxy."""
    import os

    client = GeminiAsyncClient(proxy_url="http://localhost:8080")

    # Proxy should be set
    assert os.environ.get("HTTP_PROXY") == "http://localhost:8080"
    assert os.environ.get("HTTPS_PROXY") == "http://localhost:8080"

    # Close and cleanup
    await client.close()

    # Proxy should be removed
    assert "HTTP_PROXY" not in os.environ
    assert "HTTPS_PROXY" not in os.environ


@pytest.mark.asyncio
async def test_generate_content_uses_proxy_http_options(
    client_with_proxy, generation_params
):
    """Ensure proxy is passed to GenAI client via http options."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about proxies"
    model = "gemini-pro"

    mock_response = Mock()
    mock_response.text = "proxy ok"
    mock_response.usage_metadata = None

    with patch("src.client.gemini.genai.Client") as mock_client_class, patch(
        "src.client.gemini.types.HttpOptions"
    ) as mock_http_options:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        http_options_instance = Mock()
        mock_http_options.return_value = http_options_instance

        await client_with_proxy.generate_content(
            api_key=api_key,
            prompt=prompt,
            model=model,
            parameters=generation_params,
            request_id=request_id,
        )

        mock_http_options.assert_called_once_with(
            client_args={"proxy": client_with_proxy.proxy_url},
            async_client_args={"proxy": client_with_proxy.proxy_url},
        )
        mock_client_class.assert_called_once_with(
            api_key=api_key,
            http_options=http_options_instance,
        )


@pytest.mark.asyncio
async def test_generate_content_location_error_includes_hint(
    client, generation_params
):
    """Surface helpful guidance when API blocks by location."""
    request_id = str(uuid4())
    api_key = "test_api_key"

    with patch("src.client.gemini.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.models.generate_content.side_effect = Exception(
            "400 FAILED_PRECONDITION. {'error': {'code': 400, 'message': 'User "
            "location is not supported for the API use.', 'status': 'FAILED_PRECONDITION'}}"
        )

        with pytest.raises(Exception) as exc_info:
            await client.generate_content(
                api_key=api_key,
                prompt="test",
                model="gemini-pro",
                parameters=generation_params,
                request_id=request_id,
            )

        msg = str(exc_info.value)
        assert "location is not supported" in msg
        assert "Configure HTTP(S)_PROXY" in msg


@pytest.mark.asyncio
async def test_generate_content_empty_response_with_feedback(
    client, generation_params
):
    """Include block reasons when text is missing."""
    request_id = str(uuid4())
    api_key = "test_api_key"
    prompt = "Tell me about Python"
    model = "gemini-pro"

    mock_response = Mock()
    mock_response.text = None

    prompt_feedback = Mock()
    prompt_feedback.block_reason = "SAFETY"
    prompt_feedback.safety_ratings = []
    mock_response.prompt_feedback = prompt_feedback

    candidate = Mock()
    candidate.finish_reason = "SAFETY"
    candidate.safety_ratings = []
    mock_response.candidates = [candidate]

    with patch("src.client.gemini.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            await client.generate_content(
                api_key=api_key,
                prompt=prompt,
                model=model,
                parameters=generation_params,
                request_id=request_id,
            )

        message = str(exc_info.value)
        assert "Empty response from Gemini API" in message
        assert "block_reason=SAFETY" in message
        assert "finish_reason=SAFETY" in message


@pytest.mark.asyncio
async def test_rate_limit_detection_variations(client, generation_params):
    """Test various rate limit error message formats."""
    request_id = str(uuid4())
    api_key = "test_api_key"

    error_messages = [
        "429 Too Many Requests",
        "Rate limit exceeded",
        "Quota exceeded",
        "RATE_LIMIT_EXCEEDED",
    ]

    for error_msg in error_messages:
        with patch("src.client.gemini.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.models.generate_content.side_effect = Exception(error_msg)

            with pytest.raises(RateLimitError):
                await client.generate_content(
                    api_key=api_key,
                    prompt="test",
                    model="gemini-pro",
                    parameters=generation_params,
                    request_id=request_id,
                )
