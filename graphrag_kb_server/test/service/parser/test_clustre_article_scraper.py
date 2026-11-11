from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup

from graphrag_kb_server.model.path_link import PathLink
from graphrag_kb_server.service.parser import clustre_article_scraper as scraper
from graphrag_kb_server.service.parser import clustre_scraper_common as common
from graphrag_kb_server.service.parser.clustre_article_scraper import (
    CLUSTRE_ARTICLES_URL,
    WEBSITE_ARTICLES_FOLDER,
    article_file_name,
    article_to_markdown,
    extract_published_date,
    normalize_article_url,
    select_missing_articles,
    sync_clustre_articles,
    write_article_documents,
)
from graphrag_kb_server.service.parser.clustre_scraper_common import (
    extract_article_urls,
    extract_next_page_url,
)

EDGE_COMPUTING_URL = "https://www.clustre.net/edge-computing/"
AUTOMATION_URL = "https://www.clustre.net/intelligent-automation-robots/"

LISTING_HTML = """
<html><body>
<div class="item-grid w2 brGreen hotspot">
<a href=https://www.clustre.net/edge-computing/ ><img src=x.jpg></a>
<div class=archiveTitle><a href=https://www.clustre.net/edge-computing/ >Edge Computing</a></div>
</div>
<div class="item-grid w2 brOrange hotspot">
<a href=https://www.clustre.net/intelligent-automation-robots/ ><img src=y.jpg></a>
</div>
<div class=emm-paginate>
<a href=https://www.clustre.net/category/articles/page/2/ class=emm-next>Next page</a>
</div>
</body></html>
"""

ARTICLE_HTML = """
<html><head>
<title>Edge Computing | Clustre, The Solution Brokers</title>
<meta property="article:published_time" content="2017-06-16T09:30:00+00:00" />
</head><body>
<header><div id=menuMainWrap>Home About Contact</div></header>
<div class=internalTopHeaderBlue><h1>Edge Computing</h1></div>
<div class=container><div id=internalContent>
<p>Edge computing moves processing closer to the data.</p>
<h2>Why it matters</h2>
<ul><li>Lower latency</li><li>Less bandwidth</li></ul>
<h4>Further reading</h4>
<blockquote>The edge is the new cloud.</blockquote>
<p>Contact <a href="https://www.clustre.net/contact/">us</a> today.</p>
<div class=social-sharing><a href="https://facebook.com/share">Share on Facebook</a>
<p>Share on Twitter</p></div>
</div></div>
<div class=footerStyle><p>Copyright Clustre</p></div>
</body></html>
"""

EMPTY_ARTICLE_HTML = """
<html><head><title>Empty | Clustre</title></head><body>
<h1>Empty</h1>
<div id=internalContent><div class=social-sharing><p>Share on Facebook</p></div></div>
</body></html>
"""


def test_listing_markup_is_parsed_by_shared_functions():
    assert extract_article_urls(LISTING_HTML, CLUSTRE_ARTICLES_URL) == [
        EDGE_COMPUTING_URL,
        AUTOMATION_URL,
    ]
    assert (
        extract_next_page_url(LISTING_HTML, CLUSTRE_ARTICLES_URL)
        == "https://www.clustre.net/category/articles/page/2/"
    )


def test_extract_published_date_present():
    soup = BeautifulSoup(ARTICLE_HTML, "html.parser")
    assert extract_published_date(soup) == "2017-06-16"


def test_extract_published_date_absent():
    soup = BeautifulSoup("<html><head></head></html>", "html.parser")
    assert extract_published_date(soup) is None


def test_article_to_markdown():
    assert article_to_markdown(ARTICLE_HTML, EDGE_COMPUTING_URL) == (
        "# Edge Computing\n\n"
        "Source: https://www.clustre.net/edge-computing/\n"
        "Published: 2017-06-16\n\n"
        "Edge computing moves processing closer to the data.\n\n"
        "## Why it matters\n\n"
        "- Lower latency\n"
        "- Less bandwidth\n\n"
        "### Further reading\n\n"
        "> The edge is the new cloud.\n\n"
        "Contact us today.\n"
    )


