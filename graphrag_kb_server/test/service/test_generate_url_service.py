import datetime

from graphrag_kb_server.config import cfg
from graphrag_kb_server.model.snippet import WidgetType, Project, Platform, SearchType


def test_generate_direct_url():
    from graphrag_kb_server.service.generate_url_service import generate_direct_url

    url = generate_direct_url(
        WidgetType.FLOATING_CHAT,
        Project(
            name="test",
            platform=Platform.LIGHTRAG,
            search_type=SearchType.LOCAL,
            additional_prompt_instructions="",
            updated_timestamp=datetime.datetime.now().isoformat(),
        ),
        "test",
        True,
    )
    assert (
        url
        == f"{cfg.server_base_url}/floating-chat?project=test&platform=lightrag&search_type=local&token=test&chat_type=floating-chat&streaming=true"
    )
