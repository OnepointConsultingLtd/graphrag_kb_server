from graphrag_kb_server.model.snippet import (
    Snippet,
    WidgetType,
    Project,
    SearchType,
    Platform,
)


def create_snippet() -> tuple[str, str, Snippet]:
    root_element_id = "root_element"
    jwt_token = "jwt"
    return (
        root_element_id,
        jwt_token,
        Snippet(
            widget_type=WidgetType.FLOATING_CHAT,
            root_element_id=root_element_id,
            jwt=jwt_token,
            base_server="http://localhost:9999",
            project=Project(
                name="project",
                updated_timestamp="2025-06-16T15:17:33.945Z",
                input_files=[],
                search_type=SearchType.LOCAL,
                platform=Platform.LIGHTRAG,
                additional_prompt_instructions="You are a helpful assistant.",
            ),
            css_path="/assets/index-BP7tuhB6.css",
            script_path="/assets/index-DwkZlIms.js",
        ),
    )
