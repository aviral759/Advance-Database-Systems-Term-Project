"""Ingestion: decode → EXIF → OpenCLIP embed → zero-shot tags → SQLite (+FTS5, R*Tree) → FAISS."""
from __future__ import annotations

import hashlib
import io
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from . import db
from .exif_utils import extract_exif, parse_datetime

log = logging.getLogger(__name__)
Image.MAX_IMAGE_PIXELS = 120_000_000
BROWSER_SAFE = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}

INSERT_PHOTO = """
INSERT INTO photos (file_hash, file_name, file_path, thumb_path, width, height, format, file_size,
                    taken_at, taken_ts, camera_make, camera_model, lens_model, focal_length, f_number,
                    exposure_time, iso, gps_lat, gps_lon, caption, source)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""


@dataclass
class IngestItem:
    data: bytes
    file_name: str
    caption: str = ""
    tags: list[str] = field(default_factory=list)
    objects: list[dict] = field(default_factory=list)   # {"label", "bbox": [x1,y1,x2,y2] normalised, "score"}
    taken_at: str | None = None                         # used when EXIF has no date
    gps: tuple[float, float] | None = None              # used when EXIF has no GPS
    source: str = "upload"


@dataclass
class _Prepared:
    item: IngestItem
    digest: str
    fmt: str
    exif: dict
    image: Image.Image


def _norm_tag(name: str) -> str:
    return " ".join(str(name).lower().split())[:64]


def _res(item: IngestItem, status: str, **kw) -> dict:
    return {"file_name": item.file_name, "status": status, **kw}


class Ingestor:
    def __init__(self, settings, embedder, tagger, vindex):
        self.settings, self.embedder, self.tagger, self.vindex = settings, embedder, tagger, vindex
        self._lock = threading.Lock()

    def ingest(self, items: list[IngestItem], *, autotag: bool = True,
               save_index: bool = True, refresh_stats: bool = True) -> list[dict]:
        results: list[dict] = []
        prepared: list[_Prepared] = []
        seen: set[str] = set()
        with db.get_conn() as conn:
            for item in items:
                digest = hashlib.sha256(item.data).hexdigest()
                if digest in seen:
                    results.append(_res(item, "duplicate", detail="repeated in this batch"))
                    continue
                seen.add(digest)
                row = conn.execute("SELECT id FROM photos WHERE file_hash = ?", (digest,)).fetchone()
                if row:
                    results.append(_res(item, "duplicate", photo_id=row[0]))
                    continue
                try:
                    img = Image.open(io.BytesIO(item.data))
                    img.load()
                    fmt = (img.format or "JPEG").upper()
                    exif = extract_exif(img)
                    upright = ImageOps.exif_transpose(img).convert("RGB")
                except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
                    results.append(_res(item, "error", detail=f"cannot decode image: {exc}"))
                    continue
                prepared.append(_Prepared(item, digest, fmt, exif, upright))
        if not prepared:
            return results

        vecs = self.embedder.encode_images([p.image for p in prepared])
        auto = self.tagger.tag(vecs) if autotag else [[] for _ in prepared]

        kept_ids, kept_vecs = [], []
        with self._lock, db.get_conn() as conn:
            with db.transaction(conn):
                for p, vec, auto_tags in zip(prepared, vecs, auto):
                    row = conn.execute("SELECT id FROM photos WHERE file_hash = ?", (p.digest,)).fetchone()
                    if row:  # raced with a concurrent upload
                        results.append(_res(p.item, "duplicate", photo_id=row[0]))
                        continue
                    pid, tags = self._write_one(conn, p, vec, auto_tags)
                    kept_ids.append(pid)
                    kept_vecs.append(vec)
                    results.append(_res(p.item, "ingested", photo_id=pid, tags=tags))
            if kept_ids:
                self.vindex.add(kept_ids, np.vstack(kept_vecs))
                if save_index:
                    self.vindex.save()
            if refresh_stats:
                db.refresh_planner_stats(conn)
        return results

    # ------------------------------------------------------------------ internals
    def _write_files(self, p: _Prepared) -> tuple[Path, Path]:
        s = self.settings
        ext = BROWSER_SAFE.get(p.fmt, ".jpg")
        rel_img = Path("images") / p.digest[:2] / f"{p.digest}{ext}"
        rel_thumb = Path("thumbs") / p.digest[:2] / f"{p.digest}.jpg"
        abs_img, abs_thumb = s.data_dir / rel_img, s.data_dir / rel_thumb
        abs_img.parent.mkdir(parents=True, exist_ok=True)
        abs_thumb.parent.mkdir(parents=True, exist_ok=True)
        if not abs_img.exists():
            if p.fmt in BROWSER_SAFE:
                abs_img.write_bytes(p.item.data)
            else:  # TIFF/BMP/etc. → store a browser-displayable JPEG
                p.image.save(abs_img, "JPEG", quality=92)
        if not abs_thumb.exists():
            thumb = p.image.copy()
            thumb.thumbnail((s.thumb_size, s.thumb_size), Image.Resampling.LANCZOS)
            thumb.save(abs_thumb, "JPEG", quality=85, optimize=True)
        return rel_img, rel_thumb

    def _tag(self, conn, pid: int, name: str, conf: float, origin: str, acc: set[str]) -> None:
        name = _norm_tag(name)
        if not name:
            return
        tid = db.upsert_tag(conn, name)
        conn.execute(
            "INSERT INTO photo_tags (photo_id, tag_id, confidence, origin) VALUES (?,?,?,?) "
            "ON CONFLICT(photo_id, tag_id) DO UPDATE SET confidence = MAX(confidence, excluded.confidence)",
            (pid, tid, round(conf, 4), origin),
        )
        acc.add(name)

    def _write_one(self, conn, p: _Prepared, vec: np.ndarray, auto_tags) -> tuple[int, list[str]]:
        item, ex = p.item, p.exif
        rel_img, rel_thumb = self._write_files(p)
        taken_at, taken_ts = ex.get("taken_at"), ex.get("taken_ts")
        if taken_at is None and item.taken_at:
            taken_at, taken_ts = parse_datetime(item.taken_at)
        lat, lon = ex.get("gps_lat"), ex.get("gps_lon")
        if (lat is None or lon is None) and item.gps:
            lat, lon = item.gps
        cur = conn.execute(INSERT_PHOTO, (
            p.digest, item.file_name, rel_img.as_posix(), rel_thumb.as_posix(), p.image.width, p.image.height,
            p.fmt, len(item.data), taken_at, taken_ts, ex.get("camera_make"), ex.get("camera_model"),
            ex.get("lens_model"), ex.get("focal_length"), ex.get("f_number"), ex.get("exposure_time"),
            ex.get("iso"), lat, lon, item.caption or "", item.source,
        ))
        pid = int(cur.lastrowid)
        tags: set[str] = set()
        for name in item.tags:
            self._tag(conn, pid, name, 1.0, "manual", tags)
        for obj in item.objects:
            try:
                x1, y1, x2, y2 = (min(1.0, max(0.0, float(v))) for v in obj["bbox"])
            except (KeyError, TypeError, ValueError):
                continue
            if x2 <= x1 or y2 <= y1:
                continue
            label = _norm_tag(obj.get("label", ""))
            if not label:
                continue
            oc = conn.execute(
                "INSERT INTO photo_objects (photo_id, label, score, x_min, y_min, x_max, y_max) VALUES (?,?,?,?,?,?,?)",
                (pid, label, float(obj.get("score", 1.0)), x1, y1, x2, y2),
            )
            conn.execute("INSERT INTO object_rtree (id, min_x, max_x, min_y, max_y) VALUES (?,?,?,?,?)",
                         (oc.lastrowid, x1, x2, y1, y2))
            self._tag(conn, pid, label, 1.0, "annotation", tags)
        for name, prob in auto_tags:
            self._tag(conn, pid, name, prob, "clip", tags)
        if lat is not None and lon is not None:
            conn.execute("INSERT INTO geo_rtree (id, min_lat, max_lat, min_lon, max_lon) VALUES (?,?,?,?,?)",
                         (pid, lat, lat, lon, lon))
        conn.execute("INSERT INTO photo_embeddings (photo_id, model, dim, vector) VALUES (?,?,?,?)",
                     (pid, self.embedder.model_id, int(vec.shape[0]), np.asarray(vec, np.float32).tobytes()))
        db.refresh_fts(conn, pid)
        return pid, sorted(tags)