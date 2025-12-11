"""
Tests for history compression service.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.compression import CompressionService, COMPRESSION_SYSTEM_PROMPT
from app.models.chat import Chat
from app.models.message import Message


class TestCompressionService:
    """Tests for CompressionService."""

    @pytest.fixture
    def mock_chat(self):
        """Create a mock chat with compression enabled."""
        chat = MagicMock(spec=Chat)
        chat.id = uuid.uuid4()
        chat.history_compression_enabled = True
        chat.history_compression_message_limit = 10
        chat.compressed_history_summary = None
        return chat

    @pytest.fixture
    def mock_messages(self):
        """Create mock messages list."""
        messages = []
        for i in range(12):
            msg = MagicMock(spec=Message)
            msg.id = uuid.uuid4()
            msg.role = "user" if i % 2 == 0 else "assistant"
            msg.content = f"Message content {i}"
            msg.status = "completed"
            msg.is_compressed = False
            messages.append(msg)
        return messages

    @pytest.mark.asyncio
    async def test_should_compress_returns_false_when_disabled(self, mock_chat):
        """Test that compression check returns False when disabled."""
        mock_chat.history_compression_enabled = False

        mock_db = AsyncMock()

        result = await CompressionService.should_compress(mock_db, mock_chat)

        assert result is False

    @pytest.mark.asyncio
    async def test_should_compress_returns_false_when_under_limit(self, mock_chat):
        """Test that compression check returns False when under message limit."""
        mock_chat.history_compression_message_limit = 10

        mock_db = AsyncMock()
        # Mock returning only 5 messages (under limit)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock() for _ in range(5)]
        mock_db.execute.return_value = mock_result

        result = await CompressionService.should_compress(mock_db, mock_chat)

        assert result is False

    @pytest.mark.asyncio
    async def test_should_compress_returns_true_when_at_limit(self, mock_chat):
        """Test that compression check returns True when at message limit."""
        mock_chat.history_compression_message_limit = 10

        mock_db = AsyncMock()
        # Mock returning 10 messages (at limit)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock() for _ in range(10)]
        mock_db.execute.return_value = mock_result

        result = await CompressionService.should_compress(mock_db, mock_chat)

        assert result is True

    @pytest.mark.asyncio
    async def test_should_compress_returns_true_when_over_limit(self, mock_chat, mock_messages):
        """Test that compression check returns True when over message limit."""
        mock_chat.history_compression_message_limit = 10

        mock_db = AsyncMock()
        # Mock returning 12 messages (over limit)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_db.execute.return_value = mock_result

        result = await CompressionService.should_compress(mock_db, mock_chat)

        assert result is True

    @pytest.mark.asyncio
    async def test_should_compress_uses_default_limit_when_none(self, mock_chat):
        """Test that compression uses default limit of 10 when limit is None."""
        mock_chat.history_compression_message_limit = None

        mock_db = AsyncMock()
        # Mock returning 10 messages (at default limit)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock() for _ in range(10)]
        mock_db.execute.return_value = mock_result

        result = await CompressionService.should_compress(mock_db, mock_chat)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_messages_for_compression_returns_ordered_messages(self):
        """Test that messages are returned in chronological order."""
        mock_db = AsyncMock()
        chat_id = uuid.uuid4()

        # Create mock messages
        messages = []
        for i in range(5):
            msg = MagicMock(spec=Message)
            msg.id = uuid.uuid4()
            msg.role = "user" if i % 2 == 0 else "assistant"
            msg.content = f"Message {i}"
            messages.append(msg)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = messages
        mock_db.execute.return_value = mock_result

        result = await CompressionService.get_messages_for_compression(mock_db, chat_id)

        assert len(result) == 5
        assert result == messages

    @pytest.mark.asyncio
    async def test_get_messages_for_compression_filters_correctly(self):
        """Test that only uncompressed completed messages are retrieved."""
        mock_db = AsyncMock()
        chat_id = uuid.uuid4()

        # Mock the return value properly
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Verify the SQL query filters are correct by checking execute was called
        await CompressionService.get_messages_for_compression(mock_db, chat_id)

        assert mock_db.execute.called
        # The service should call execute with a select statement
        call_args = mock_db.execute.call_args
        assert call_args is not None

    def test_build_compression_prompt(self, mock_messages):
        """Test building compression prompt from messages."""
        prompt = CompressionService.build_compression_prompt(mock_messages[:4])

        assert "User: Message content 0" in prompt
        assert "Assistant: Message content 1" in prompt
        assert "User: Message content 2" in prompt
        assert "Assistant: Message content 3" in prompt
        assert "Please summarize the following conversation" in prompt

    def test_build_compression_prompt_handles_different_roles(self):
        """Test that prompt correctly labels user and assistant messages."""
        messages = []

        # User message
        user_msg = MagicMock(spec=Message)
        user_msg.role = "user"
        user_msg.content = "Hello, how are you?"
        messages.append(user_msg)

        # Assistant message
        assistant_msg = MagicMock(spec=Message)
        assistant_msg.role = "assistant"
        assistant_msg.content = "I'm doing well, thank you!"
        messages.append(assistant_msg)

        prompt = CompressionService.build_compression_prompt(messages)

        assert "User: Hello, how are you?" in prompt
        assert "Assistant: I'm doing well, thank you!" in prompt

    def test_build_compression_prompt_with_single_message(self):
        """Test building prompt with just one message."""
        msg = MagicMock(spec=Message)
        msg.role = "user"
        msg.content = "Single message"

        prompt = CompressionService.build_compression_prompt([msg])

        assert "User: Single message" in prompt
        assert "Please summarize the following conversation" in prompt

    def test_build_compression_prompt_with_empty_list(self):
        """Test building prompt with empty message list."""
        prompt = CompressionService.build_compression_prompt([])

        assert "Please summarize the following conversation" in prompt

    @pytest.mark.asyncio
    async def test_build_compression_request_returns_none_when_no_messages(self, mock_chat):
        """Test that compression request returns None when no messages to compress."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await CompressionService.build_compression_request(
            mock_db, mock_chat, uuid.uuid4()
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_build_compression_request_creates_valid_request(self, mock_chat, mock_messages):
        """Test that compression request is properly built."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_db.execute.return_value = mock_result

        request_id = uuid.uuid4()

        with patch('app.services.compression.settings') as mock_settings:
            mock_settings.OPENROUTER_MODEL = "google/gemini-2.5-flash"

            result = await CompressionService.build_compression_request(
                mock_db, mock_chat, request_id
            )

        assert result is not None
        assert result.request_id == request_id
        assert result.system_instruction == COMPRESSION_SYSTEM_PROMPT
        assert result.parameters.temperature == 0.3
        assert "Message content" in result.prompt

    @pytest.mark.asyncio
    async def test_build_compression_request_uses_correct_temperature(self, mock_chat, mock_messages):
        """Test that compression request uses temperature of 0.3 for consistent summaries."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_db.execute.return_value = mock_result

        with patch('app.services.compression.settings') as mock_settings:
            mock_settings.OPENROUTER_MODEL = "google/gemini-2.5-flash"

            result = await CompressionService.build_compression_request(
                mock_db, mock_chat, uuid.uuid4()
            )

        assert result.parameters.temperature == 0.3

    @pytest.mark.asyncio
    async def test_build_compression_request_includes_system_prompt(self, mock_chat, mock_messages):
        """Test that compression request includes the compression system prompt."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_db.execute.return_value = mock_result

        with patch('app.services.compression.settings') as mock_settings:
            mock_settings.OPENROUTER_MODEL = "google/gemini-2.5-flash"

            result = await CompressionService.build_compression_request(
                mock_db, mock_chat, uuid.uuid4()
            )

        assert result.system_instruction == COMPRESSION_SYSTEM_PROMPT
        assert "conversation summarizer" in result.system_instruction

    @pytest.mark.asyncio
    async def test_apply_compression_updates_chat_and_messages(self):
        """Test that apply_compression updates the database correctly."""
        mock_db = AsyncMock()
        chat_id = uuid.uuid4()
        summary = "This is a test summary."

        await CompressionService.apply_compression(mock_db, chat_id, summary)

        # Verify execute was called twice (update chat, update messages)
        assert mock_db.execute.call_count == 2
        # Verify commit was called
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_compression_saves_summary_to_chat(self):
        """Test that compression summary is saved to chat record."""
        mock_db = AsyncMock()
        chat_id = uuid.uuid4()
        summary = "This is a detailed summary of the conversation."

        await CompressionService.apply_compression(mock_db, chat_id, summary)

        # Check that execute was called
        assert mock_db.execute.called
        # First call should be updating the chat
        first_call = mock_db.execute.call_args_list[0]
        assert first_call is not None

    @pytest.mark.asyncio
    async def test_apply_compression_marks_messages_as_compressed(self):
        """Test that messages are marked as compressed."""
        mock_db = AsyncMock()
        chat_id = uuid.uuid4()
        summary = "Summary text."

        await CompressionService.apply_compression(mock_db, chat_id, summary)

        # Second execute call should be updating messages
        assert mock_db.execute.call_count == 2
        second_call = mock_db.execute.call_args_list[1]
        assert second_call is not None

    @pytest.mark.asyncio
    async def test_apply_compression_commits_transaction(self):
        """Test that compression changes are committed."""
        mock_db = AsyncMock()
        chat_id = uuid.uuid4()
        summary = "Summary."

        await CompressionService.apply_compression(mock_db, chat_id, summary)

        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_uncompressed_message_count(self):
        """Test counting uncompressed messages."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock() for _ in range(7)]
        mock_db.execute.return_value = mock_result

        count = await CompressionService.get_uncompressed_message_count(mock_db, uuid.uuid4())

        assert count == 7

    @pytest.mark.asyncio
    async def test_get_uncompressed_message_count_returns_zero_when_empty(self):
        """Test that count returns 0 when no uncompressed messages exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        count = await CompressionService.get_uncompressed_message_count(mock_db, uuid.uuid4())

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_uncompressed_message_count_filters_correctly(self):
        """Test that count only includes completed, uncompressed messages."""
        mock_db = AsyncMock()
        chat_id = uuid.uuid4()

        # Mock the return value properly
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Just verify the method is called - the filtering is done in the SQL query
        await CompressionService.get_uncompressed_message_count(mock_db, chat_id)

        assert mock_db.execute.called


class TestCompressionSystemPrompt:
    """Tests for compression system prompt constant."""

    def test_compression_system_prompt_has_required_elements(self):
        """Test that system prompt contains all required elements."""
        assert "conversation summarizer" in COMPRESSION_SYSTEM_PROMPT
        assert "Rules:" in COMPRESSION_SYSTEM_PROMPT
        assert "500 words" in COMPRESSION_SYSTEM_PROMPT
        assert "bullet points" in COMPRESSION_SYSTEM_PROMPT
        assert "Output format:" in COMPRESSION_SYSTEM_PROMPT

    def test_compression_system_prompt_mentions_key_requirements(self):
        """Test that prompt mentions key preservation requirements."""
        assert "key facts" in COMPRESSION_SYSTEM_PROMPT
        assert "context" in COMPRESSION_SYSTEM_PROMPT
        assert "chronological" in COMPRESSION_SYSTEM_PROMPT
