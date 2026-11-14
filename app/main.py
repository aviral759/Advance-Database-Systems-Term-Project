"""FastAPI server: REST API + static dashboard."""
from __future__ import annotations

import io
import json
import logging
import os
import secrets
import shutil
import statistics
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from . import db
from .config import ROOT, settings
from .context import AppContext, build_context
from .ingest import IngestItem
from .planner import Filters, normalize_region, parse_date, parse_query

log = logging.getLogger("hps")
FRONTEND_DIR = ROOT / "frontend"
Mode = Literal["auto", "filter_first", "vector_first"]

STARTED_AT = time.time()
SEARCH_LOG: deque = deque(maxlen=240)            # recent query latencies (live telemetry)
_SIZE_CACHE: dict = {"at": 0.0, "value": None}   # cached on-disk sizes (refreshed every 20 s)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app.state.ctx = build_context()
    log.info("Ready: %d vectors indexed on %s", len(app.state.ctx.vindex), app.state.ctx.embedder.device)
    yield
    app.state.ctx.vindex.save()


app = FastAPI(title="Hybrid Photo Library Search Engine", version="1.1.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)


# ---------------------------------------------------------------- demo-token gate (tunnel mode)
OPEN_PATHS = {"/api/health"}
LOCKED_HTML = """<!doctype html><html><body style="background:#F7F8FA;color:#252A35;font-family:Segoe UI,Arial,sans-serif;
padding:48px"><h2 style="color:#5267D9">Access token required</h2><p>Open this page with <code>?token=&lt;demo token&gt;</code>
appended to the URL.</p></body></html>"""


@app.middleware("http")
async def demo_token_gate(request: Request, call_next):
    token = settings.demo_token
    if not token or request.url.path in OPEN_PATHS:
        return await call_next(request)
    supplied = (request.headers.get("x-demo-token") or request.query_params.get("token")
                or request.cookies.get("hps_token") or "")
    if not secrets.compare_digest(supplied.encode(), token.encode()):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "Demo token required"}, status_code=401)
        return HTMLResponse(LOCKED_HTML, status_code=401)
    response = await call_next(request)
    if request.query_params.get("token"):
        secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        response.set_cookie("hps_token", token, httponly=True, samesite="lax", secure=secure, max_age=86400)
    return response


# ---------------------------------------------------------------- schemas
class SearchFilters(BaseModel):
    tags: list[str] = Field(default_factory=list)
    camera: str | None = None
    date_from: str | None = Field(None, description="YYYY, YYYY-MM or YYYY-MM-DD")
    date_to: str | None = None
    near_lat: float | None = Field(None, ge=-90, le=90)
    near_lon: float | None = Field(None, ge=-180, le=180)
    near_km: float = Field(25.0, gt=0, le=20000)
    objects: list[str] = Field(default_factory=list)
    region: list[float] | None = Field(None, min_length=4, max_length=4, description="x1,y1,x2,y2 in [0,1]")
    text: str | None = Field(None, description="Hard FTS5 keyword filter")
    source: str | None = None


class SearchRequest(BaseModel):
    q: str = Field("", max_length=1000, description="Natural language + inline filters (tag:, after:, near:, …)")
    filters: SearchFilters = Field(default_factory=SearchFilters)
    k: int = Field(24, ge=1, le=200)
    mode: Mode = "auto"
    lexical_weight: float = Field(0.05, ge=0.0, le=1.0)


class SimilarRequest(BaseModel):
    photo_id: int
    q: str = Field("", description="Optional filter tokens, e.g. 'tag:dog after:2013'")
    filters: SearchFilters = Field(default_factory=SearchFilters)
    k: int = Field(24, ge=1, le=200)
    mode: Mode = "auto"


# ---------------------------------------------------------------- helpers
def _ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def _merge_filters(sf: SearchFilters, f: Filters) -> Filters:
    f.tags.extend(t.strip().lower() for t in sf.tags if t.strip())
    f.objects.extend(o.strip().lower() for o in sf.objects if o.strip())
    if sf.camera:
        f.camera = sf.camera
    if sf.date_from:
        f.date_from = parse_date(sf.date_from)
    if sf.date_to:
        f.date_to = parse_date(sf.date_to, end=True)
    if sf.near_lat is not None and sf.near_lon is not None:
        f.near = (sf.near_lat, sf.near_lon, sf.near_km)
    if sf.region:
        f.region = normalize_region(sf.region)
    if sf.text:
        f.text = sf.text
    if sf.source:
        f.source = sf.source
    return f


