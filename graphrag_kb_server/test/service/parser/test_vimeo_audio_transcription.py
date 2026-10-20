import subprocess
from pathlib import Path

import httpx
import pytest

from graphrag_kb_server.service.parser import vimeo_audio_transcription as module
from graphrag_kb_server.service.parser.vimeo_audio_transcription import (
    build_download_options,
    download_audio,
    extract_audio_as_mp3,
    extract_audio_from_first_link_with_audio,
    fetch_api_download_links,
    has_audio_stream,
    sort_download_links,
    transcribe_vimeo_audio,
)


def test_build_download_options_sets_referer_and_output(tmp_path: Path):
    options = build_download_options("123", "https://www.clustre.net/a/", tmp_path)
    assert options["http_headers"] == {"Referer": "https://www.clustre.net/a/"}
    assert options["outtmpl"] == str(tmp_path / "123.%(ext)s")
    assert options["postprocessors"][0]["preferredcodec"] == "mp3"


@pytest.mark.asyncio
async def test_transcribe_returns_none_when_download_fails(monkeypatch):
    monkeypatch.setattr(module, "download_vimeo_audio", lambda *args: None)
    assert await transcribe_vimeo_audio("123", "https://www.clustre.net/a/") is None


@pytest.mark.asyncio
async def test_transcribe_converts_downloaded_audio(monkeypatch):
    def fake_download(vimeo_id: str, article_url: str, target_dir: Path) -> Path:
        audio_file = target_dir / f"{vimeo_id}.mp3"
        audio_file.write_bytes(b"audio")
        return audio_file

    async def fake_convert_audio(audio_file: Path, language: str = "en") -> Path:
        transcript_file = audio_file.parent / f"{audio_file.stem}.txt"
        transcript_file.write_text(" Hello world \n", encoding="utf-8")
        return transcript_file

    monkeypatch.setattr(module, "download_vimeo_audio", fake_download)
    monkeypatch.setattr(module, "convert_audio", fake_convert_audio)
    transcript = await transcribe_vimeo_audio("123", "https://www.clustre.net/a/")
    assert transcript == "Hello world"


@pytest.mark.asyncio
async def test_transcribe_returns_none_instead_of_raising_on_failure(monkeypatch):
    def fake_download(vimeo_id: str, article_url: str, target_dir: Path) -> Path:
        audio_file = target_dir / f"{vimeo_id}.mp3"
        audio_file.write_bytes(b"audio")
        return audio_file

    async def failing_convert_audio(audio_file: Path, language: str = "en") -> Path:
        raise RuntimeError("transcription service down")

    monkeypatch.setattr(module, "download_vimeo_audio", fake_download)
    monkeypatch.setattr(module, "convert_audio", failing_convert_audio)
    assert await transcribe_vimeo_audio("123", "https://www.clustre.net/a/") is None


def test_sort_download_links_orders_by_size_and_skips_missing_links():
    download = [
        {"quality": "hd", "size": 900, "link": "https://dl.test/hd.mp4"},
        {"quality": "sd", "size": 100, "link": "https://dl.test/sd.mp4"},
        {"quality": "source", "size": 10, "link": None},
    ]
    assert sort_download_links(download) == [
        "https://dl.test/sd.mp4",
        "https://dl.test/hd.mp4",
    ]


def test_sort_download_links_without_links():
    assert sort_download_links([]) == []
    assert sort_download_links([{"size": 1, "link": None}]) == []


