from weasyprint import HTML
from asyncer import asyncify


def convert_html_to_pdf(html: str) -> bytes:
    htmldoc = HTML(string=html, base_url="")
    return htmldoc.write_pdf()

async_convert_html_to_pdf = asyncify(convert_html_to_pdf)
