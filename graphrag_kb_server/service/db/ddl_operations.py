from graphrag_kb_server.service.db.connection_pool import execute_query, fetch_one


async def create_schema(schema_name: str):
    await execute_query(f"""CREATE SCHEMA IF NOT EXISTS {schema_name};""")


async def drop_schema(schema_name: str):
    await execute_query(f"""DROP SCHEMA IF EXISTS {schema_name} CASCADE;""")
    # Function-level import to avoid a module import cycle.
    from graphrag_kb_server.service.db.common_operations import (
        invalidate_project_id_cache,
    )

    invalidate_project_id_cache(schema_name)


async def schema_exists(schema_name: str) -> bool:
    row = await fetch_one(
        "SELECT 1 FROM information_schema.schemata WHERE schema_name = $1",
        schema_name,
    )
    return row is not None
