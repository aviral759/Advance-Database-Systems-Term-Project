"""Tests for the library endpoints and the extended telemetry (fake embedder, offline)."""
import io
import os

from fastapi.testclient import TestClient
from PIL import Image

from app.ingest import IngestItem
from app.main import app

SRC = "library-test"


def _noise_png() -> bytes:
    buf = io.BytesIO()
    Image.frombytes("RGB", (48, 36), os.urandom(48 * 36 * 3)).save(buf, "PNG")
    return buf.getvalue()


def test_library_collections_and_telemetry():
    with TestClient(app) as c:
        items = [
            IngestItem(data=_noise_png(), file_name="a.png", tags=["lib-alpha"], gps=(35.68, 139.69), source=SRC),
            IngestItem(data=_noise_png(), file_name="b.png", tags=["lib-alpha"], gps=(35.70, 139.70), source=SRC),
            IngestItem(data=_noise_png(), file_name="c.png", tags=["lib-beta"], source=SRC),
        ]
        res = c.app.state.ctx.ingestor.ingest(items, autotag=False)
        ids = [r["photo_id"] for r in res]
        assert all(r["status"] == "ingested" for r in res)

        page = c.get(f"/api/photos?source={SRC}&limit=2&sort=ingested").json()
        assert page["total"] == 3 and len(page["items"]) == 2
        assert page["items"][0]["id"] == max(ids)                     # newest first
        assert page["items"][0]["thumb_url"].endswith("/thumb")
        page2 = c.get(f"/api/photos?source={SRC}&limit=2&offset=2&sort=ingested").json()
        assert len(page2["items"]) == 1

        assert c.get("/api/photos?tag=lib-alpha").json()["total"] == 2
        geo = c.get(f"/api/photos?source={SRC}&geotagged=true").json()
        assert {i["file_name"] for i in geo["items"]} == {"a.png", "b.png"}
        picked = c.get(f"/api/photos?ids={ids[0]},{ids[2]}").json()
        assert {i["id"] for i in picked["items"]} == {ids[0], ids[2]}

        col = c.get("/api/collections").json()
        assert any(t["name"] == "lib-alpha" for t in col["tags"])
        assert any(s["name"] == SRC for s in col["sources"])
        tokyo = [p for p in col["places"] if abs(p["lat"] - 35.69) < 0.5]
        assert tokyo and tokyo[0]["count"] >= 2                       # both Tokyo photos clustered

        c.post("/api/search", json={"q": "anything", "k": 3})
        st = c.get("/api/stats").json()
        assert st["telemetry"]["searches"] >= 1 and st["telemetry"]["p50_ms"] is not None
        assert st["health"]["index_consistent"] is True
        for key in ("images_bytes", "thumbs_bytes", "disk_total", "disk_free"):
            assert key in st["storage"]
        assert st["vector_index"]["ram_bytes_estimate"] > 0