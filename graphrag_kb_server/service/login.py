from graphrag_kb_server.service.db.db_persistence_admin_user import select_admin_user
from graphrag_kb_server.service.validations import check_password


async def admin_login(username: str, email: str, password: str) -> bool:
    admin_user = await select_admin_user(email)
    if admin_user is None:
        return False
    return admin_user.name == username and check_password(password, admin_user.password_hash)