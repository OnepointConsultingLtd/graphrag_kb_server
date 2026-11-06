from graphrag_kb_server.model.project_setting import SECRET_SETTINGS, ProjectSetting
from graphrag_kb_server.service.crypto.secret_cipher import (
    decrypt_secret,
    encrypt_secret,
)
from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    fetch_one,
)

TB_PROJECT_KEYS = "TB_PROJECT_KEYS"

_SETTING_COLUMNS = [setting.value for setting in ProjectSetting]


async def create_project_keys_table(schema_name: str):
    """Create the per-project settings table. A NULL column means 'use the .env value'."""
    setting_columns_ddl = ",\n".join(
        f"    {column} TEXT" for column in _SETTING_COLUMNS
    )
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_PROJECT_KEYS} (
    ID         SERIAL    NOT NULL,
    PROJECT_ID INTEGER   NOT NULL,
{setting_columns_ddl},
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    UNIQUE (PROJECT_ID),
    CONSTRAINT PROJECT_KEYS_PROJECT_ID_FK
        FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID)
        MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )
    await _add_missing_setting_columns(schema_name)


async def _add_missing_setting_columns(schema_name: str):
    """Add the setting columns that are missing from a table created by an older version.

    CREATE TABLE IF NOT EXISTS does not add columns to an existing table, so every setting
    column is added idempotently here. This keeps tenant schemas up to date when a new
    setting is introduced.
    """
    add_columns_ddl = ",\n".join(
        f"    ADD COLUMN IF NOT EXISTS {column} TEXT" for column in _SETTING_COLUMNS
    )
    await execute_query(
        f"""
ALTER TABLE {schema_name}.{TB_PROJECT_KEYS}
{add_columns_ddl};
"""
    )


async def drop_project_keys_table(schema_name: str):
    await execute_query(f"DROP TABLE IF EXISTS {schema_name}.{TB_PROJECT_KEYS};")


def _encode_value(setting: ProjectSetting, value: str | None) -> str | None:
    """Encrypt the value if the setting is a secret; None stays None."""
    if value is None:
        return None
    return encrypt_secret(value) if setting in SECRET_SETTINGS else value


def _decode_value(setting: ProjectSetting, stored_value: str) -> str:
    """Decrypt the stored value if the setting is a secret."""
    return decrypt_secret(stored_value) if setting in SECRET_SETTINGS else stored_value


async def upsert_project_keys(
    schema_name: str, project_id: int, values: dict[ProjectSetting, str | None]
):
    """Insert or update the settings of a project.

    Only the settings present in ``values`` are written; a value of None resets that setting
    to the .env fallback. Secret settings are encrypted before being stored.
    """
    if not values:
        return
    settings = list(values.keys())
    columns = [setting.value for setting in settings]
    encoded_values = [_encode_value(setting, values[setting]) for setting in settings]
    placeholders = ", ".join(f"${index + 2}" for index in range(len(columns)))
    updates = ", ".join(f"{column} = EXCLUDED.{column}" for column in columns)
    await execute_query(
        f"""
INSERT INTO {schema_name}.{TB_PROJECT_KEYS} (PROJECT_ID, {", ".join(columns)})
VALUES ($1, {placeholders})
ON CONFLICT (PROJECT_ID) DO UPDATE SET {updates}, UPDATED_AT = now();
""",
        project_id,
        *encoded_values,
    )


async def find_project_keys(
    schema_name: str, project_id: int
) -> dict[ProjectSetting, str]:
    """Return the non-null settings of a project, with secrets decrypted. Empty if no row."""
    row = await fetch_one(
        f"SELECT {', '.join(_SETTING_COLUMNS)} FROM {schema_name}.{TB_PROJECT_KEYS} WHERE PROJECT_ID = $1;",
        project_id,
    )
    if row is None:
        return {}
    return {
        setting: _decode_value(setting, row[setting.value.lower()])
        for setting in ProjectSetting
        if row[setting.value.lower()] is not None
    }


async def delete_project_keys(schema_name: str, project_id: int):
    """Remove the settings row of a project (the project then falls back to .env)."""
    await execute_query(
        f"DELETE FROM {schema_name}.{TB_PROJECT_KEYS} WHERE PROJECT_ID = $1;",
        project_id,
    )
