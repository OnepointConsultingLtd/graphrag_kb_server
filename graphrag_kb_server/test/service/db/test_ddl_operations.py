import pytest





_TEST_SCHEMA = "test_schema"


async def _create_check_destroy():
    from graphrag_kb_server.service.db.connection_pool import create_connection_pool
    from graphrag_kb_server.service.db.ddl_operations import (
        create_schema,
        drop_schema,
        schema_exists,
    )
    await create_connection_pool()
    await create_schema(_TEST_SCHEMA)
    assert (
        await schema_exists(_TEST_SCHEMA) is True
    ), f"Schema {_TEST_SCHEMA} does not exist"
    await drop_schema(_TEST_SCHEMA)


@pytest.mark.asyncio
async def test_schema_exists():
    await _create_check_destroy()
