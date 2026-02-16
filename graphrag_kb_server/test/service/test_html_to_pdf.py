from pathlib import Path


def test_convert_html_to_pdf():
    from graphrag_kb_server.service.html_to_pdf import convert_html_to_pdf

    html = "<html><body><h1>Title</h1><p>Here is some text<p></body></html>"
    res = convert_html_to_pdf(html)
    simple_pdf = Path("simple.pdf")
    simple_pdf.write_bytes(res)
    assert simple_pdf.exists()
