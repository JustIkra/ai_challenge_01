# Backend Tests

This directory contains the test suite for the backend application.

## Running Tests

### Run all tests
```bash
cd backend
python3 -m pytest tests/ -v
```

### Run specific test file
```bash
python3 -m pytest tests/test_compression.py -v
```

### Run with coverage
```bash
python3 -m pytest tests/ --cov=app --cov-report=term-missing
```

### Run specific test
```bash
python3 -m pytest tests/test_compression.py::TestCompressionService::test_should_compress_returns_false_when_disabled -v
```

## Test Structure

### conftest.py
Contains shared fixtures and test configuration:
- Environment variable setup for settings
- Mock database session fixtures
- Common test utilities

### test_compression.py
Tests for the history compression service (`app.services.compression.CompressionService`).

**Coverage: 100%**

**Test Classes:**
- `TestCompressionService`: Tests all methods of the CompressionService
- `TestCompressionSystemPrompt`: Tests the compression system prompt constant

**Key Test Areas:**
1. **Compression decision logic** (`should_compress`)
   - Tests when compression is disabled
   - Tests message count thresholds
   - Tests default limit handling

2. **Message retrieval** (`get_messages_for_compression`)
   - Tests proper filtering of messages
   - Tests chronological ordering

3. **Prompt building** (`build_compression_prompt`)
   - Tests prompt formatting
   - Tests role labeling (user/assistant)
   - Tests edge cases (empty, single message)

4. **Request construction** (`build_compression_request`)
   - Tests GeminiRequestMessage creation
   - Tests temperature setting (0.3 for consistency)
   - Tests system instruction inclusion

5. **Compression application** (`apply_compression`)
   - Tests database updates
   - Tests message marking as compressed
   - Tests transaction commits

6. **Message counting** (`get_uncompressed_message_count`)
   - Tests accurate counting
   - Tests proper filtering

## Test Patterns

### Async Tests
All async service methods use `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_something(self):
    result = await CompressionService.some_method(mock_db, ...)
    assert result == expected
```

### Mocking
- Use `AsyncMock` for async database sessions
- Use `MagicMock` for models and regular objects
- Use `@patch` decorator for external dependencies (like settings)

### Fixtures
Fixtures are defined either:
- In `conftest.py` for shared fixtures
- At class level using `@pytest.fixture` for test-specific fixtures

Example:
```python
@pytest.fixture
def mock_chat(self):
    """Create a mock chat with compression enabled."""
    chat = MagicMock(spec=Chat)
    chat.id = uuid.uuid4()
    chat.history_compression_enabled = True
    return chat
```

## Adding New Tests

1. Create a new test file: `test_<module_name>.py`
2. Import necessary dependencies and the module to test
3. Create test classes: `Test<ClassName>`
4. Write test methods: `test_<description>`
5. Use descriptive docstrings for each test
6. Add fixtures in `conftest.py` if they're reusable

## Best Practices

- Each test should test one specific behavior
- Use descriptive test names that explain what is being tested
- Mock external dependencies (database, APIs, etc.)
- Aim for high code coverage (>80%)
- Test both happy paths and edge cases
- Test error conditions and exception handling
