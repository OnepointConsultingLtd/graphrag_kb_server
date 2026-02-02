from pathlib import Path
from pdf_to_markdown_llm.service.openai_pdf_to_text import SupportedFormat, convert_file

FINAL_SUFFIX = "_final.txt"


async def convert_pdf_to_markdown(local_pdf: Path) -> Path:
    process_result = await convert_file(local_pdf, SupportedFormat.MARKDOWN)
    if len(process_result.exceptions):
        raise Exception(
            f"Failed to convert PDF to markdown: {process_result.exceptions}"
        )
    return process_result.final_path
