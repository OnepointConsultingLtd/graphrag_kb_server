from pathlib import Path
from pdf_to_markdown_llm.service.pdf_to_text import remove_markdown_tags


def test_remove_markdown_tags():
    markdown_file = (
        Path(__file__).parent
        / "../../docs/markdown/Algorithmic-impact-assessment-user-guide_aggregate.md"
    )
    assert markdown_file.exists(), "Cannot find file"
    clean = remove_markdown_tags(markdown_file, False)
    output_file = markdown_file.parent / f"{markdown_file.stem}_changed.md"
    output_file.write_text(clean, encoding="utf-8")
    assert "```markdown" not in clean, "Markdown tags still in markdown"
