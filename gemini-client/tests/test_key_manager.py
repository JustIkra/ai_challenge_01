"""Tests for KeyManager."""
import asyncio
import time

import pytest

from src.client.key_manager import KeyManager, KeyState


@pytest.mark.asyncio
async def test_key_manager_initialization():
    """Test KeyManager initialization."""
    keys = ["key1", "key2", "key3"]
    manager = KeyManager(api_keys=keys, max_per_minute=10, cooldown_seconds=60)

    assert len(manager.keys) == 3
    assert manager.max_per_minute == 10
    assert manager.cooldown_seconds == 60
    assert manager.current_index == 0


@pytest.mark.asyncio
async def test_key_manager_empty_keys():
    """Test KeyManager raises error with empty keys."""
    with pytest.raises(ValueError, match="At least one API key must be provided"):
        KeyManager(api_keys=[], max_per_minute=10, cooldown_seconds=60)


@pytest.mark.asyncio
async def test_get_available_key_round_robin():
    """Test round-robin key rotation."""
    keys = ["key1", "key2", "key3"]
    manager = KeyManager(api_keys=keys, max_per_minute=10, cooldown_seconds=60)

    # Get keys in round-robin order
    key1 = await manager.get_available_key()
    key2 = await manager.get_available_key()
    key3 = await manager.get_available_key()
    key4 = await manager.get_available_key()

    assert key1 == "key1"
    assert key2 == "key2"
    assert key3 == "key3"
    assert key4 == "key1"  # Back to first key


@pytest.mark.asyncio
async def test_get_available_key_usage_limit():
    """Test that keys become unavailable after usage limit."""
    keys = ["key1"]
    manager = KeyManager(api_keys=keys, max_per_minute=2, cooldown_seconds=60)

    # Use key twice (at limit)
    key1 = await manager.get_available_key()
    key2 = await manager.get_available_key()

    assert key1 == "key1"
    assert key2 == "key1"

    # Third request should return None
    key3 = await manager.get_available_key()
    assert key3 is None


@pytest.mark.asyncio
async def test_key_state_reset():
    """Test that key usage resets after 1 minute."""
    keys = ["key1"]
    manager = KeyManager(api_keys=keys, max_per_minute=2, cooldown_seconds=60)

    # Use key to limit
    await manager.get_available_key()
    await manager.get_available_key()

    # Verify key is unavailable
    key = await manager.get_available_key()
    assert key is None

    # Manually set last_reset to simulate time passage
    manager.keys[0].last_reset = time.time() - 61  # 61 seconds ago

    # Key should be available again
    key = await manager.get_available_key()
    assert key == "key1"
    assert manager.keys[0].usage_count == 1  # Reset and incremented


@pytest.mark.asyncio
async def test_mark_rate_limited():
    """Test marking a key as rate limited."""
    keys = ["key1", "key2"]
    manager = KeyManager(api_keys=keys, max_per_minute=10, cooldown_seconds=5)

    # Mark key1 as rate limited
    await manager.mark_rate_limited("key1")

    # key1 should be unavailable
    key = await manager.get_available_key()
    assert key == "key2"  # Skips key1, returns key2

    # key2 should be next
    key = await manager.get_available_key()
    assert key == "key2"


@pytest.mark.asyncio
async def test_rate_limit_cooldown():
    """Test that rate-limited key becomes available after cooldown."""
    keys = ["key1"]
    manager = KeyManager(api_keys=keys, max_per_minute=10, cooldown_seconds=1)

    # Mark as rate limited
    await manager.mark_rate_limited("key1")

    # Should be unavailable
    key = await manager.get_available_key()
    assert key is None

    # Wait for cooldown
    await asyncio.sleep(1.1)

    # Should be available again
    key = await manager.get_available_key()
    assert key == "key1"


@pytest.mark.asyncio
async def test_get_stats():
    """Test getting key statistics."""
    keys = ["key1", "key2"]
    manager = KeyManager(api_keys=keys, max_per_minute=10, cooldown_seconds=60)

    # Use some keys
    await manager.get_available_key()
    await manager.get_available_key()
    await manager.mark_rate_limited("key1")

    # Get stats
    stats = await manager.get_stats()

    assert stats["total_keys"] == 2
    assert stats["available_keys"] == 1  # key2 is available
    assert len(stats["keys"]) == 2

    # Check key1 stats
    key1_stats = stats["keys"][0]
    assert key1_stats["usage_count"] == 1
    assert key1_stats["total_requests"] == 1
    assert key1_stats["rate_limit_count"] == 1
    assert not key1_stats["is_available"]

    # Check key2 stats
    key2_stats = stats["keys"][1]
    assert key2_stats["usage_count"] == 1
    assert key2_stats["total_requests"] == 1
    assert key2_stats["rate_limit_count"] == 0
    assert key2_stats["is_available"]


@pytest.mark.asyncio
async def test_key_state_is_available():
    """Test KeyState is_available method."""
    key_state = KeyState(key="test_key")
    current_time = time.time()

    # Should be available initially
    assert key_state.is_available(max_per_minute=10, current_time=current_time)

    # Should be unavailable when usage exceeds limit
    key_state.usage_count = 10
    assert not key_state.is_available(max_per_minute=10, current_time=current_time)

    # Should be unavailable when in cooldown
    key_state.usage_count = 0
    key_state.cooldown_until = current_time + 60
    assert not key_state.is_available(max_per_minute=10, current_time=current_time)

    # Should be available after cooldown expires
    key_state.cooldown_until = current_time - 1
    assert key_state.is_available(max_per_minute=10, current_time=current_time)


@pytest.mark.asyncio
async def test_concurrent_key_access():
    """Test that concurrent access to keys is thread-safe."""
    keys = ["key1", "key2", "key3"]
    manager = KeyManager(api_keys=keys, max_per_minute=100, cooldown_seconds=60)

    # Simulate concurrent access
    async def get_key():
        return await manager.get_available_key()

    results = await asyncio.gather(*[get_key() for _ in range(30)])

    # All requests should get a key
    assert all(key is not None for key in results)

    # Keys should be distributed evenly (10 of each)
    assert results.count("key1") == 10
    assert results.count("key2") == 10
    assert results.count("key3") == 10
