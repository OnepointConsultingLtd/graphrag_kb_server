from pathlib import Path
import jinja2

from graphrag_kb_server.model.snippet import Snippet
from graphrag_kb_server.config import cfg


def generate_snippet(snippet: Snippet) -> str:
    path = Path(__file__).parent.parent.parent / "templates"
    template_loader = jinja2.FileSystemLoader(searchpath=path.resolve())
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("snippet.html")
    return template.render(snippet=snippet.model_dump())


def _build_http_path(ending: str, assets_path: Path) -> str:
    return f"{cfg.server_base_url}/{ending.relative_to(assets_path.parent).as_posix()}"


def find_chat_assets() -> tuple[Path, Path]:
    assets_path = Path(__file__).parent.parent.parent / "front_end_chat/dist/assets"
    if not assets_path.exists():
        raise FileNotFoundError(f"Assets path {assets_path} does not exist")
    css_files = list(assets_path.glob("*.css"))
    script_files = list(assets_path.glob("*.js"))
    return assets_path, css_files, script_files


def inject_scripts_path(snippet: Snippet) -> str:
    assets_path, css_files, script_files = find_chat_assets()
    if len(css_files) == 0:
        raise FileNotFoundError(f"No CSS files found in {assets_path}")
    if len(script_files) == 0:
        raise FileNotFoundError(f"No script files found in {assets_path}")
    snippet.css_path = _build_http_path(css_files[0], assets_path)
    snippet.script_path = _build_http_path(script_files[0], assets_path)


if __name__ == "__main__":
    from graphrag_kb_server.test.provider.snippet_provider import create_snippet
    root_element_id, jwt_token, snippet = create_snippet()
    inject_scripts_path(snippet)
    print(snippet.css_path)
    print(snippet.script_path)
    
