from pathlib import Path
from aiohttp import web
import uuid

from graphrag_kb_server.config import cfg
from graphrag_kb_server.utils.file_support import write_uploaded_file
from graphrag_kb_server.main.error_handler import handle_error
from graphrag_kb_server.service.file_conversion import convert_pdf_to_markdown
from graphrag_kb_server.service.html_to_pdf import async_convert_html_to_pdf

from graphrag_kb_server.logger import logger

routes = web.RouteTableDef()


@routes.post("/protected/pdf")
async def convert_single_pdf(request: web.Request) -> web.Response:
    """
    Convert single PDF
    ---
    summary: Upload a single PDF file which is then converted to a single markdown file
    tags:
      - utils
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              file:
                type: string
                format: binary
                description: The PDF which is to be converted to a markdown file.
    responses:
      "200":
        description: A file with the content in markdown format
        content:
          text/markdown:
            example:
              Some markdown text
      "400":
        description: Bad Request - No file uploaded or invalid file format.
        content:
          application/json:
            example:
              status: "error"
              message: "No file was uploaded"
    """

    async def handle_request(request: web.Request) -> web.Response:
        body = request["data"]["body"]
        file = body["file"]
        file_name = body["file_name"]
        if file_name is not None and file_name.lower().endswith(".pdf"):
            pdf_dir = cfg.upload_dir / f"pdfs_{uuid.uuid4()}"
            if not pdf_dir.exists():
                pdf_dir.mkdir(parents=True, exist_ok=True)
            local_pdf: Path = write_uploaded_file(file, pdf_dir / file_name)
            try:
                markdown_file = await convert_pdf_to_markdown(local_pdf)
                return web.FileResponse(
                    markdown_file,
                    headers={
                        "CONTENT-DISPOSITION": f'attachment; filename="{markdown_file.name}"'
                    },
                )
            except Exception:
                return web.json_response(
                    {"error": "Uploaded file failed to process"}, status=500
                )

    return await handle_error(handle_request, request=request)


@routes.post("/protected/pdf/generate")
async def generate_pdf(request: web.Request) -> web.Response:
    """
    Convert single PDF
    ---
    summary: Generates PDFs from html
    tags:
      - utils
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              html:
                type: string
                description: The HTML to be converted
                default: "<html><body><h1>Test</h1><p style='font-weight: bold'>The Damerau–Levenshtein distance differs from the classical Levenshtein distance by including transpositions among its allowable operations in addition to the three classical single-character edit operations (insertions, deletions and substitutions).</p></body></html>"
    responses:
      "200":
        description: A PDF file with the content of the html
        content:
          application/pdf:
            example:
              Some markdown text
      "400":
        description: Bad Request - HTML is missing
        content:
          application/json:
            example:
              status: "error"
              message: "No file was uploaded"
    """
    async def handle_request(request: web.Request) -> web.Response:
        body = request["data"]["body"]
        html = body.get("html")
        if html is None or len(html.strip()) == 0:
            return web.json_response(
                {"error": "No HTML available. Please add the HTML to convert."}, status=400
            )
        # send the bytes to the client
        pdf_bytes = await async_convert_html_to_pdf(html)
        return web.Response(
            body=pdf_bytes,
            content_type='application/pdf',
            headers={
                'Content-Disposition': 'attachment; filename="document.pdf"'
            }
        )
    return await handle_error(handle_request, request=request)

logger.info("pdf_server.py loaded")
