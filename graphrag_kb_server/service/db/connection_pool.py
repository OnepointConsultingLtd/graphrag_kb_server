import asyncio
import logging
from typing import Optional, Sequence, Any

import asyncpg

from graphrag_kb_server.config import db_cfg

logger = logging.getLogger(__name__)

# Global pool instance
_connection_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()


async def create_connection_pool() -> asyncpg.Pool:
    """Create or return existing connection pool.

    Returns:
        asyncpg.Pool: The database connection pool

    Raises:
        asyncpg.PostgresError: If connection to database fails
        ValueError: If configuration is invalid
    """
    global _connection_pool

    # Double-checked locking pattern for thread safety
    if _connection_pool is not None:
        return _connection_pool

    async with _pool_lock:
        # Check again after acquiring lock
        if _connection_pool is not None:
            return _connection_pool

        try:
            logger.info("Creating database connection pool...")

            pool = await asyncpg.create_pool(
                dsn=db_cfg.postgres_connection_string,
                min_size=db_cfg.postgres_connection_pool_min_size,
                max_size=db_cfg.postgres_connection_pool_max_size,
                # Optional tuning:
                # command_timeout=10.0,
                # max_inactive_connection_lifetime=300.0,
                # statement_cache_size=1000,
            )

            _connection_pool = pool
            logger.info(
                f"Database connection pool created successfully (min: {pool.get_min_size()}, max: {pool.get_max_size()})"
            )
            return pool

        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise


async def close_connection_pool() -> None:
    """Close the connection pool and cleanup resources."""
    global _connection_pool

    if _connection_pool is not None:
        logger.info("Closing database connection pool...")
        await _connection_pool.close()
        _connection_pool = None
        logger.info("Database connection pool closed")


async def execute_query(sql: str, *args: Sequence[Any]) -> list[dict]:
    await create_connection_pool()
    if _connection_pool is None:
        raise ValueError("Connection pool is not created")
    async with _connection_pool.acquire() as conn:
        return await conn.execute(sql, *args)


async def fetch_all(sql: str, *args: Sequence[Any]) -> list[asyncpg.Record]:
    await create_connection_pool()
    if _connection_pool is None:
        raise ValueError("Connection pool is not created")
    async with _connection_pool.acquire() as conn:
        return await conn.fetch(sql, *args)


async def fetch_one(sql: str, *args: Sequence[Any]) -> Optional[asyncpg.Record]:
    """Fetch a single record from the database.
    
    Returns:
        asyncpg.Record or None: The single record, or None if no records found
    """
    await create_connection_pool()
    if _connection_pool is None:
        raise ValueError("Connection pool is not created")
    async with _connection_pool.acquire() as conn:
        return await conn.fetchrow(sql, *args)


async def execute_query_with_return(sql: str, *args: Sequence[Any]) -> int:
    await create_connection_pool()
    if _connection_pool is None:
        raise ValueError("Connection pool is not created")
    async with _connection_pool.acquire() as conn:
        return int(await conn.fetchval(sql, *args))
