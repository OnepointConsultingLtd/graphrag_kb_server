from pathlib import Path
from pdf_to_markdown_llm.service.openai_pdf_to_text import SupportedFormat
from pdf_to_markdown_llm.service.openai_pdf_to_text import (
    convert_single_file,
    compact_files,
)
from graphrag_kb_server.logger import logger

FINAL_SUFFIX = "_final.txt"


async def convert_pdf_to_markdown(local_pdf: Path) -> Path:
    process_result = await convert_single_file(local_pdf)
    if len(process_result.exceptions):
        raise Exception("Failed to convert PDF to markdown")
    dict_path = await compact_files(
        [local_pdf.parent.as_posix()], SupportedFormat.MARKDOWN
    )
    result_files = list(dict_path.values())
    if len(result_files) > 0:
        markdown_file = result_files[0][0]
        try:
            for f in local_pdf.parent.glob(f"{local_pdf.stem}*.md"):
                if not f.name.endswith("aggregate.md"):
                    logger.info(f"Deleting {f}")
                    f.unlink(missing_ok=True)
        except Exception:
            logger.error(f"Failed to delete {local_pdf.stem}*.md files")
        markdown_file.rename(
            markdown_file.parent
            / markdown_file.name.replace("_aggregate.md", FINAL_SUFFIX)
        )
        return markdown_file
    raise Exception("No file generated")
