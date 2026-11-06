from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from graphrag_kb_server.service import file_conversion, index_support
from graphrag_kb_server.service.project_config_service import ProjectConfig

FILE_CONVERSION = "graphrag_kb_server.service.file_conversion"
INDEX_SUPPORT = "graphrag_kb_server.service.index_support"


def make_config(**overrides) -> ProjectConfig:
    return replace(ProjectConfig.from_env(), project_label="tenant/project", **overrides)


class FakeAudioChunk:
    def export(self, path, format):
        Path(path).write_bytes(b"audio")


class FakeAudio:
    """A one second audio, so that it is transcribed in a single chunk."""

    def __len__(self):
        return 1000

    def __getitem__(self, chunk_range):
        return FakeAudioChunk()


class FakeAudioSegment:
    @staticmethod
    def from_file(audio_file):
        return FakeAudio()


class FakeOpenAI:
    created: list["FakeOpenAI"] = []

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.models_used: list[str] = []
        self.audio = SimpleNamespace(
            transcriptions=SimpleNamespace(create=self._transcribe)
        )
        FakeOpenAI.created.append(self)

    def _transcribe(self, model, file, language, prompt):
        self.models_used.append(model)
        return SimpleNamespace(text="hello world")


@pytest.fixture
def fake_audio(monkeypatch):
    FakeOpenAI.created = []
    monkeypatch.setattr(f"{FILE_CONVERSION}.AudioSegment", FakeAudioSegment)
    monkeypatch.setattr(f"{FILE_CONVERSION}.OpenAI", FakeOpenAI)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key, model",
    [("openai-a", "audio-model-a"), ("openai-b", "audio-model-b")],
)
async def test_convert_audio_uses_key_and_audio_model_of_the_project(
    fake_audio, tmp_path, key, model
):
    audio_file = tmp_path / "talk.mp3"
    audio_file.write_bytes(b"audio")
    config = make_config(openai_api_key=key, audio_model=model)

    transcript_file = await file_conversion.convert_audio(audio_file, config=config)

    assert transcript_file.read_text(encoding="utf-8") == "hello world"
    client = FakeOpenAI.created[0]
    assert client.api_key == key
    assert client.models_used == [model]
    assert not (tmp_path / "chunk_0.mp3").exists()


@pytest.mark.asyncio
async def test_convert_audio_without_key_falls_back_to_sdk_lookup(fake_audio, tmp_path):
    audio_file = tmp_path / "talk.mp3"
    audio_file.write_bytes(b"audio")
    await file_conversion.convert_audio(
        audio_file, config=make_config(openai_api_key="", audio_model="m")
    )
    assert FakeOpenAI.created[0].api_key is None


@pytest.mark.asyncio
async def test_convert_to_text_transcribes_audio_with_the_config_of_the_project(
    monkeypatch, tmp_path
):
    project_dir = tmp_path / "tenant" / "lightrag" / "project"
    input_folder = project_dir / "input"
    input_folder.mkdir(parents=True)
    (input_folder / "talk.mp3").write_bytes(b"audio")
    config = make_config(openai_api_key="project-key")
    lookup = AsyncMock(return_value=config)
    convert_audio = AsyncMock()
    monkeypatch.setattr(f"{INDEX_SUPPORT}.get_project_config_for_dir", lookup)
    monkeypatch.setattr(f"{INDEX_SUPPORT}.convert_audio", convert_audio)

    await index_support.convert_to_text(input_folder, project_dir)

    lookup.assert_awaited_once_with(project_dir)
    convert_audio.assert_awaited_once_with(
        input_folder / "talk.mp3", language="en", config=config
    )


@pytest.mark.asyncio
async def test_convert_to_text_without_audio_does_not_resolve_the_config(
    monkeypatch, tmp_path
):
    project_dir = tmp_path / "tenant" / "lightrag" / "project"
    input_folder = project_dir / "input"
    input_folder.mkdir(parents=True)
    (input_folder / "notes.md").write_text("# notes", encoding="utf-8")
    lookup = AsyncMock()
    monkeypatch.setattr(f"{INDEX_SUPPORT}.get_project_config_for_dir", lookup)

    await index_support.convert_to_text(input_folder, project_dir)

    lookup.assert_not_awaited()
    assert (input_folder / "notes.txt").read_text(encoding="utf-8") == "# notes"
