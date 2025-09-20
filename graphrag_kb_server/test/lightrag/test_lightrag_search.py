from graphrag_kb_server.service.lightrag.lightrag_search import _inject_keywords


def test_lightrag_search():
    hl_keywords = ["Artificial Intelligence", "Automation"]
    ll_keywords = ["Machine Learning", "Robotics"]
    query = """What is the capital of France?
<high_level_keywords>
  
</high_level_keywords>

<low_level_keywords>

</low_level_keywords>
"""
    query = _inject_keywords(query, hl_keywords, ll_keywords)
    assert all([k in query for k in hl_keywords])
    assert all([k in query for k in ll_keywords])