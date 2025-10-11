from datetime import datetime
from graphrag_kb_server.utils.date_support import convert_linkedin_date


def test_convert_linkedin_date():
    date_str = "Oct 2009"
    dt = convert_linkedin_date(date_str)
    assert dt == datetime(2009, 10, 1)