def test_article_to_markdown_removes_share_block_and_hrefs():
    markdown = article_to_markdown(ARTICLE_HTML, EDGE_COMPUTING_URL)
    assert "Share on" not in markdown
    assert "facebook.com" not in markdown
    assert "https://www.clustre.net/contact/" not in markdown


def test_article_to_markdown_skips_repeated_title():
    html = (
        "<html><body><div id=internalContent>"
        "<h1>Edge Computing</h1><p>Body text</p>"
        "</div></body></html>"
    )
    assert article_to_markdown(html, EDGE_COMPUTING_URL) == (
        "# Edge Computing\n\n"
        "Source: https://www.clustre.net/edge-computing/\n\n"
        "Body text\n"
    )


def test_article_to_markdown_without_body_text():
    assert article_to_markdown(EMPTY_ARTICLE_HTML, EDGE_COMPUTING_URL) is None


def test_article_file_name():
    assert article_file_name(EDGE_COMPUTING_URL) == "edge-computing.md"
    assert article_file_name("https://www.clustre.net/a/b?x=1") == "b.md"
    assert article_file_name("https://www.clustre.net/") == "article.md"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.clustre.net/edge-computing/",
        "http://www.clustre.net/edge-computing/",
        "https://clustre.net/edge-computing",
        "https://WWW.Clustre.net/edge-computing/?utm_source=x#top",
        " https://www.clustre.net/edge-computing/ ",
    ],
)
def test_normalize_article_url(url):
    assert normalize_article_url(url) == "https://clustre.net/edge-computing"


def test_select_missing_articles():
    indexed_urls = {
        normalize_article_url("http://clustre.net/edge-computing"),
        normalize_article_url("https://vimeo.com/676029919"),
    }
    article_urls = [
        EDGE_COMPUTING_URL,
        AUTOMATION_URL,
        "https://www.clustre.net/net-zero/",
    ]
    assert select_missing_articles(article_urls, indexed_urls) == [
        AUTOMATION_URL,
        "https://www.clustre.net/net-zero/",
    ]
    assert select_missing_articles([], indexed_urls) == []


def _mock_http_client(monkeypatch, handler) -> list[str]:
    """Make create_http_client return a client served by handler and record the requested URLs."""
    requested_urls: list[str] = []
    real_client = httpx.AsyncClient

    def recording_handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return handler(request)

    def fake_create_http_client() -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(recording_handler))

    monkeypatch.setattr(scraper, "create_http_client", fake_create_http_client)
    return requested_urls


def _article_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/broken/":
        return httpx.Response(500)
    if request.url.path == "/empty/":
        return httpx.Response(200, text=EMPTY_ARTICLE_HTML)
    return httpx.Response(200, text=ARTICLE_HTML)


@pytest.mark.asyncio
async def test_write_article_documents(monkeypatch, tmp_path):
    messages: list[str] = []

    class RecordingLogger:
        def __getattr__(self, level):
            return messages.append

    monkeypatch.setattr(scraper, "logger", RecordingLogger())
    requested_urls = _mock_http_client(monkeypatch, _article_handler)
    articles_folder = tmp_path / WEBSITE_ARTICLES_FOLDER
    articles_folder.mkdir()
    (articles_folder / "intelligent-automation-robots.md").write_text("stale")
    missing_urls = [
        EDGE_COMPUTING_URL,
        "https://www.clustre.net/broken/",
        AUTOMATION_URL,
        "https://www.clustre.net/empty/",
    ]
    files = await write_article_documents(articles_folder, missing_urls)
    assert files == [
        articles_folder / "edge-computing.md",
        articles_folder / "intelligent-automation-robots.md",
    ]
    assert requested_urls == missing_urls
    rewritten = files[1].read_text(encoding="utf-8")
    assert rewritten.startswith("# Edge Computing\n\nSource: ")
    assert any(m.startswith("[1/4] Wrote article") for m in messages)
    assert any(m.startswith("[2/4] Failed to fetch article") for m in messages)
    assert any(m.startswith("[3/4] Wrote article") for m in messages)
    assert any(m.startswith("[4/4] No text in article") for m in messages)


