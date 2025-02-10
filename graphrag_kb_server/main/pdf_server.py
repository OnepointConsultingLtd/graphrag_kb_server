from pathlib import Path
from aiohttp import web
import uuid

from pdf_to_markdown_llm.service.pdf_to_text import convert_single_file, compact_files
from graphrag_kb_server.config import cfg
from graphrag_kb_server.utils.file_support import write_uploaded_file
from graphrag_kb_server.main.error_handler import handle_error

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
            pdf_dir = cfg.upload_dir/f"pdfs_{uuid.uuid4()}"
            if not pdf_dir.exists():
                pdf_dir.mkdir(parents=True, exist_ok=True)
            local_pdf: Path = write_uploaded_file(file, pdf_dir/file_name)
            process_result = await convert_single_file(local_pdf)
            if len(process_result.exceptions):
                return web.json_response(
                    {"error": "Uploaded file failed to process"}, status=500
                )
            dict_path = await compact_files([pdf_dir.as_posix()])
            result_files = list(dict_path.values())
            if len(result_files) > 0:
                markdown_file = result_files[0][0]
                return web.FileResponse(
                    markdown_file,
                    headers={
                        "CONTENT-DISPOSITION": f'attachment; filename="{markdown_file.name}"'
                    },
                )
            return web.json_response(
                {"error": "No file generated"}, status=404
            )
    return await handle_error(handle_request, request=request)
            