def _resolve(q: str, sf: SearchFilters) -> tuple[str, Filters, list[str]]:
    text, inline, warnings = parse_query(q)
    try:
        return text, _merge_filters(sf, inline), warnings
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _filters_dict(f: Filters) -> dict:
    d = asdict(f)
    for key in ("date_from", "date_to"):
        if d[key] is not None:
            d[key] = datetime.fromtimestamp(d[key], tz=timezone.utc).strftime("%Y-%m-%d")
    return d


def _decorate(rows: list[dict]) -> list[dict]:
    for r in rows:
        r["thumb_url"] = f"/api/photos/{r['id']}/thumb"
        r["image_url"] = f"/api/photos/{r['id']}/image"
    return rows


def _add_encode(plan: dict, ms: float) -> None:
    plan["timings_ms"]["encode"] = round(ms, 3)
    plan["timings_ms"]["total"] = round(plan["timings_ms"]["total"] + ms, 3)


def _log_search(plan: dict, kind: str) -> None:
    SEARCH_LOG.append({"t": round(time.time(), 3), "ms": plan["timings_ms"].get("total", 0.0),
                       "strategy": plan.get("strategy"), "kind": kind})


def _read_upload(f: UploadFile) -> bytes:
    limit = settings.max_upload_mb * 1024 * 1024
    data = f.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"{f.filename}: exceeds {settings.max_upload_mb} MB")
    return data


def _require_writable() -> None:
    if settings.read_only:
        raise HTTPException(status_code=403, detail="Server is in read-only demo mode")


def _dir_stats(path: Path) -> tuple[int, int]:
    total = count = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
                count += 1
            except OSError:
                pass
    return total, count


def _storage_sizes() -> dict:
    now = time.time()
    if _SIZE_CACHE["value"] is not None and now - _SIZE_CACHE["at"] < 20:
        return _SIZE_CACHE["value"]
    img_b, img_n = _dir_stats(settings.images_dir)
    th_b, th_n = _dir_stats(settings.thumbs_dir)
    du = shutil.disk_usage(settings.data_dir)
    value = {"images_bytes": img_b, "image_files": img_n, "thumbs_bytes": th_b, "thumb_files": th_n,
             "disk_total": du.total, "disk_used": du.used, "disk_free": du.free}
    _SIZE_CACHE.update(at=now, value=value)
    return value


def _invalidate_sizes() -> None:
    _SIZE_CACHE["at"] = 0.0


def _run_similar(c: AppContext, vec, q: str, sf: SearchFilters, k: int, mode: str, exclude) -> dict:
    text, filters, warnings = _resolve(q, sf)
    if text:
        warnings.append(f"Free text '{text}' is ignored in image-to-image search; only filter tokens apply.")
    with db.get_conn() as conn:
        results, plan = c.planner.search(conn, qvec=vec, filters=filters, k=k, mode=mode,
                                         exclude_ids=exclude, warnings=warnings)
    plan["timings_ms"].setdefault("encode", 0.0)
    return {"query": {"raw": q, "semantic_text": "", "filters": _filters_dict(filters)},
            "results": _decorate(results), "plan": plan}


LIST_SQL = """
SELECT p.id, p.file_name, p.width, p.height, p.taken_at, p.camera_make, p.camera_model,
       p.caption, p.source, p.gps_lat, p.gps_lon, p.created_at,
       (SELECT group_concat(t.name, '|') FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id
         WHERE pt.photo_id = p.id) AS tags
FROM photos p
"""
LIST_SORTS = {
    "taken": "p.taken_ts IS NULL, p.taken_ts DESC, p.id DESC",
    "ingested": "p.id DESC",
    "name": "p.file_name COLLATE NOCASE ASC, p.id ASC",
}


