"""End-to-end smoke test against a RUNNING server (real OpenCLIP model, real data).

Exercises every endpoint and feature: health, dashboard, stats, browse, semantic
search, tag / date / geo / object / region / keyword filters, forced strategies,
lexical fusion, photo detail, image + thumbnail, image-to-image, query-by-image,
validation errors, upload → search → delete, and admin calibration.

Usage:
  python scripts/smoke_test.py
  python scripts/smoke_test.py --base-url https://xyz.trycloudflare.com --token abc123
  python scripts/smoke_test.py --skip-write          # read-only servers
"""
import argparse
import io
import os
import sys
import time

import requests
from PIL import Image

if os.name == "nt":
    os.system("")  # enable ANSI colours in Windows consoles

COLOR = {"PASS": "\033[92m", "WARN": "\033[93m", "FAIL": "\033[91m", "ERROR": "\033[91m", "SKIP": "\033[90m"}
RESET = "\033[0m"


class Skip(Exception):
    pass


class Runner:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.s = requests.Session()
        if token:
            self.s.headers["x-demo-token"] = token
        self.results = []

    def req(self, method, path, **kw):
        return self.s.request(method, self.base + path, timeout=180, **kw)

    def search(self, q="", expect=200, **body):
        body = {"q": q, "k": body.pop("k", 24), **body}
        r = self.req("POST", "/api/search", json=body)
        assert r.status_code == expect, f"HTTP {r.status_code}: {r.text[:200]}"
        return r.json()

    def detail(self, pid):
        r = self.req("GET", f"/api/photos/{pid}")
        assert r.status_code == 200, f"detail HTTP {r.status_code}"
        return r.json()

    def check(self, name, fn):
        t0 = time.perf_counter()
        try:
            out = fn()
            status, detail = out if isinstance(out, tuple) else ("PASS", out or "")
        except Skip as e:
            status, detail = "SKIP", str(e)
        except AssertionError as e:
            status, detail = "FAIL", str(e) or "assertion failed"
        except Exception as e:  # noqa: BLE001
            status, detail = "ERROR", f"{type(e).__name__}: {e}"
        ms = (time.perf_counter() - t0) * 1000
        self.results.append(status)
        print(f"{COLOR[status]}{status:<5}{RESET} {name:<44} {ms:>8.1f} ms  {detail}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--token", default="")
    ap.add_argument("--skip-write", action="store_true")
    args = ap.parse_args()
    r = Runner(args.base_url, args.token)
    ctx: dict = {}
    print(f"Smoke-testing {r.base}\n")

    def health():
        resp = r.req("GET", "/api/health")
        assert resp.status_code == 200 and resp.json()["status"] == "ok"
    r.check("health endpoint", health)

    def dashboard():
        resp = r.req("GET", "/")
        assert resp.status_code == 200 and "HybridSearch" in resp.text.replace("<span>", "").replace("</span>", ""), "index.html not served"
        for asset in ("/styles.css", "/app.js"):
            assert r.req("GET", asset).status_code == 200, f"{asset} missing"
    r.check("dashboard + static assets served", dashboard)

    def stats():
        s = r.req("GET", "/api/stats").json()
        assert s["library"]["photos"] > 0, "library is empty: ingest a dataset first"
        assert s["storage"]["journal_mode"].lower() == "wal", "WAL not enabled"
        caps = s["storage"]["capabilities"]
        assert caps["fts5"] and caps["rtree"], "FTS5/R*Tree missing"
        ctx["stats"] = s
        return f"{s['library']['photos']} photos, {s['vector_index']['active']} vectors, model {s['embedding']['model_id']}"
    r.check("stats + WAL/FTS5/R*Tree capabilities", stats)
    if "stats" not in ctx:
        sys.exit("Cannot continue without a populated library.")
    S = ctx["stats"]
    tags = [t["name"] for t in S["top_tags"] if t["name"] != "synthetic-geo"]

    def browse():
        d = r.search("")
        assert d["plan"]["strategy"] == "metadata_only" and d["results"]
        ctx["any_id"] = d["results"][0]["id"]
        return f"{len(d['results'])} latest photos"
    r.check("browse (metadata-only plan)", browse)

    def semantic():
        d = r.search("a dog playing outside")
        assert d["plan"]["strategy"] == "vector_only", d["plan"]["strategy"]
        assert len(d["results"]) == min(24, S["vector_index"]["active"])
        return f"top score {d['results'][0]['score']:.3f}"
    r.check("semantic text search (vector-only)", semantic)

    def semantic_quality():
        d = r.search("a photo of a dog", k=10)
        hits = sum("dog" in x["tags"] for x in d["results"])
        return ("PASS" if hits >= 5 else "WARN", f"{hits}/10 top results tagged 'dog'")
    r.check("semantic relevance sanity (dog)", semantic_quality)

    def common_tag():
        if not tags:
            raise Skip("no tags")
        tag = tags[0]
        d = r.search(f"people outdoors tag:{tag}")
        assert all(tag in x["tags"] for x in d["results"]), "result without the tag"
        ctx["common_tag"] = tag
        return f"tag:{tag} → {d['plan']['strategy']} (s≈{d['plan']['estimates']['selectivity']:.3f})"
    r.check("tag filter (common tag)", common_tag)

    def rare_tag():
        if len(tags) < 2:
            raise Skip("not enough tags")
        tag = tags[-1]
        d = r.search(f"something interesting tag:{tag}")
        assert all(tag in x["tags"] for x in d["results"])
        return f"tag:{tag} → {d['plan']['strategy']}"
    r.check("tag filter (less common tag)", rare_tag)

    def forced_agree():
        tag = ctx.get("common_tag")
        if not tag:
            raise Skip("no tag")
        ff = r.search(f"a person tag:{tag}", mode="filter_first")
        vf = r.search(f"a person tag:{tag}", mode="vector_first")
        a, b = {x["id"] for x in ff["results"]}, {x["id"] for x in vf["results"]}
        overlap = len(a & b) / max(len(a), 1)
        assert ff["plan"]["strategy"] == "filter_first"
        assert vf["plan"]["strategy"] in ("vector_first",) or vf["plan"].get("strategy_fallback")
        return ("PASS" if overlap >= 0.8 else "WARN", f"overlap {overlap:.0%} | FF {ff['plan']['timings_ms']['total']:.1f} ms vs VF {vf['plan']['timings_ms']['total']:.1f} ms")
    r.check("forced strategies agree (recall)", forced_agree)

    def date_filter():
        if not S["library"]["date_max"]:
            raise Skip("no dated photos")
        year = S["library"]["date_max"][:4]
        d = r.search(f"after:{year}")
        assert d["results"], "no results"
        assert all((x["taken_at"] or "") >= year for x in d["results"])
        return f"after:{year} → {len(d['results'])} results"
    r.check("date range filter (histogram)", date_filter)

    def geo_filter():
        if S["library"]["geotagged"] == 0:
            raise Skip("no geotagged photos (use --synthetic-geo)")
        seed = r.search("tag:synthetic-geo", k=1)["results"] or r.search("", k=50)["results"]
        seed = next((x for x in seed if x["gps_lat"] is not None), None)
        if not seed:
            raise Skip("could not find a geotagged photo")
        d = r.search(f"near:{seed['gps_lat']},{seed['gps_lon']},5", k=50)
        assert seed["id"] in {x["id"] for x in d["results"]}, "seed photo not within its own radius"
        return f"{len(d['results'])} photos within 5 km"
    r.check("geo radius filter (R*Tree + haversine)", geo_filter)

    def object_filter():
        if S["library"]["objects"] == 0:
            raise Skip("no bounding boxes")
        d = r.search("object:person", k=5)
        assert d["results"], "no person objects"
        det = r.detail(d["results"][0]["id"])
        assert any(o["label"] == "person" for o in det["objects"])
        return f"{len(d['results'])} results"
    r.check("object label filter", object_filter)

    def region_filter():
        if S["library"]["objects"] == 0:
            raise Skip("no bounding boxes")
        d = r.search("object:person region:0,0,0.5,1", k=5)
        if not d["results"]:
            return ("WARN", "no person fully inside the left half")
        det = r.detail(d["results"][0]["id"])
        ok = any(o["label"] == "person" and o["x_max"] <= 0.5 + 1e-3 for o in det["objects"])
        assert ok, "no person box inside the region"
        return f"{len(d['results'])} results"
    r.check("object region filter (R*Tree)", region_filter)

    def fts_filter():
        d = r.search("text:frisbee", k=5)
        if not d["results"]:
            return ("WARN", "no captions contain 'frisbee'")
        det = r.detail(d["results"][0]["id"])
        blob = (det["caption"] + " " + " ".join(t["name"] for t in det["tags"])).lower()
        assert "frisbee" in blob
        return f"{len(d['results'])} results"
    r.check("keyword filter (FTS5)", fts_filter)

    def lexical():
        d = r.search("frisbee", lexical_weight=0.5)
        assert d["plan"]["lexical_query"], "lexical channel not used"
        return f"lexical query {d['plan']['lexical_query']}"
    r.check("hybrid lexical fusion (BM25)", lexical)

    def detail_and_files():
        pid = ctx["any_id"]
        det = r.detail(pid)
        for url in (det["image_url"], det["thumb_url"]):
            resp = r.req("GET", url)
            assert resp.status_code == 200 and resp.headers["content-type"].startswith("image/"), url
        ctx["image_bytes"] = r.req("GET", det["image_url"]).content
        return f"photo #{pid}: {len(det['tags'])} tags, {len(det['objects'])} objects"
    r.check("photo detail + image + thumbnail", detail_and_files)

    def similar():
        pid = ctx["any_id"]
        d = r.req("POST", "/api/similar", json={"photo_id": pid, "k": 6}).json()
        assert len(d["results"]) == 6 and all(x["id"] != pid for x in d["results"])
        return f"top neighbour #{d['results'][0]['id']} ({d['results'][0]['score']:.3f})"
    r.check("image-to-image (stored photo)", similar)

    def similar_upload():
        pid = ctx["any_id"]
        files = {"file": ("query.jpg", ctx["image_bytes"], "image/jpeg")}
        d = r.req("POST", "/api/similar/upload", files=files, data={"k": "5"}).json()
        top = d["results"][0]
        assert top["id"] == pid and top["cosine"] > 0.99, f"top was #{top['id']} cos {top['cosine']}"
        return f"identical image found first (cos {top['cosine']:.4f})"
    r.check("query by uploaded image", similar_upload)

    def validation():
        assert r.req("POST", "/api/search", json={"q": "", "filters": {"date_from": "2013-13"}}).status_code == 422
        assert r.req("POST", "/api/search", json={"q": "", "filters": {"region": [0, 0, 2, 2]}}).status_code == 422
        assert r.req("POST", "/api/similar", json={"photo_id": 999999999}).status_code == 404
        assert r.req("GET", "/api/photos/999999999").status_code == 404
        d = r.search("dog near:abc")
        assert d["plan"]["warnings"], "bad inline token not reported"
        return "422 / 404 / warnings behave correctly"
    r.check("input validation + error handling", validation)

    def write_cycle():
        if args.skip_write or S["server"]["read_only"]:
            raise Skip("read-only")
        img = Image.frombytes("RGB", (96, 72), os.urandom(96 * 72 * 3))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        up = r.req("POST", "/api/upload", files=[("files", ("smoke.png", buf.getvalue(), "image/png"))],
                   data={"tags": "smoke-test", "caption": "smoke test image"}).json()
        res = up["results"][0]
        assert res["status"] == "ingested", res
        pid = res["photo_id"]
        found = r.search("tag:smoke-test", k=5)
        assert pid in {x["id"] for x in found["results"]}, "uploaded photo not searchable"
        dup = r.req("POST", "/api/upload", files=[("files", ("smoke.png", buf.getvalue(), "image/png"))]).json()
        assert dup["results"][0]["status"] == "duplicate"
        assert r.req("DELETE", f"/api/photos/{pid}").status_code == 200
        gone = r.search("tag:smoke-test", k=5)
        assert pid not in {x["id"] for x in gone["results"]}, "deleted photo still returned"
        return f"photo #{pid} uploaded, found, de-duplicated, deleted"
    r.check("upload → search → dedupe → delete", write_cycle)

    def calibrate():
        c = r.req("POST", "/api/admin/calibrate").json()
        assert c["calibrated"] is True
        return f"dot={c['dot_ms_per_dim']:.2e} ms, hnsw_ef={c['hnsw_ef_ms']:.2e} ms"
    r.check("cost-model calibration", calibrate)

    failed = sum(s in ("FAIL", "ERROR") for s in r.results)
    print(f"\n{r.results.count('PASS')} passed, {r.results.count('WARN')} warnings, "
          f"{r.results.count('SKIP')} skipped, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()