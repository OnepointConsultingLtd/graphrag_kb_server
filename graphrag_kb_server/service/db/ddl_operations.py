from graphrag_kb_server.service.db.connection_pool import execute_query


async def create_schema(schema_name: str):
    await execute_query(f"""CREATE SCHEMA IF NOT EXISTS {schema_name};""")


async def drop_schema(schema_name: str):
    await execute_query(f"""DROP SCHEMA IF EXISTS {schema_name};""")


async def schema_exists(schema_name: str) -> bool:
    result = await execute_query(
        f"""
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name = '{schema_name}'
"""
    )
    return len(result) > 0
