from app.planner import CostModel, build_predicates, fts_query, parse_query


def test_parse_query_extracts_filters():
    text, f, warnings = parse_query(
        "dog on beach tag:Dog after:2013-01 before:2014 near:48.85,2.35,10 object:person region:0,0,0.5,1")
    assert text == "dog on beach"
    assert f.tags == ["dog"] and f.objects == ["person"]
    assert f.near == (48.85, 2.35, 10.0)
    assert f.region == (0.0, 0.0, 0.5, 1.0)
    assert f.date_from < f.date_to
    assert not warnings


def test_parse_query_bad_token_warns_and_unknown_keys_kept():
    text, f, warnings = parse_query("sunset near:abc foo:bar")
    assert f.near is None and warnings
    assert "foo:bar" in text


def test_fts_query_sanitises():
    assert fts_query('the "red" car!', "OR", drop_stop=True) == '"red" OR "car"'
    assert fts_query("", "AND") == ""


def test_predicates_built():
    _, f, _ = parse_query("tag:cat object:person region:0,0.5,1,1 text:kitchen")
    preds, _ = build_predicates(f)
    assert {p.kind for p in preds} == {"tag", "object", "text"}


def test_cost_model_crossover():
    cm, n, d, k = CostModel(), 100_000, 512, 24
    # rare predicate → filter-first must win
    ff_rare = cm.filter_first(0.001 * n, d)
    vf_rare, kp_rare, _ = cm.vector_first(k, 0.001, n, 64)
    assert ff_rare < vf_rare and kp_rare >= cm.degenerate_ratio * n
    # common predicate → vector-first must win
    ff_common = cm.filter_first(0.8 * n, d)
    vf_common, kp_common, _ = cm.vector_first(k, 0.8, n, 64)
    assert vf_common < ff_common and kp_common < 100