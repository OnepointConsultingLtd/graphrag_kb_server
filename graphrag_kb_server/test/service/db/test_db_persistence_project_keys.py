import pytest

from graphrag_kb_server.model.project import FullProject
from graphrag_kb_server.model.project_setting import ProjectSetting
from graphrag_kb_server.service.crypto.secret_cipher import (
    ENCRYPTION_KEY_ENV_VARIABLE,
    generate_encryption_key,
)
from graphrag_kb_server.test.service.db.common_test_support import (
    create_test_project_wrapper,
)


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv(ENCRYPTION_KEY_ENV_VARIABLE, generate_encryption_key())


@pytest.mark.asyncio
async def test_upsert_and_find_round_trip():
    from graphrag_kb_server.service.db.db_persistence_project_keys import (
        create_project_keys_table,
        drop_project_keys_table,
        find_project_keys,
        upsert_project_keys,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        try:
            await create_project_keys_table(schema_name)
            await upsert_project_keys(
                schema_name,
                project_id,
                {
                    ProjectSetting.OPENAI_API_KEY: "sk-plain",
                    ProjectSetting.LIGHTRAG_MODEL: "gpt-4o",
                },
            )
            found = await find_project_keys(schema_name, project_id)
            assert found == {
                ProjectSetting.OPENAI_API_KEY: "sk-plain",
                ProjectSetting.LIGHTRAG_MODEL: "gpt-4o",
            }
        finally:
            await drop_project_keys_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_secrets_are_encrypted_in_column_and_models_are_plaintext():
    from graphrag_kb_server.service.db.connection_pool import fetch_one
    from graphrag_kb_server.service.db.db_persistence_project_keys import (
        TB_PROJECT_KEYS,
        create_project_keys_table,
        drop_project_keys_table,
        upsert_project_keys,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        try:
            await create_project_keys_table(schema_name)
            await upsert_project_keys(
                schema_name,
                project_id,
                {
                    ProjectSetting.GEMINI_API_KEY: "gemini-plain",
                    ProjectSetting.CAG_MODEL: "gemini-flash",
                },
            )
            row = await fetch_one(
                f"SELECT GEMINI_API_KEY, CAG_MODEL FROM {schema_name}.{TB_PROJECT_KEYS} WHERE PROJECT_ID = $1",
                project_id,
            )
            assert "gemini-plain" not in row["gemini_api_key"]
            assert row["cag_model"] == "gemini-flash"
        finally:
            await drop_project_keys_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_upsert_updates_only_given_settings_and_none_resets():
    from graphrag_kb_server.service.db.db_persistence_project_keys import (
        create_project_keys_table,
        drop_project_keys_table,
        find_project_keys,
        upsert_project_keys,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        try:
            await create_project_keys_table(schema_name)
            await upsert_project_keys(
                schema_name,
                project_id,
                {
                    ProjectSetting.CAG_MODEL: "model-a",
                    ProjectSetting.AUDIO_MODEL: "audio-a",
                },
            )
            await upsert_project_keys(
                schema_name,
                project_id,
                {ProjectSetting.CAG_MODEL: "model-b", ProjectSetting.AUDIO_MODEL: None},
            )
            assert await find_project_keys(schema_name, project_id) == {
                ProjectSetting.CAG_MODEL: "model-b"
            }
        finally:
            await drop_project_keys_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_find_returns_empty_without_row_and_after_delete():
    from graphrag_kb_server.service.db.db_persistence_project_keys import (
        create_project_keys_table,
        delete_project_keys,
        drop_project_keys_table,
        find_project_keys,
        upsert_project_keys,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        try:
            await create_project_keys_table(schema_name)
            assert await find_project_keys(schema_name, project_id) == {}
            await upsert_project_keys(
                schema_name, project_id, {ProjectSetting.CAG_MODEL: "m"}
            )
            await delete_project_keys(schema_name, project_id)
            assert await find_project_keys(schema_name, project_id) == {}
        finally:
            await drop_project_keys_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_keys_deleted_when_project_is_removed():
    from graphrag_kb_server.service.db.db_persistence_project import delete_project
    from graphrag_kb_server.service.db.db_persistence_project_keys import (
        create_project_keys_table,
        drop_project_keys_table,
        find_project_keys,
        upsert_project_keys,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        try:
            await create_project_keys_table(schema_name)
            await upsert_project_keys(
                schema_name, project_id, {ProjectSetting.CAG_MODEL: "m"}
            )
            await delete_project(full_project)
            assert await find_project_keys(schema_name, project_id) == {}
        finally:
            await drop_project_keys_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_togetherai_key_is_encrypted_and_round_trips():
    from graphrag_kb_server.service.db.connection_pool import fetch_one
    from graphrag_kb_server.service.db.db_persistence_project_keys import (
        TB_PROJECT_KEYS,
        create_project_keys_table,
        drop_project_keys_table,
        find_project_keys,
        upsert_project_keys,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        try:
            await create_project_keys_table(schema_name)
            await upsert_project_keys(
                schema_name, project_id, {ProjectSetting.TOGETHERAI_API_KEY: "tg-plain"}
            )
            row = await fetch_one(
                f"SELECT TOGETHERAI_API_KEY FROM {schema_name}.{TB_PROJECT_KEYS} WHERE PROJECT_ID = $1",
                project_id,
            )
            assert "tg-plain" not in row["togetherai_api_key"]
            assert await find_project_keys(schema_name, project_id) == {
                ProjectSetting.TOGETHERAI_API_KEY: "tg-plain"
            }
        finally:
            await drop_project_keys_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_create_adds_missing_columns_to_table_from_older_version():
    """A table created before TOGETHERAI_API_KEY existed gets the column, keeping its data."""
    from graphrag_kb_server.service.db.connection_pool import (
        execute_query,
        fetch_all,
    )
    from graphrag_kb_server.service.db.db_persistence_project_keys import (
        TB_PROJECT_KEYS,
        create_project_keys_table,
        drop_project_keys_table,
        find_project_keys,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        try:
            await drop_project_keys_table(schema_name)
            # The table layout of the first version: without TOGETHERAI_API_KEY.
            await execute_query(
                f"""
CREATE TABLE {schema_name}.{TB_PROJECT_KEYS} (
    ID SERIAL NOT NULL,
    PROJECT_ID INTEGER NOT NULL,
    CAG_MODEL TEXT,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    UNIQUE (PROJECT_ID),
    FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID) ON DELETE CASCADE
);
"""
            )
            await execute_query(
                f"INSERT INTO {schema_name}.{TB_PROJECT_KEYS} (PROJECT_ID, CAG_MODEL) VALUES ($1, 'old-model')",
                project_id,
            )

            await create_project_keys_table(schema_name)
            await create_project_keys_table(schema_name)  # idempotent

            columns = await fetch_all(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = $1 AND table_name = $2",
                schema_name.lower(),
                TB_PROJECT_KEYS.lower(),
            )
            column_names = {row["column_name"] for row in columns}
            assert {setting.value.lower() for setting in ProjectSetting} <= column_names
            assert await find_project_keys(schema_name, project_id) == {
                ProjectSetting.CAG_MODEL: "old-model"
            }
        finally:
            await drop_project_keys_table(schema_name)

    await create_test_project_wrapper(test_function)
