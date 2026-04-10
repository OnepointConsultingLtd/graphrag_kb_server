"""
Reset the asyncpg connection pool before every async test.

Each pytest-asyncio test runs in its own event loop. The connection pool in
connection_pool.py is a module-level global, so without this fixture it would
be reused across tests even after its original event loop has been closed —
causing "Event loop is closed" errors on every test after the first one.

We use a synchronous autouse fixture so it works regardless of asyncio_mode.
The reset is done *before* the test (not after) so the current test's event
loop is already active when the new pool is created.
"""

import pytest


@pytest.fixture(autouse=True)
def reset_connection_pool():
    """Null out the global pool before each test so a fresh one is created."""
    import graphrag_kb_server.service.db.connection_pool as _pool_module

    _pool_module._connection_pool = None
    yield
    _pool_module._connection_pool = None