class SyncFakes:
    """Replaces the database, crawling and indexing calls of sync_clustre_articles."""

    def __init__(self, monkeypatch, project_dir: Path | None, indexed_links: list[str]):
        self.indexed_links = list(indexed_links)
        self.indexed_files: list[Path] = []
        self.written_urls: list[str] = []

        async def fake_create_path_links_table(schema_name: str):
            return None

        async def fake_get_project_id(schema_name, project_name, engine):
            return 7

        async def fake_collect_listing_article_urls():
            return [EDGE_COMPUTING_URL, AUTOMATION_URL]

        async def fake_find_path_links(schema_name: str, project_id: int):
            return [
                PathLink(path=f"doc_{i}.md", link=link, project_id=project_id)
                for i, link in enumerate(self.indexed_links)
            ]

        async def fake_write_article_documents(articles_folder: Path, missing_urls):
            self.written_urls.extend(missing_urls)
            return [articles_folder / article_file_name(url) for url in missing_urls]

        async def fake_index_files_into_project(project_dir: Path, files: list[Path]):
            self.indexed_files.extend(files)
            self.indexed_links.extend(self.written_urls)

        monkeypatch.setattr(scraper, "create_path_links_table", fake_create_path_links_table)
        monkeypatch.setattr(scraper, "get_project_id", fake_get_project_id)
        monkeypatch.setattr(
            scraper, "collect_listing_article_urls", fake_collect_listing_article_urls
        )
        monkeypatch.setattr(scraper, "find_path_links", fake_find_path_links)
        monkeypatch.setattr(scraper, "write_article_documents", fake_write_article_documents)
        monkeypatch.setattr(
            scraper, "index_files_into_project", fake_index_files_into_project
        )
        monkeypatch.setattr(
            scraper,
            "resolve_lightrag_project_dir",
            lambda schema_name, project_name, engine: project_dir,
        )


@pytest.mark.asyncio
async def test_sync_dry_run_indexes_nothing(monkeypatch, tmp_path):
    fakes = SyncFakes(monkeypatch, tmp_path, indexed_links=[])
    await sync_clustre_articles("schema", "project", "lightrag", dry_run=True)
    assert fakes.written_urls == []
    assert fakes.indexed_files == []


@pytest.mark.asyncio
async def test_sync_without_missing_articles_indexes_nothing(monkeypatch, tmp_path):
    fakes = SyncFakes(
        monkeypatch,
        tmp_path,
        indexed_links=["http://clustre.net/edge-computing", AUTOMATION_URL],
    )
    await sync_clustre_articles("schema", "project", "lightrag")
    assert fakes.written_urls == []
    assert fakes.indexed_files == []


@pytest.mark.asyncio
async def test_sync_writes_and_indexes_missing_articles(monkeypatch, tmp_path):
    fakes = SyncFakes(monkeypatch, tmp_path, indexed_links=[EDGE_COMPUTING_URL])
    await sync_clustre_articles("schema", "project", "lightrag")
    assert fakes.written_urls == [AUTOMATION_URL]
    assert fakes.indexed_files == [
        tmp_path / "input" / WEBSITE_ARTICLES_FOLDER / "intelligent-automation-robots.md"
    ]


@pytest.mark.asyncio
async def test_sync_without_indexable_project_writes_nothing(monkeypatch):
    fakes = SyncFakes(monkeypatch, None, indexed_links=[])
    await sync_clustre_articles("schema", "project", "graphrag")
    assert fakes.written_urls == []
    assert fakes.indexed_files == []


def test_article_scraper_uses_shared_noise_selectors():
    assert ".social-sharing" in common.PAGE_NOISE_SELECTORS
