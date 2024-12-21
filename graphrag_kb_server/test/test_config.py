from graphrag_kb_server.config import jwt_cfg, admin_cfg


def test_jwt_config():
    assert jwt_cfg.timedelta_minutes > 0, "No time delta available"
    assert admin_cfg.administrators is not None
    assert len(admin_cfg.administrators) > 0
    assert jwt_cfg.admin_jwt is not None
