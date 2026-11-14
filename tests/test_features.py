"""Feature tests: every filter type, all strategies, fusion, similarity, errors,
read-only mode and the demo-token gate. Uses the fake embedder (no downloads)."""
import io
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app.main as main
from app.ingest import IngestItem

SRC = "feature-test"


def _jpeg(color, size=(80, 60)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG", quality=95)
    return buf.getvalue()


RED, GREEN, BLUE = _jpeg((250, 10, 10)), _jpeg((10, 250, 10)), _jpeg((10, 10, 250))


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        items = [
            IngestItem(data=RED, file_name="red.jpg", caption="a red kite over the beach", tags=["kite"],
                       objects=[{"label": "kite", "bbox": [0.05, 0.05, 0.4, 0.4]}],
                       taken_at="2012-05-01 10:00:00", gps=(51.5074, -0.1278), source=SRC),
            IngestItem(data=GREEN, file_name="green.jpg", caption="a green field with a dog", tags=["dog"],
                       objects=[{"label": "dog", "bbox": [0.6, 0.5, 0.95, 0.95]}],
                       taken_at="2015-07-01 10:00:00", gps=(48.8566, 2.3522), source=SRC),
            IngestItem(data=BLUE, file_name="blue.jpg", caption="a blue ocean and a boat", tags=["boat"],
                       taken_at="2018-01-01 10:00:00", source=SRC),
        ]
        res = c.app.state.ctx.ingestor.ingest(items, autotag=False)
        assert all(r["status"] == "ingested" for r in res), res
        yield c


def names(resp) -> set:
    assert resp.status_code == 200, resp.text
    return {r["file_name"] for r in resp.json()["results"]}


def search(c, q="", k=50, **filters):
    return c.post("/api/search", json={"q": q, "k": k, "filters": {"source": SRC, **filters}})


def test_tag_filter_is_metadata_only(client):
    r = search(client, tags=["dog"])
    assert names(r) == {"green.jpg"}
    assert r.json()["plan"]["strategy"] == "metadata_only"


def test_date_range_structured_and_inline(client):
    assert names(search(client, date_from="2014", date_to="2016")) == {"green.jpg"}
    r = client.post("/api/search", json={"q": "after:2017 source:feature-test", "k": 50})
    assert names(r) == {"blue.jpg"}


def test_geo_radius(client):
    assert names(search(client, near_lat=51.5, near_lon=-0.12, near_km=20)) == {"red.jpg"}
    assert names(search(client, near_lat=48.85, near_lon=2.35, near_km=5)) == {"green.jpg"}


def test_object_and_region(client):
    assert names(search(client, objects=["dog"])) == {"green.jpg"}
    assert names(search(client, objects=["dog"], region=[0.5, 0.5, 1, 1])) == {"green.jpg"}
    assert names(search(client, objects=["dog"], region=[0, 0, 0.5, 0.5])) == set()
    assert names(search(client, region=[0, 0, 0.5, 0.5])) == {"red.jpg"}


def test_fts_keyword_with_stemming(client):
    assert names(search(client, text="oceans")) == {"blue.jpg"}


def test_semantic_all_strategies_agree(client):
    sets = []
    for mode in ("auto", "filter_first", "vector_first"):
        r = client.post("/api/search", json={"q": "a boat on the water", "k": 50, "mode": mode,
                                             "filters": {"source": SRC}})
        body = r.json()
        assert body["plan"]["strategy"] in ("filter_first", "vector_first")
        if mode != "auto":
            assert body["plan"]["strategy"] == mode or body["plan"].get("strategy_fallback")
        assert all(x["score"] is not None for x in body["results"])
        sets.append(names(r))
    assert sets[0] == sets[1] == sets[2] == {"red.jpg", "green.jpg", "blue.jpg"}


def test_lexical_fusion_promotes_keyword_match(client):
    r = client.post("/api/search", json={"q": "kite beach", "k": 3, "lexical_weight": 1.0,
                                         "filters": {"source": SRC}})
    body = r.json()
    assert body["results"][0]["file_name"] == "red.jpg"
    assert body["results"][0]["lexical"] == pytest.approx(1.0)
    assert body["plan"]["lexical_query"]


def test_similar_and_query_by_image(client):
    red_id = search(client, tags=["kite"]).json()["results"][0]["id"]
    sim = client.post("/api/similar", json={"photo_id": red_id, "k": 5, "q": "source:feature-test"}).json()
    assert red_id not in {x["id"] for x in sim["results"]} and len(sim["results"]) == 2
    up = client.post("/api/similar/upload", files={"file": ("q.jpg", RED, "image/jpeg")},
                     data={"k": "3", "q": "source:feature-test"}).json()
    assert up["results"][0]["id"] == red_id
    assert up["results"][0]["cosine"] == pytest.approx(1.0, abs=1e-4)


def test_photo_detail(client):
    red_id = search(client, tags=["kite"]).json()["results"][0]["id"]
    d = client.get(f"/api/photos/{red_id}").json()
    assert d["gps_lat"] == pytest.approx(51.5074, abs=1e-4)
    assert d["objects"][0]["label"] == "kite"
    assert "kite" in {t["name"] for t in d["tags"]}
    assert d["has_embedding"] is True
    assert client.get(d["image_url"]).status_code == 200


def test_plan_structure(client):
    body = client.post("/api/search", json={"q": "a dog tag:dog", "k": 5}).json()
    p = body["plan"]
    for key in ("strategy", "reason", "steps", "timings_ms", "predicates", "estimates", "sql", "sqlite_query_plan"):
        assert key in p, key
    assert p["estimates"]["k_prime"] >= 1
    assert body["query"]["semantic_text"] == "a dog"


def test_validation_errors(client):
    assert search(client, region=[0, 0, 2, 2]).status_code == 422
    assert search(client, date_from="2013-13").status_code == 422
    assert client.post("/api/similar", json={"photo_id": 987654321}).status_code == 404
    assert client.get("/api/photos/987654321/image").status_code == 404
    r = client.post("/api/upload", files=[("files", ("bad.jpg", b"not an image", "image/jpeg"))]).json()
    assert r["results"][0]["status"] == "error"
    warn = client.post("/api/search", json={"q": "dog near:abc"}).json()
    assert warn["plan"]["warnings"]


def test_read_only_mode(client, monkeypatch):
    monkeypatch.setattr(main, "settings", replace(main.settings, read_only=True))
    r = client.post("/api/upload", files=[("files", ("x.png", _jpeg((1, 2, 3)), "image/jpeg"))])
    assert r.status_code == 403
    assert client.delete("/api/photos/1").status_code == 403


def test_demo_token_gate(client, monkeypatch):
    monkeypatch.setattr(main, "settings", replace(main.settings, demo_token="s3cret"))
    client.cookies.clear()
    assert client.get("/api/stats").status_code == 401
    assert client.get("/").status_code == 401
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/stats", headers={"x-demo-token": "s3cret"}).status_code == 200
    first = client.get("/?token=s3cret")
    assert first.status_code == 200 and "hps_token" in first.headers.get("set-cookie", "")
    assert client.get("/api/stats").status_code == 200          # cookie now carries the token
    client.cookies.clear()


def test_delete_then_rebuild(client):
    blue_id = search(client, tags=["boat"]).json()["results"][0]["id"]
    assert client.delete(f"/api/photos/{blue_id}").status_code == 200
    assert names(search(client)) == {"red.jpg", "green.jpg"}
    assert names(client.post("/api/search", json={"q": "a boat", "k": 50, "filters": {"source": SRC}})) == {"red.jpg", "green.jpg"}
    rebuilt = client.post("/api/admin/rebuild-index").json()
    assert rebuilt["removed"] >= 1