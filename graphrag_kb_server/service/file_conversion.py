import math
import logging
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment
from pdf_to_markdown_llm.service.openai_pdf_to_text import SupportedFormat, convert_file

from graphrag_kb_server.config import cfg

FINAL_SUFFIX = "_final.txt"

AUDIO_FILES = [".mp3", ".wav", ".m4a", ".ogg", ".flac"]

log = logging.getLogger(__name__)

async def convert_pdf_docx_pptx_to_markdown(local_doc: Path) -> Path:
    process_result = await convert_file(local_doc, SupportedFormat.MARKDOWN)
    if len(process_result.exceptions):
        raise Exception(
            f"Failed to convert PDF to markdown: {process_result.exceptions}"
        )
    return process_result.final_path


async def convert_audio(audio_file: Path, language="en", chunk_duration_ms=10 * 60 * 1000) -> Path:
    suffix = audio_file.suffix
    audio = AudioSegment.from_file(audio_file)
    client = OpenAI(api_key=cfg.openai_api_key)
    total_chunks = math.ceil(len(audio) / chunk_duration_ms)
    full_transcript = []
    previous_text = ""

    for i in range(total_chunks):
        start = i * chunk_duration_ms
        end = min((i + 1) * chunk_duration_ms, len(audio))
        chunk = audio[start:end]

        chunk_path = audio_file.parent / f"chunk_{i}{suffix}"
        chunk.export(chunk_path, format=suffix[1:])
        text = await convert_audio_chunked(chunk_path, prompt=previous_text, language=language, client=client)
        full_transcript.append(text)
        # Use the last ~200 words as context for the next chunk
        previous_text = " ".join(text.split()[-200:])
        try:
            chunk_path.unlink()
        except Exception as e:
            log.error(f"Failed to delete chunk file {chunk_path}: {e}")

    full_transcript_text = " ".join(full_transcript)
    output_file = audio_file.parent / f"{audio_file.stem}.txt"
    output_file.write_text(full_transcript_text, encoding="utf-8")
    return output_file


async def convert_audio_chunked(audio_file: Path, prompt: str = "", language="en", client: OpenAI = None) -> str:
    with open(audio_file, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model=cfg.audio_model,
            file=f,
            language=language,
            prompt=prompt or None,
        )
    return transcript.text


if __name__ == "__main__":
    import asyncio

    def check_file_conversion():
        local_doc = Path(__file__).parent.parent.parent / "data/powerpoint/sample1.pptx"
        assert local_doc.exists(), "File does not exist"
        asyncio.run(convert_pdf_docx_pptx_to_markdown(local_doc))
        

    def check_audio_conversion():
        local_audio = Path(__file__).parent.parent.parent / "data/audio/Clustre Podcast Without Zuhlke mention.mp3"
        assert local_audio.exists(), "File does not exist"
        asyncio.run(convert_audio(local_audio, language="en"))

    # check_file_conversion()
    check_audio_conversion()