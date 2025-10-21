import pytest

from graphrag_kb_server.service.db.connection_pool import (
    create_connection_pool,
    create_connection_pool,
)


@pytest.mark.asyncio
async def test_create_connection_pool():
    """Test that connection pool can be created and has valid configuration."""
    connection_pool = await create_connection_pool()
    assert connection_pool is not None
    assert connection_pool.get_max_size() > 0
    assert connection_pool.get_min_size() > 0


@pytest.mark.asyncio
async def test_connection_pool_singleton():
    """Test that multiple calls return the same pool instance."""
    pool1 = await create_connection_pool()
    pool2 = await create_connection_pool()
    assert pool1 is pool2
