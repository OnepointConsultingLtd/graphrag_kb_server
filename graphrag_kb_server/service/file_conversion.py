from pathlib import Path
from pdf_to_markdown_llm.service.openai_pdf_to_text import SupportedFormat, convert_file

FINAL_SUFFIX = "_final.txt"


async def convert_pdf_docx_pptx_to_markdown(local_doc: Path) -> Path:
    process_result = await convert_file(local_doc, SupportedFormat.MARKDOWN)
    if len(process_result.exceptions):
        raise Exception(
            f"Failed to convert PDF to markdown: {process_result.exceptions}"
        )
    return process_result.final_path


if __name__ == "__main__":
    import asyncio

    local_doc = Path(__file__).parent.parent.parent / "data/powerpoint/sample1.pptx"
    assert local_doc.exists(), "File does not exist"
    asyncio.run(convert_pdf_docx_pptx_to_markdown(local_doc))