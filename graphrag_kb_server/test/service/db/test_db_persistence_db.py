import pytest

from graphrag_kb_server.model.admin import AdminUser
from graphrag_kb_server.service.db.db_persistence_admin_user import create_admin_user_table, delete_admin_user, insert_admin_user, select_admin_user, select_all_admin_users

@pytest.mark.asyncio
async def test_create_drop_admin_user_table():
    await create_admin_user_table()
    admin_user_test = AdminUser(
        name="test_admin_user",
        email="test_admin_user@example.com",
        password_plain="test_password",
    )
    await insert_admin_user(admin_user_test)
    admin_user_data = await select_admin_user(admin_user_test.email)
    assert admin_user_data is not None
    assert admin_user_data.name == admin_user_test.name
    assert admin_user_data.email == admin_user_test.email

    all_admin_users = await select_all_admin_users()
    assert len(all_admin_users) > 1

    delete_result = await delete_admin_user(admin_user_test.email)
    assert delete_result is True
    admin_user_data = await select_admin_user(admin_user_test.email)
    assert admin_user_data is None