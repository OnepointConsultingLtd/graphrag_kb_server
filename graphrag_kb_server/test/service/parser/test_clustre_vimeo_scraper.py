import httpx
import pytest

from graphrag_kb_server.service.parser import clustre_vimeo_scraper as scraper
from graphrag_kb_server.service.parser.clustre_vimeo_scraper import (
    CLUSTRE_VIDEOS_URL,
    extract_article_urls,
    extract_next_page_url,
    extract_page_text,
    extract_vimeo_links,
    fetch_page_text,
    fetch_transcript,
    fetch_transcript_with_audio_fallback,
    transcript_content,
    transcript_file_name,
    vtt_to_text,
    write_transcripts,
)

VTT = """WEBVTT

1
00:00:01.000 --> 00:00:04.000
<v Simon>Net Zero cannot fly on noble intentions.

2
00:00:04.000 --> 00:00:06.000
Net Zero cannot fly on noble intentions.

3
00:00:06.000 --> 00:00:09.000
Engage everyone, at every level.
"""

CATEGORY_HTML = """
<html><head>
<link rel=next href=https://www.clustre.net/category/videos/page/2/ >
</head><body>
<div id=grid>
<div class="item-grid w2  brGreen hotspot">
<a href=https://www.clustre.net/feb-22-it-edit/ ><img src=x.jpg></a>
<div class=archiveTitle><a href=https://www.clustre.net/feb-22-it-edit/ >Net Zero</a></div>
</div>
<div class="item-grid w2  brOrange hotspot">
<a href=https://www.clustre.net/jan-22-it-full-edit/ ><img src=y.jpg></a>
</div>
</div>
<div class=emm-paginate>
<a href=https://www.clustre.net/category/videos/page/2/ class=emm-page>2</a>
<a href=https://www.clustre.net/category/videos/page/2/ class=emm-next>Next page</a>
</div>
</body></html>
"""

ARTICLE_HTML = """
<div class="su-vimeo su-u-responsive-media-yes"><iframe
width=600 height=660 src="//player.vimeo.com/video/676029919?title=0&amp;byline=0"
frameborder=0 allowfullscreen></iframe></div>
<iframe src="//player.vimeo.com/video/676029919?autoplay=1"></iframe>
<iframe src="https://www.youtube.com/embed/abc"></iframe>
"""


def test_extract_article_urls():
    assert extract_article_urls(CATEGORY_HTML, CLUSTRE_VIDEOS_URL) == [
        "https://www.clustre.net/feb-22-it-edit/",
        "https://www.clustre.net/jan-22-it-full-edit/",
    ]


def test_extract_next_page_url():
    assert (
        extract_next_page_url(CATEGORY_HTML, CLUSTRE_VIDEOS_URL)
        == "https://www.clustre.net/category/videos/page/2/"
    )
    assert extract_next_page_url("<html></html>", CLUSTRE_VIDEOS_URL) is None


def test_extract_vimeo_links():
    assert extract_vimeo_links(ARTICLE_HTML) == ["https://vimeo.com/676029919"]


def test_vtt_to_text():
    assert vtt_to_text(VTT) == (
        "Net Zero cannot fly on noble intentions.\nEngage everyone, at every level."
    )


def test_transcript_file_name_and_content():
    article = "https://www.clustre.net/feb-22-it-edit/"
    assert transcript_file_name(article, "676029919") == "feb-22-it-edit_676029919.txt"
    assert transcript_content(article, "676029919", "Hello") == (
        "Video: https://vimeo.com/676029919\n"
        "Web page: https://www.clustre.net/feb-22-it-edit/\n\nHello\n"
    )


def _vimeo_client(tracks: list[dict]) -> tuple[httpx.AsyncClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "api.vimeo.com":
            return httpx.Response(200, json={"data": tracks})
        return httpx.Response(200, text=VTT)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), requests


@pytest.mark.asyncio
async def test_fetch_transcript_prefers_active_english_track():
    tracks = [
        {"language": "fr", "active": True, "link": "https://captions.test/fr.vtt"},
        {"language": "en", "active": False, "link": "https://captions.test/old.vtt"},
        {"language": "en-GB", "active": True, "link": "https://captions.test/en.vtt"},
    ]
    client, requests = _vimeo_client(tracks)
    async with client:
        transcript = await fetch_transcript(client, "676029919", "token")
    assert transcript is not None and transcript.startswith("Net Zero")
    api_request, track_request = requests
    assert api_request.url.path == "/videos/676029919/texttracks"
    assert api_request.headers["Authorization"] == "bearer token"
    assert str(track_request.url) == "https://captions.test/en.vtt"
    assert "Authorization" not in track_request.headers


@pytest.mark.asyncio
async def test_fetch_transcript_without_tracks():
    client, requests = _vimeo_client([])
    async with client:
        assert await fetch_transcript(client, "676029919", "token") is None
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_audio_fallback_used_when_no_text_tracks(monkeypatch):
    calls: list[tuple[str, str]] = []

    async def fake_transcribe(vimeo_id: str, article_url: str, token: str) -> str:
        calls.append((vimeo_id, article_url))
        return "spoken words"

    monkeypatch.setattr(scraper, "transcribe_vimeo_audio", fake_transcribe)
    client, _ = _vimeo_client([])
    async with client:
        transcript = await fetch_transcript_with_audio_fallback(
            client, "676029919", "https://www.clustre.net/a/", "token"
        )
    assert transcript == "spoken words"
    assert calls == [("676029919", "https://www.clustre.net/a/")]


