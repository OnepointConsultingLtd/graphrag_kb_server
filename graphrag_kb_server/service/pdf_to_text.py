import sys
import asyncio
from dotenv import load_dotenv

# ruff: noqa: E402
load_dotenv()

from pdf_to_markdown_llm.service.openai_pdf_to_text import (
    convert_all_pdfs,
    compact_files,
    zip_md_files,
)


if __name__ == "__main__":

    if len(sys.argv) < 3:
        sys.stderr.write(
            """Please specify the command and the directory
Example: convert python ./graphrag_kb_server/service/pdf_to_text.py /development/onepoint/thinqwin/graphrag_kb_server/docs/hypergility
"""
        )
        sys.exit(1)

    command = sys.argv[1]
    directories = sys.argv[2:]

    match command:
        case "convert":
            asyncio.run(convert_all_pdfs(directories, False))
        case "compact":
            folder_files = asyncio.run(compact_files(directories))
            zip_files = zip_md_files(folder_files)
            for zip_file in zip_files:
                print(zip_file)
        case _:
            sys.stderr.write(f"Command {command} not found.")