# ---------------------------------------------------------------- endpoints
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/search")
def search(req: SearchRequest, request: Request):
    """Hybrid search: OpenCLIP text embedding + structured filters + FTS5 lexical fusion."""
    c = _ctx(request)
    text, filters, warnings = _resolve(req.q, req.filters)
    t0 = time.perf_counter()
    qvec = c.embedder.encode_texts([text])[0] if text else None
    encode_ms = (time.perf_counter() - t0) * 1000
    with db.get_conn() as conn:
        results, plan = c.planner.search(conn, qvec=qvec, filters=filters, k=req.k, mode=req.mode,
                                         lexical_text=text, lexical_weight=req.lexical_weight, warnings=warnings)
    _add_encode(plan, encode_ms)
    _log_search(plan, "text" if text else "browse")
    return {"query": {"raw": req.q, "semantic_text": text, "filters": _filters_dict(filters)},
            "results": _decorate(results), "plan": plan}


@app.get("/api/search")
def search_get(request: Request, q: str = "", k: int = Query(24, ge=1, le=200), mode: Mode = "auto",
               lexical_weight: float = Query(0.05, ge=0, le=1)):
    return search(SearchRequest(q=q, k=k, mode=mode, lexical_weight=lexical_weight), request)


@app.post("/api/similar")
def similar(req: SimilarRequest, request: Request):
    """Image-to-image search using a stored photo's embedding as the query."""
    c = _ctx(request)
    vec = c.vindex.get_vector(req.photo_id)
    if vec is None:
        raise HTTPException(status_code=404, detail=f"No embedding for photo {req.photo_id}")
    out = _run_similar(c, vec, req.q, req.filters, req.k, req.mode, exclude=[req.photo_id])
    out["query"]["photo_id"] = req.photo_id
    _log_search(out["plan"], "similar")
    return out


@app.get("/api/similar/{photo_id}")
def similar_get(photo_id: int, request: Request, k: int = Query(24, ge=1, le=200), mode: Mode = "auto", q: str = ""):
    return similar(SimilarRequest(photo_id=photo_id, k=k, mode=mode, q=q), request)


@app.post("/api/similar/upload")
def similar_upload(request: Request, file: UploadFile = File(...), k: int = Form(24),
                   mode: Mode = Form("auto"), q: str = Form("")):
    """Query by an uploaded image (the image is not added to the library)."""
    c = _ctx(request)
    data = _read_upload(file)
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=415, detail=f"Cannot decode image: {exc}") from exc
    t0 = time.perf_counter()
    vec = c.embedder.encode_images([img])[0]
    encode_ms = (time.perf_counter() - t0) * 1000
    out = _run_similar(c, vec, q, SearchFilters(), max(1, min(k, 200)), mode, exclude=())
    _add_encode(out["plan"], encode_ms)
    out["query"]["uploaded_file"] = file.filename
    _log_search(out["plan"], "image")
    return out


@app.post("/api/upload")
def upload(request: Request, files: list[UploadFile] = File(...), caption: str = Form(""),
           tags: str = Form(""), autotag: bool = Form(True)):
    """Ingest one or more images: EXIF, OpenCLIP embedding, zero-shot tags, FTS5, R*Tree, HNSW."""
    _require_writable()
    c = _ctx(request)
    manual = [t.strip().lower() for t in tags.split(",") if t.strip()]
    items, rejected = [], []
    for f in files:
        try:
            data = _read_upload(f)
        except HTTPException as exc:
            rejected.append({"file_name": f.filename, "status": "error", "detail": exc.detail})
            continue
        items.append(IngestItem(data=data, file_name=Path(f.filename or "upload").name,
                                caption=caption.strip(), tags=manual))
    results = c.ingestor.ingest(items, autotag=autotag) if items else []
    _invalidate_sizes()
    return {"results": rejected + results, "vectors": len(c.vindex)}


