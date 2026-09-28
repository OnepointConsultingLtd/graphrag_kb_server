import httpx
import pytest

from graphrag_kb_server.service.parser.clustre_vimeo_parser import (
    CLUSTRE_VIDEOS_URL,
    extract_article_urls,
    extract_next_page_url,
    extract_vimeo_links,
    fetch_transcript,
    transcript_content,
    transcript_file_name,
    vtt_to_text,
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
