from graphrag_kb_server.config import cfg
from graphrag_kb_server.model.snippet import WidgetType, Project, Platform


def generate_direct_url(chat_type: WidgetType, project: Project, jwt_token: str) -> str:
    path = ""
    match chat_type:
        case WidgetType.FLOATING_CHAT:
            path = "floating-chat"
        case WidgetType.CHAT:
            path = "chat"
    return f"{cfg.server_base_url}/{path}?project={project.name}&platform={project.platform}&search_type={project.search_type}&token={jwt_token}&chat_type={path}"


if __name__ == "__main__":
    from graphrag_kb_server.model.snippet import (
        WidgetType,
        Project,
        Platform,
        SearchType,
    )
    import datetime

    print(
        generate_direct_url(
            WidgetType.FLOATING_CHAT,
            Project(
                name="test",
                platform=Platform.LIGHTRAG,
                search_type=SearchType.LOCAL,
                additional_prompt_instructions="",
                updated_timestamp=datetime.datetime.now().isoformat(),
            ),
            "test",
        )
    )