@app.get("/api/photos")
def list_photos(limit: int = Query(60, ge=1, le=200), offset: int = Query(0, ge=0),
                sort: Literal["taken", "ingested", "name"] = "taken",
                tag: str | None = None, source: str | None = None,
                geotagged: bool = False, ids: str | None = None):
    """Paginated library browsing (no vectors involved)."""
    where, params = [], []
    if tag:
        where.append("p.id IN (SELECT pt.photo_id FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id WHERE t.name = ?)")
        params.append(tag.strip().lower())
    if source:
        where.append("p.source = ?")
        params.append(source)
    if geotagged:
        where.append("p.gps_lat IS NOT NULL AND p.gps_lon IS NOT NULL")
    if ids is not None:
        id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()][:200]
        where.append("p.id IN (SELECT value FROM json_each(?))")
        params.append(json.dumps(id_list))
    clause = " AND ".join(where) or "1=1"
    with db.get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM photos p WHERE {clause}", params).fetchone()[0]
        rows = conn.execute(f"{LIST_SQL} WHERE {clause} ORDER BY {LIST_SORTS[sort]} LIMIT ? OFFSET ?",
                            [*params, limit, offset]).fetchall()
    items = []
    for r in rows:
        item = dict(r)
        item["tags"] = [t for t in (item.pop("tags") or "").split("|") if t]
        items.append(item)
    return {"total": total, "offset": offset, "limit": limit, "items": _decorate(items)}


@app.get("/api/collections")
def collections():
    """Collections derived from the data: top tags, sources and GPS place clusters."""
    with db.get_conn() as conn:
        tags = [{"name": r[0], "count": r[1], "cover": f"/api/photos/{r[2]}/thumb"} for r in conn.execute(
            "SELECT t.name, COUNT(*) AS c, MAX(pt.photo_id) FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id "
            "GROUP BY t.id ORDER BY c DESC LIMIT 16")]
        sources = [{"name": r[0], "count": r[1], "cover": f"/api/photos/{r[2]}/thumb"} for r in conn.execute(
            "SELECT source, COUNT(*) AS c, MAX(id) FROM photos GROUP BY source ORDER BY c DESC")]
        points = conn.execute("SELECT id, gps_lat, gps_lon FROM photos "
                              "WHERE gps_lat IS NOT NULL AND gps_lon IS NOT NULL ORDER BY id").fetchall()
    clusters: list[dict] = []
    for pid, lat, lon in points:              # greedy 60 km clustering
        for cl in clusters:
            if db.haversine_km(lat, lon, cl["lat0"], cl["lon0"]) <= 60:
                cl["n"] += 1
                cl["slat"] += lat
                cl["slon"] += lon
                cl["cover"] = pid
                break
        else:
            clusters.append({"lat0": lat, "lon0": lon, "slat": lat, "slon": lon, "n": 1, "cover": pid})
    clusters.sort(key=lambda c: c["n"], reverse=True)
    places = [{"lat": round(c["slat"] / c["n"], 4), "lon": round(c["slon"] / c["n"], 4), "count": c["n"],
               "cover": f"/api/photos/{c['cover']}/thumb"} for c in clusters[:24]]
    return {"tags": tags, "sources": sources, "places": places}


@app.get("/api/photos/{photo_id}")
def photo_detail(photo_id: int, request: Request):
    c = _ctx(request)
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Photo not found")
        tags = [dict(r) for r in conn.execute(
            "SELECT t.name, pt.confidence, pt.origin FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id "
            "WHERE pt.photo_id = ? ORDER BY pt.confidence DESC, t.name", (photo_id,))]
        objects = [dict(r) for r in conn.execute(
            "SELECT id, label, score, x_min, y_min, x_max, y_max FROM photo_objects WHERE photo_id = ? ORDER BY id",
            (photo_id,))]
    out = dict(row)
    out.update(tags=tags, objects=objects, has_embedding=c.vindex.get_vector(photo_id) is not None,
               thumb_url=f"/api/photos/{photo_id}/thumb", image_url=f"/api/photos/{photo_id}/image")
    return out


