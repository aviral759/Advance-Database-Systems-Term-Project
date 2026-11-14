import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


def _png(color, size=(64, 48)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def test_end_to_end():
    with TestClient(app) as client:
        files = [("files", (f"c{i}.png", _png((i * 40 % 256, 80, 200 - i * 10)), "image/png")) for i in range(6)]
        r = client.post("/api/upload", files=files, data={"caption": "a red test card", "tags": "test,synthetic"})
        assert r.status_code == 200, r.text
        assert sum(x["status"] == "ingested" for x in r.json()["results"]) == 6

        dup = client.post("/api/upload", files=files[:1]).json()["results"][0]
        assert dup["status"] == "duplicate"

        for mode in ("auto", "filter_first", "vector_first"):
            s = client.post("/api/search", json={"q": "test card tag:test", "k": 5, "mode": mode}).json()
            assert len(s["results"]) == 5
            assert s["plan"]["strategy"] in {"filter_first", "vector_first"}
            assert s["plan"]["timings_ms"]["total"] > 0

        meta = client.post("/api/search", json={"q": "tag:synthetic"}).json()
        assert meta["plan"]["strategy"] == "metadata_only" and len(meta["results"]) == 6

        pid = meta["results"][0]["id"]
        sim = client.post("/api/similar", json={"photo_id": pid, "k": 3}).json()
        assert len(sim["results"]) == 3 and all(x["id"] != pid for x in sim["results"])

        detail = client.get(f"/api/photos/{pid}").json()
        assert detail["has_embedding"] and {t["name"] for t in detail["tags"]} >= {"test", "synthetic"}
        assert client.get(f"/api/photos/{pid}/thumb").status_code == 200

        assert client.delete(f"/api/photos/{pid}").status_code == 200
        after = client.post("/api/search", json={"q": "test card", "k": 10}).json()
        assert all(x["id"] != pid for x in after["results"])

        st = client.get("/api/stats").json()
        assert st["library"]["photos"] == 5 and st["storage"]["journal_mode"].lower() == "wal"