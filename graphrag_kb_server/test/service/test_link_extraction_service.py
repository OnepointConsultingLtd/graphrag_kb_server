from pathlib import Path

from graphrag_kb_server.service.file_find_service import ORIGINAL_INPUT_FOLDER
from graphrag_kb_server.service.link_extraction_service import extract_links


def test_extract_links_when_original_input_missing(tmp_path: Path) -> None:
    """When project_dir has no original_input folder, returns empty list."""
    assert extract_links(tmp_path) == []


def test_extract_links_when_original_input_empty(tmp_path: Path) -> None:
    """When original_input exists but has no .txt/.md files, returns empty list."""
    (tmp_path / ORIGINAL_INPUT_FOLDER).mkdir()
    assert extract_links(tmp_path) == []


def test_extract_links_txt_file_no_urls(tmp_path: Path) -> None:
    """A .txt file with no URLs returns one entry with empty link list."""
    original = tmp_path / ORIGINAL_INPUT_FOLDER
    original.mkdir()
    (original / "readme.txt").write_text("No links here.", encoding="utf-8")
    result = extract_links(tmp_path)
    assert len(result) == 1
    path, links = result[0]
    assert path.endswith("readme.txt")
    assert links == []


def test_extract_links_txt_file_with_one_url(tmp_path: Path) -> None:
    """A .txt file with one URL returns that URL."""
    original = tmp_path / ORIGINAL_INPUT_FOLDER
    original.mkdir()
    (original / "doc.txt").write_text(
        "See https://example.com for more.",
        encoding="utf-8",
    )
    result = extract_links(tmp_path)
    assert len(result) == 1
    path, links = result[0]
    assert path.endswith("doc.txt")
    assert links == ["https://example.com"]


def test_extract_links_txt_file_with_multiple_urls(tmp_path: Path) -> None:
    """A .txt file with multiple URLs returns all of them."""
    original = tmp_path / ORIGINAL_INPUT_FOLDER
    original.mkdir()
    (original / "links.txt").write_text(
        "First https://a.com and then http://b.org end.",
        encoding="utf-8",
    )
    result = extract_links(tmp_path)
    assert len(result) == 1
    _, links = result[0]
    assert "https://a.com" in links
    assert "http://b.org" in links
    assert len(links) == 2


def test_extract_links_md_file_accepted(tmp_path: Path) -> None:
    """Markdown files are accepted and URLs are extracted."""
    original = tmp_path / ORIGINAL_INPUT_FOLDER
    original.mkdir()
    (original / "notes.md").write_text(
        "Check https://example.org",
        encoding="utf-8",
    )
    result = extract_links(tmp_path)
    assert len(result) == 1
    path, links = result[0]
    assert path.endswith("notes.md")
    assert links == ["https://example.org"]


def test_extract_links_skips_non_accepted_extensions(tmp_path: Path) -> None:
    """Files with extensions other than .txt/.md are skipped."""
    original = tmp_path / ORIGINAL_INPUT_FOLDER
    original.mkdir()
    (original / "page.html").write_text(
        "Link: https://skip.me",
        encoding="utf-8",
    )
    (original / "doc.txt").write_text(
        "Link: https://count.me",
        encoding="utf-8",
    )
    result = extract_links(tmp_path)
    assert len(result) == 1
    _, links = result[0]
    assert links == ["https://count.me"]


def test_extract_links_multiple_files(tmp_path: Path) -> None:
    """Multiple accepted files each get an entry (path, links)."""
    original = tmp_path / ORIGINAL_INPUT_FOLDER
    original.mkdir()
    (original / "a.txt").write_text("https://first.com", encoding="utf-8")
    (original / "b.md").write_text("https://second.com", encoding="utf-8")
    result = extract_links(tmp_path)
    assert len(result) == 2
    paths = [p for p, _ in result]
    links = [links for _, links in result]
    assert any("a.txt" in p for p in paths)
    assert any("b.md" in p for p in paths)
    assert ["https://first.com"] in links
    assert ["https://second.com"] in links


def test_extract_links_subdirectory(tmp_path: Path) -> None:
    """Files in subdirectories of original_input are included."""
    original = tmp_path / ORIGINAL_INPUT_FOLDER
    sub = original / "sub"
    sub.mkdir(parents=True)
    (sub / "nested.txt").write_text("https://nested.com", encoding="utf-8")
    result = extract_links(tmp_path)
    assert len(result) == 1
    path, links = result[0]
    assert "sub" in path and "nested.txt" in path
    assert links == ["https://nested.com"]