def _photo_file(photo_id: int, column: str) -> Path:
    with db.get_conn() as conn:
        row = conn.execute(f"SELECT {column} FROM photos WHERE id = ?", (photo_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    path = settings.data_dir / row[0]
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return path


@app.get("/api/photos/{photo_id}/image")
def photo_image(photo_id: int):
    return FileResponse(_photo_file(photo_id, "file_path"), headers={"Cache-Control": "private, max-age=86400"})


@app.get("/api/photos/{photo_id}/thumb")
def photo_thumb(photo_id: int):
    return FileResponse(_photo_file(photo_id, "thumb_path"), headers={"Cache-Control": "private, max-age=86400"})


@app.delete("/api/photos/{photo_id}")
def photo_delete(photo_id: int, request: Request):
    _require_writable()
    c = _ctx(request)
    with db.get_conn() as conn:
        with db.transaction(conn):
            paths = db.delete_photo(conn, photo_id)
        if paths is None:
            raise HTTPException(status_code=404, detail="Photo not found")
        db.refresh_planner_stats(conn)
    c.vindex.remove(photo_id)
    for rel in paths.values():
        (settings.data_dir / rel).unlink(missing_ok=True)
    _invalidate_sizes()
    return {"deleted": photo_id, "tombstones": c.vindex.stats()["tombstones"]}


@app.get("/api/stats")
def stats(request: Request):
    c = _ctx(request)
    with db.get_conn() as conn:
        def one(sql: str, params=()):
            return conn.execute(sql, params).fetchone()[0]

        library = {
            "photos": one("SELECT COUNT(*) FROM photos"),
            "tags": one("SELECT COUNT(*) FROM tags"),
            "tag_assignments": one("SELECT COUNT(*) FROM photo_tags"),
            "objects": one("SELECT COUNT(*) FROM photo_objects"),
            "embeddings": one("SELECT COUNT(*) FROM photo_embeddings"),
            "geotagged": one("SELECT COUNT(*) FROM geo_rtree"),
            "date_min": one("SELECT MIN(taken_at) FROM photos"),
            "date_max": one("SELECT MAX(taken_at) FROM photos"),
            "sources": {r[0]: r[1] for r in conn.execute("SELECT source, COUNT(*) FROM photos GROUP BY source")},
        }
        model_embeddings = one("SELECT COUNT(*) FROM photo_embeddings WHERE model = ?", (c.embedder.model_id,))
        top_tags = [{"name": r[0], "count": r[1]} for r in conn.execute(
            "SELECT t.name, COUNT(*) AS c FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id "
            "GROUP BY t.id ORDER BY c DESC LIMIT 15")]
        storage = {
            "db_bytes": one("PRAGMA page_count") * one("PRAGMA page_size"),
            "journal_mode": one("PRAGMA journal_mode"),
            "migrations": [dict(r) for r in conn.execute(
                "SELECT version, name, applied_at FROM schema_migrations ORDER BY version")],
        }
    wal = Path(str(settings.db_path) + "-wal")
    storage["wal_bytes"] = wal.stat().st_size if wal.exists() else 0
    storage["capabilities"] = db.check_capabilities()
    storage.update(_storage_sizes())

    vstats = c.vindex.stats()
    vstats["ram_bytes_estimate"] = int(vstats["ntotal"] * vstats["dim"] * 4 * 2       # RAM matrix + HNSW vectors
                                       + vstats["ntotal"] * 2 * vstats["M"] * 4)      # layer-0 graph links

    recent = list(SEARCH_LOG)
    lat = sorted(r["ms"] for r in recent)
    telemetry = {
        "uptime_s": round(time.time() - STARTED_AT),
        "searches": len(recent),
        "p50_ms": round(statistics.median(lat), 3) if lat else None,
        "p95_ms": round(lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))], 3) if lat else None,
        "recent": recent[-80:],
    }
    return {
        "library": library, "top_tags": top_tags, "storage": storage,
        "vector_index": vstats,
        "embedding": {"model_id": c.embedder.model_id, "dim": c.embedder.dim, "device": c.embedder.device},
        "planner": asdict(c.planner.cost),
        "telemetry": telemetry,
        "health": {"status": "ok", "index_consistent": vstats["active"] == model_embeddings,
                   "model_embeddings": model_embeddings},
        "server": {"read_only": settings.read_only, "token_protected": bool(settings.demo_token)},
    }


@app.post("/api/admin/rebuild-index")
def admin_rebuild(request: Request):
    _require_writable()
    return _ctx(request).vindex.compact()


@app.post("/api/admin/reload")
def admin_reload(request: Request):
    """Reload vectors and stats from SQLite (e.g. after running scripts/ingest_folder.py)."""
    c = _ctx(request)
    with db.get_conn() as conn:
        info = c.vindex.load_from_db(conn, c.embedder.model_id)
        db.refresh_planner_stats(conn)
    _invalidate_sizes()
    return info


@app.post("/api/admin/calibrate")
def admin_calibrate(request: Request):
    c = _ctx(request)
    with db.get_conn() as conn:
        return c.planner.calibrate(conn)


# Static dashboard (mounted last so /api routes take precedence)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")