@pytest.mark.asyncio
async def test_audio_fallback_skipped_when_text_track_exists(monkeypatch):
    async def fail_transcribe(vimeo_id: str, article_url: str, token: str) -> str:
        raise AssertionError("audio fallback must not run")

    monkeypatch.setattr(scraper, "transcribe_vimeo_audio", fail_transcribe)
    tracks = [{"language": "en", "active": True, "link": "https://captions.test/en.vtt"}]
    client, _ = _vimeo_client(tracks)
    async with client:
        transcript = await fetch_transcript_with_audio_fallback(
            client, "676029919", "https://www.clustre.net/a/", "token"
        )
    assert transcript is not None and transcript.startswith("Net Zero")


PAGE_HTML = """
<html><head><title>Why engage everyone | Clustre, The Solution Brokers</title></head>
<body>
<header><div id=menuMainWrap>Home About Contact</div></header>
<nav id=mobileMenu><ul><li>Menu item</li></ul></nav>
<div class=internalTopHeaderBlue><h1>Why engage everyone</h1></div>
<div class=container><div id=internalContent>
<div class=wp-block-spacer></div>
<p class=wp-block-paragraph>Net Zero cannot   fly on <b>noble</b> intentions.</p>
<ul><li><p>Engage everyone</p></li><li>Measure progress</li></ul>
<iframe src="//player.vimeo.com/video/676029919"></iframe>
<form><p>Subscribe to our newsletter</p></form>
</div></div>
<div class=footerStyle><p>Copyright Clustre</p></div>
<div id=inlinePopUp><p>Popup text</p></div>
<div id=cookie-notice><span>We use cookies</span></div>
</body></html>
"""


def test_extract_page_text_keeps_article_text_only():
    assert extract_page_text(PAGE_HTML) == (
        "Why engage everyone\n"
        "Net Zero cannot fly on noble intentions.\n"
        "Engage everyone\n"
        "Measure progress"
    )


def test_extract_page_text_without_content_container_removes_noise():
    html = (
        "<html><head><title>Plain page | Clustre</title></head><body>"
        "<nav>Menu</nav><div><p>Useful paragraph</p></div>"
        "<div class=footerStyle>Footer</div><div id=cookie-notice>Cookies</div>"
        "</body></html>"
    )
    assert extract_page_text(html) == "Plain page\nUseful paragraph"


def test_extract_page_text_uses_plain_text_when_no_blocks():
    html = "<html><body><div id=internalContent>Just <br>text</div></body></html>"
    assert extract_page_text(html) == "Just\ntext"


def test_extract_page_text_of_empty_page():
    assert extract_page_text("<html></html>") == ""


def test_transcript_content_with_page_text_has_separate_sections():
    content = transcript_content(
        "https://www.clustre.net/a/", "1", "Spoken words", "Title\nBody"
    )
    assert content == (
        "Video: https://vimeo.com/1\n"
        "Web page: https://www.clustre.net/a/\n\n"
        "## Page text\n\nTitle\nBody\n\n"
        "## Video transcript\n\nSpoken words\n"
    )


@pytest.mark.asyncio
async def test_fetch_page_text_returns_empty_text_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_page_text(client, "https://www.clustre.net/a/") == ""


@pytest.mark.asyncio
async def test_write_transcripts_adds_page_text_once_per_page(monkeypatch, tmp_path):
    page_requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page_requests.append(str(request.url))
        return httpx.Response(200, text=PAGE_HTML)

    async def fake_transcript(client, vimeo_id, article_url, token):
        return f"words {vimeo_id}"

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        scraper.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(scraper, "fetch_transcript_with_audio_fallback", fake_transcript)
    article = "https://www.clustre.net/why-engage/"
    files = await write_transcripts(
        tmp_path, {article: ["https://vimeo.com/1", "https://vimeo.com/2"]}, "token"
    )
    assert len(files) == 2
    assert page_requests == [article]
    content = files[0].read_text(encoding="utf-8")
    assert "## Page text\n\nWhy engage everyone\nNet Zero cannot fly" in content
    assert content.endswith("## Video transcript\n\nwords 1\n")


def test_format_progress():
    assert scraper.format_progress(3, 120) == "[3/120]"


@pytest.mark.asyncio
async def test_write_transcripts_logs_progress_for_every_video(monkeypatch, tmp_path):
    messages: list[str] = []

    class RecordingLogger:
        def __getattr__(self, level):
            return messages.append

    monkeypatch.setattr(scraper, "logger", RecordingLogger())
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=PAGE_HTML)

    async def fake_transcript(client, vimeo_id, article_url, token):
        return None if vimeo_id == "3" else f"words {vimeo_id}"

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        scraper.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(scraper, "fetch_transcript_with_audio_fallback", fake_transcript)
    article = "https://www.clustre.net/why-engage/"
    (tmp_path / scraper.transcript_file_name(article, "2")).write_text("old")
    links = [f"https://vimeo.com/{vimeo_id}" for vimeo_id in ("1", "2", "3")]
    await write_transcripts(tmp_path, {article: links}, "token")
    assert any(m.startswith("[1/3] Transcribing Vimeo video 1") for m in messages)
    assert any(m.startswith("[1/3] Wrote transcript") for m in messages)
    assert any(m.startswith("[2/3] Transcript already exists") for m in messages)
    assert any(m.startswith("[3/3] No transcript for Vimeo video 3") for m in messages)
