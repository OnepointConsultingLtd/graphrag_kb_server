import base64
from typing import Final

from aiohttp import BodyPartReader, web

SINGLE_FILE_FIELD: Final = "file"
MULTIPLE_FILES_FIELD: Final = "files"


async def read_binary_field(field: BodyPartReader) -> tuple[bytes, str | None]:
    """Reads a file part of a multipart request.

    Returns:
        The base64 encoded content of the file and its name.
    """
    return base64.b64encode(await field.read()), field.filename


async def multipart_form(request: web.Request) -> tuple[dict, bool]:
    """Parses a multipart request for the swagger validation.

    - A ``file`` part is stored base64 encoded under ``file`` with its name under ``file_name``.
    - Every ``files`` part is appended base64 encoded to the ``files`` list and its
      name to the ``files_names`` list, which allows uploading several files.
    - All other parts are decoded as UTF-8 text.
    """
    reader = await request.multipart()
    form = {}
    while True:
        field = await reader.next()
        if field is None:
            break
        field_name = field.name
        if field_name == SINGLE_FILE_FIELD:
            form[field_name], form[f"{field_name}_name"] = await read_binary_field(
                field
            )
        elif field_name == MULTIPLE_FILES_FIELD:
            content, file_name = await read_binary_field(field)
            form.setdefault(field_name, []).append(content)
            form.setdefault(f"{field_name}_names", []).append(file_name)
        else:
            form[field_name] = (await field.read()).decode("utf-8")
    return form, True
