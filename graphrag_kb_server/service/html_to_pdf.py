from weasyprint import HTML
from asyncer import asyncify


def convert_html_to_pdf(html: str) -> bytes:
    html = html.replace("</head>", """
<style>
  @font-face {
    font-family: 'Noto Sans Devanagari';
    src: url('https://fonts.gstatic.com/s/notosansdevanagari/v26/TuGoUUFzXI5FBtUq5a8bjKYTZjtRU6Sgv3NaV_SNmI0b2TFnDJKNvOkFfQ.woff2') format('woff2');
  }
  body { font-family: 'Noto Sans Devanagari', sans-serif; }
</style>
</head>""")
    htmldoc = HTML(string=html, base_url="")
    return htmldoc.write_pdf()


async_convert_html_to_pdf = asyncify(convert_html_to_pdf)
