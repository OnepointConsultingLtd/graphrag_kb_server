from graphrag_kb_server.model.search.entity import Abstraction, EntityWithScore
from graphrag_kb_server.service.search.matching import is_abbreviation_of, remove_abbreviations


def _entity(name: str, score: float = 1.0) -> EntityWithScore:
    return EntityWithScore(
        entity=name,
        score=score,
        reasoning="test",
        abstraction=Abstraction.HIGH_LEVEL,
    )


# ---------------------------------------------------------------------------
# is_abbreviation_of
# ---------------------------------------------------------------------------

def test_abbreviation_match():
    assert is_abbreviation_of("AI", "Artificial Intelligence")


def test_abbreviation_match_case_insensitive():
    assert is_abbreviation_of("ai", "Artificial Intelligence")


def test_abbreviation_no_match():
    assert not is_abbreviation_of("ML", "Artificial Intelligence")


def test_abbreviation_partial_match_is_false():
    # "AI" is not the abbreviation of "Artificial Intelligence Systems"
    assert not is_abbreviation_of("AI", "Artificial Intelligence Systems")


def test_abbreviation_single_word():
    # Single-word entity — its initial is just the first letter
    assert is_abbreviation_of("A", "Algorithms")
    assert not is_abbreviation_of("AI", "Algorithms")


# ---------------------------------------------------------------------------
# remove_abbreviations
# ---------------------------------------------------------------------------

def test_empty_list():
    assert remove_abbreviations([]) == []


def test_single_entity_preserved():
    entities = [_entity("Artificial Intelligence")]
    assert remove_abbreviations(entities) == entities


def test_abbreviation_is_removed():
    full = _entity("Artificial Intelligence", score=0.9)
    abbr = _entity("AI", score=0.8)
    result = remove_abbreviations([full, abbr])
    assert result == [full]
    assert _entity("AI") not in result


def test_abbreviation_is_removed_reverse_order():
    full = _entity("Artificial Intelligence", score=0.9)
    abbr = _entity("AI", score=0.8)
    result = remove_abbreviations([abbr, full])
    assert result == [full]
    assert _entity("AI") not in result


def test_non_abbreviation_entities_all_preserved():
    entities = [
        _entity("Machine Learning"),
        _entity("Natural Language Processing"),
        _entity("Computer Vision"),
    ]
    result = remove_abbreviations(entities)
    assert result == entities


def test_multiple_abbreviations_removed():
    ml = _entity("Machine Learning")
    nlp_full = _entity("Natural Language Processing")
    cv = _entity("Computer Vision")
    ml_abbr = _entity("ML")
    nlp_abbr = _entity("NLP")
    result = remove_abbreviations([ml, nlp_full, cv, ml_abbr, nlp_abbr])
    names = [e.entity for e in result]
    assert "ML" not in names
    assert "NLP" not in names
    assert "Machine Learning" in names
    assert "Natural Language Processing" in names
    assert "Computer Vision" in names


def test_order_preserved_for_non_abbreviations():
    entities = [_entity("B"), _entity("A"), _entity("C")]
    result = remove_abbreviations(entities)
    assert [e.entity for e in result] == ["B", "A", "C"]


def test_duplicate_full_names_not_deduplicated():
    # remove_abbreviations only removes abbreviations, not exact duplicates
    e1 = _entity("Artificial Intelligence", score=0.9)
    e2 = _entity("Artificial Intelligence", score=0.8)
    result = remove_abbreviations([e1, e2])
    # e2 is not an abbreviation of e1, so both are kept
    assert len(result) == 2
