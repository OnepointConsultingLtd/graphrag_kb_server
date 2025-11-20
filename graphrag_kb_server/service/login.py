from graphrag_kb_server.model.admin import AdminUser
from graphrag_kb_server.service.db.db_persistence_admin_user import select_admin_user
from graphrag_kb_server.service.validations import check_password


async def admin_login(username: str, email: str, password: str) -> AdminUser | None:
    admin_user = await select_admin_user(email)
    if admin_user is None:
        return None
    if admin_user.name == username and check_password(
        password, admin_user.password_hash
    ):
        return admin_user
    else:
        return None