def _api_client(payload: dict | list, status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.vimeo.com"
        assert request.headers["Authorization"] == "bearer token"
        return httpx.Response(status_code, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_fetch_api_download_links_returns_sorted_links():
    payload = {
        "download": [
            {"size": 50, "link": "https://dl.test/big.mp4"},
            {"size": 5, "link": "https://dl.test/small.mp4"},
        ]
    }
    async with _api_client(payload) as client:
        links = await fetch_api_download_links(client, "123", "token")
    assert links == ["https://dl.test/small.mp4", "https://dl.test/big.mp4"]


@pytest.mark.asyncio
async def test_fetch_api_download_links_empty_without_video_files_scope():
    async with _api_client({"uri": "/videos/123"}) as client:
        assert await fetch_api_download_links(client, "123", "token") == []


@pytest.mark.asyncio
async def test_fetch_api_download_links_empty_when_api_returns_empty_list():
    async with _api_client([]) as client:
        assert await fetch_api_download_links(client, "123", "token") == []


@pytest.mark.asyncio
async def test_fetch_api_download_links_empty_on_http_error():
    async with _api_client({"error": "nope"}, status_code=404) as client:
        assert await fetch_api_download_links(client, "123", "token") == []


def _fake_run(returncode: int = 0, stdout: str = "", stderr: str = ""):
    def run(command, **kwargs):
        if kwargs.get("check") and returncode != 0:
            raise subprocess.CalledProcessError(
                returncode, command, output=stdout, stderr=stderr
            )
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    return run


def test_has_audio_stream_true_when_ffprobe_reports_audio(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(stdout="audio\n"))
    assert has_audio_stream("https://dl.test/a.mp4") is True


def test_has_audio_stream_false_for_video_only_file(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(stdout=""))
    assert has_audio_stream("https://dl.test/a.mp4") is False


def test_has_audio_stream_false_when_ffprobe_is_missing(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(subprocess, "run", missing)
    assert has_audio_stream("https://dl.test/a.mp4") is False


def test_extract_audio_as_mp3_returns_none_when_ffmpeg_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", _fake_run(returncode=1, stderr="boom"))
    assert extract_audio_as_mp3("https://dl.test/a.mp4", tmp_path / "a.mp3") is None


def test_extract_audio_as_mp3_returns_file_written_by_ffmpeg(monkeypatch, tmp_path):
    audio_file = tmp_path / "a.mp3"

    def run(command, **kwargs):
        audio_file.write_bytes(b"mp3")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    assert extract_audio_as_mp3("https://dl.test/a.mp4", audio_file) == audio_file


def test_extract_uses_smallest_link_with_audio(monkeypatch, tmp_path):
    audio_file = tmp_path / "123.mp3"
    links = ["https://dl.test/video_only.mp4", "https://dl.test/with_audio.mp4"]
    extracted: list[str] = []
    monkeypatch.setattr(
        module, "has_audio_stream", lambda link: link.endswith("with_audio.mp4")
    )

    def fake_extract(source: str, target: Path) -> Path:
        extracted.append(source)
        return target

    monkeypatch.setattr(module, "extract_audio_as_mp3", fake_extract)
    result = extract_audio_from_first_link_with_audio("123", links, audio_file)
    assert result == audio_file
    assert extracted == ["https://dl.test/with_audio.mp4"]


def test_extract_returns_none_when_no_link_has_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(module, "has_audio_stream", lambda link: False)

    def fail_extract(source: str, target: Path) -> Path:
        raise AssertionError("must not extract without audio")

    monkeypatch.setattr(module, "extract_audio_as_mp3", fail_extract)
    links = ["https://dl.test/a.mp4"]
    assert (
        extract_audio_from_first_link_with_audio("123", links, tmp_path / "a.mp3")
        is None
    )


@pytest.mark.asyncio
async def test_download_audio_uses_api_before_yt_dlp(monkeypatch, tmp_path: Path):
    api_audio = tmp_path / "123.mp3"

    async def fake_api(vimeo_id: str, token: str, target_dir: Path) -> Path:
        return api_audio

    def fail_yt_dlp(*args):
        raise AssertionError("yt-dlp must not run when the API works")

    monkeypatch.setattr(module, "download_audio_with_api", fake_api)
    monkeypatch.setattr(module, "download_vimeo_audio", fail_yt_dlp)
    assert await download_audio("123", "https://a/", "token", tmp_path) == api_audio


@pytest.mark.asyncio
async def test_download_audio_falls_back_to_yt_dlp_without_api_links(
    monkeypatch, tmp_path: Path
):
    yt_dlp_audio = tmp_path / "yt.mp3"

    async def api_without_links(vimeo_id: str, token: str, target_dir: Path):
        return None

    monkeypatch.setattr(module, "download_audio_with_api", api_without_links)
    monkeypatch.setattr(module, "download_vimeo_audio", lambda *args: yt_dlp_audio)
    assert await download_audio("123", "https://a/", "token", tmp_path) == yt_dlp_audio


@pytest.mark.asyncio
async def test_download_audio_skips_api_without_token(monkeypatch, tmp_path: Path):
    async def fail_api(*args):
        raise AssertionError("API must not be used without a token")

    monkeypatch.setattr(module, "download_audio_with_api", fail_api)
    monkeypatch.setattr(module, "download_vimeo_audio", lambda *args: None)
    assert await download_audio("123", "https://a/", None, tmp_path) is None
