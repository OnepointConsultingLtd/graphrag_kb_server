import asyncio
import subprocess
import tempfile
from pathlib import Path

import httpx
import yt_dlp

from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.file_conversion import convert_audio

AUDIO_FORMAT = "mp3"
# The embeddable player page works without a Vimeo login, unlike the web client
VIMEO_PLAYER_URL = "https://player.vimeo.com/video/{vimeo_id}"
VIMEO_API_VIDEO_URL = "https://api.vimeo.com/videos/{vimeo_id}"
VIMEO_API_ACCEPT = "application/vnd.vimeo.*+json;version=3.4"
API_TIMEOUT = 30
FFPROBE_TIMEOUT = 60
FFMPEG_TIMEOUT = 1800
# Mono and 64 kbit/s is plenty for speech to text and keeps the files small
FFMPEG_AUDIO_ARGS = ["-vn", "-map", "0:a:0", "-ac", "1", "-b:a", "64k"]


def build_download_options(
    vimeo_id: str, article_url: str, target_dir: Path
) -> dict:
    """Build the yt-dlp options which extract the audio of a Vimeo video as mp3.

    The article url is sent as referer because videos embedded on a website are
    often restricted to the domains they are embedded in. Impersonating a browser
    needs the curl-cffi extra of yt-dlp, otherwise Vimeo rejects the requests.
    """
    return {
        "format": "bestaudio/best",
        "outtmpl": str(target_dir / f"{vimeo_id}.%(ext)s"),
        "http_headers": {"Referer": article_url},
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": AUDIO_FORMAT,
            }
        ],
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "noplaylist": True,
    }


def download_vimeo_audio(
    vimeo_id: str, article_url: str, target_dir: Path
) -> Path | None:
    """Download the audio of a Vimeo video into target_dir with yt-dlp (blocking call).

    Returns the path of the mp3 file or None if the download failed.
    """
    options = build_download_options(vimeo_id, article_url, target_dir)
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([VIMEO_PLAYER_URL.format(vimeo_id=vimeo_id)])
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Failed to download audio for Vimeo video {vimeo_id}: {e}")
        return None
    audio_file = target_dir / f"{vimeo_id}.{AUDIO_FORMAT}"
    return audio_file if audio_file.exists() else None


def sort_download_links(download: list[dict]) -> list[str]:
    """Return the links of the Vimeo API download list, smallest rendition first.

    The smallest files are enough for speech to text. Entries without a link are ignored.
    """
    candidates = [entry for entry in download if entry.get("link")]
    candidates.sort(key=lambda entry: entry.get("size") or float("inf"))
    return [entry["link"] for entry in candidates]


async def fetch_api_download_links(
    client: httpx.AsyncClient, vimeo_id: str, token: str
) -> list[str]:
    """Ask the Vimeo API for the direct download links of a video, smallest first.

    The API only returns the download list when the token has the video_files
    scope and owns the video. Returns an empty list when no link is available.
    """
    try:
        response = await client.get(
            VIMEO_API_VIDEO_URL.format(vimeo_id=vimeo_id),
            headers={"Authorization": f"bearer {token}", "Accept": VIMEO_API_ACCEPT},
            params={"fields": "download.link,download.size,download.quality"},
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch download links for Vimeo video {vimeo_id}: {e}")
        return []
    payload = response.json()
    # Without the video_files scope the API answers with an empty list instead of an object
    download = payload.get("download") if isinstance(payload, dict) else None
    links = sort_download_links(download or [])
    if not links:
        logger.info(f"Vimeo API returned no download links for video {vimeo_id}")
    return links


def has_audio_stream(source: str) -> bool:
    """Check with ffprobe whether a file or url contains an audio stream (blocking call).

    Some small Vimeo renditions only contain video.
    """
    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                source,
            ],
            capture_output=True,
            text=True,
            timeout=FFPROBE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.error(f"ffprobe failed: {type(e).__name__}")
        return False
    return probe.returncode == 0 and "audio" in probe.stdout


def extract_audio_as_mp3(source: str, audio_file: Path) -> Path | None:
    """Let ffmpeg read the audio track of a file or url and write it as mp3 (blocking call).

    ffmpeg runs as separate process, so no file handle of the video stays open
    in this process, which would block the removal of temporary files on Windows.
    Returns None if ffmpeg failed.
    """
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", source, *FFMPEG_AUDIO_ARGS]
            + [str(audio_file)],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg failed to extract audio: {e.stderr.strip()[-300:]}")
        return None
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.error(f"ffmpeg failed to extract audio: {type(e).__name__}")
        return None
    return audio_file if audio_file.exists() else None


def extract_audio_from_first_link_with_audio(
    vimeo_id: str, links: list[str], audio_file: Path
) -> Path | None:
    """Extract the audio from the smallest download link which contains an audio stream."""
    for link in links:
        if has_audio_stream(link):
            return extract_audio_as_mp3(link, audio_file)
    logger.info(f"No download rendition with audio for Vimeo video {vimeo_id}")
    return None


async def download_audio_with_api(
    vimeo_id: str, token: str, target_dir: Path
) -> Path | None:
    """Get the audio through the download links of the Vimeo API.

    Returns the path of the mp3 file or None if the API offers no download links
    with audio or the extraction failed.
    """
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        links = await fetch_api_download_links(client, vimeo_id, token)
    if not links:
        return None
    return await asyncio.to_thread(
        extract_audio_from_first_link_with_audio,
        vimeo_id,
        links,
        target_dir / f"{vimeo_id}.{AUDIO_FORMAT}",
    )


async def download_audio(
    vimeo_id: str, article_url: str, token: str | None, target_dir: Path
) -> Path | None:
    """Download the audio of a Vimeo video, trying the Vimeo API before yt-dlp."""
    if token:
        audio_file = await download_audio_with_api(vimeo_id, token, target_dir)
        if audio_file is not None:
            return audio_file
    return await asyncio.to_thread(
        download_vimeo_audio, vimeo_id, article_url, target_dir
    )


async def transcribe_audio_file(audio_file: Path, language: str) -> str | None:
    """Transcribe an audio file and return the stripped text, or None if it is empty."""
    transcript_file = await convert_audio(audio_file, language=language)
    transcript = transcript_file.read_text(encoding="utf-8").strip()
    return transcript or None


async def transcribe_vimeo_audio(
    vimeo_id: str, article_url: str, token: str | None = None, language: str = "en"
) -> str | None:
    """Transcribe a Vimeo video with speech to text, as fallback for videos without text tracks.

    The audio is downloaded to a temporary folder which is removed afterwards.
    The Vimeo API is used first when a token is given, then yt-dlp.
    Returns the transcript or None if the audio could not be downloaded, is empty
    or the transcription failed, so that one broken video does not stop the sync.
    """
    # Windows can keep a file locked for a moment, which must not abort the sync
    with tempfile.TemporaryDirectory(
        prefix="vimeo_audio_", ignore_cleanup_errors=True
    ) as temp_dir:
        try:
            audio_file = await download_audio(
                vimeo_id, article_url, token, Path(temp_dir)
            )
            if audio_file is None:
                return None
            logger.info(f"Transcribing audio of Vimeo video {vimeo_id}")
            return await transcribe_audio_file(audio_file, language)
        except Exception as e:
            logger.error(f"Failed to transcribe Vimeo video {vimeo_id}: {e}")
            logger.exception(e)
            return None
