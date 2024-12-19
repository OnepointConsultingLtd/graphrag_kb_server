from graphrag_kb_server.config import jwt_cfg

def test_jwt_config():
    assert jwt_cfg.timedelta_minutes > 0, "No time delta available"