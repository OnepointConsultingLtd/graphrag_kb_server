from graphrag_kb_server.config import jwt_cfg, db_cfg


def test_jwt_config():
    assert jwt_cfg.timedelta_minutes > 0, "No time delta available"
    assert jwt_cfg.admin_jwt is not None


def test_db_config():
    assert db_cfg.postgres_connection_string is not None
    assert db_cfg.postgres_connection_pool_min_size > 0
    assert db_cfg.postgres_connection_pool_max_size > 0
