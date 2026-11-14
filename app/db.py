"""SQLite layer: WAL connections, versioned migrations (FTS5 + R*Tree), planner statistics."""
from __future__ import annotations

import json
import math
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import numpy as np

from .config import settings

# --------------------------------------------------------------------------------------
# Migrations: (version, name, sql). Applied in order, each inside its own transaction.
# --------------------------------------------------------------------------------------
MIGRATIONS: list[tuple[int, str, str]] = [
    (1, "core_schema", """
CREATE TABLE photos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,   -- AUTOINCREMENT: ids never reused (HNSW ids)
    file_hash     TEXT NOT NULL UNIQUE,                 -- sha256 of original bytes (dedupe)
    file_name     TEXT NOT NULL,
    file_path     TEXT NOT NULL,                        -- relative to data dir
    thumb_path    TEXT NOT NULL,
    width         INTEGER,
    height        INTEGER,
    format        TEXT,
    file_size     INTEGER,
    taken_at      TEXT,                                 -- ISO-8601
    taken_ts      INTEGER,                              -- epoch seconds, for range scans
    camera_make   TEXT,
    camera_model  TEXT,
    lens_model    TEXT,
    focal_length  REAL,
    f_number      REAL,
    exposure_time REAL,
    iso           INTEGER,
    gps_lat       REAL,
    gps_lon       REAL,
    caption       TEXT DEFAULT '',
    source        TEXT DEFAULT 'upload',
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX idx_photos_taken_ts ON photos(taken_ts);
CREATE INDEX idx_photos_camera   ON photos(camera_make, camera_model);
CREATE INDEX idx_photos_source   ON photos(source);

CREATE TABLE tags (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE photo_tags (
    photo_id   INTEGER NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    tag_id     INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
    confidence REAL    NOT NULL DEFAULT 1.0,
    origin     TEXT    NOT NULL DEFAULT 'manual',     -- manual | annotation | clip
    PRIMARY KEY (photo_id, tag_id)
) WITHOUT ROWID;
CREATE INDEX idx_photo_tags_tag ON photo_tags(tag_id, photo_id);

CREATE TABLE photo_objects (
    id       INTEGER PRIMARY KEY,
    photo_id INTEGER NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    label    TEXT    NOT NULL COLLATE NOCASE,
    score    REAL    NOT NULL DEFAULT 1.0,
    x_min REAL, y_min REAL, x_max REAL, y_max REAL     -- normalised [0,1] image coords
);
CREATE INDEX idx_objects_photo ON photo_objects(photo_id);
CREATE INDEX idx_objects_label ON photo_objects(label, photo_id);

CREATE TABLE photo_embeddings (
    photo_id INTEGER PRIMARY KEY REFERENCES photos(id) ON DELETE CASCADE,
    model    TEXT    NOT NULL,
    dim      INTEGER NOT NULL,
    vector   BLOB    NOT NULL                           -- float32 little-endian, L2-normalised
);
"""),
    (2, "fts5_index", """
CREATE VIRTUAL TABLE photos_fts USING fts5(
    file_name, caption, tags, camera,
    tokenize = 'porter unicode61 remove_diacritics 2'
);
"""),
    (3, "rtree_indexes", """
CREATE VIRTUAL TABLE object_rtree USING rtree(id, min_x, max_x, min_y, max_y);
CREATE VIRTUAL TABLE geo_rtree    USING rtree(id, min_lat, max_lat, min_lon, max_lon);
"""),
    (4, "planner_stats", """
CREATE TABLE planner_stats (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""),
]


def haversine_km(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(
        str(path or settings.db_path), timeout=30.0,
        isolation_level=None,          # explicit BEGIN/COMMIT only
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    for pragma in (
        "PRAGMA journal_mode=WAL",
        "PRAGMA synchronous=NORMAL",
        "PRAGMA foreign_keys=ON",
        "PRAGMA temp_store=MEMORY",
        "PRAGMA mmap_size=268435456",
        "PRAGMA busy_timeout=30000",
    ):
        conn.execute(pragma)
    conn.create_function("haversine_km", 4, haversine_km, deterministic=True)
    return conn


@contextmanager
def get_conn(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def check_capabilities() -> dict:
    caps: dict = {"sqlite_version": sqlite3.sqlite_version}
    c = sqlite3.connect(":memory:")
    probes = {
        "fts5": "CREATE VIRTUAL TABLE t_fts USING fts5(x)",
        "rtree": "CREATE VIRTUAL TABLE t_rt USING rtree(id, a, b)",
        "json1": "SELECT value FROM json_each('[1]')",
    }
    for name, sql in probes.items():
        try:
            c.execute(sql).fetchall()
            caps[name] = True
        except sqlite3.OperationalError:
            caps[name] = False
    c.close()
    return caps


def init_db(path: Path | str | None = None) -> list[int]:
    """Create the database if needed and apply pending migrations. Returns applied versions."""
    settings.ensure_dirs()
    caps = check_capabilities()
    missing = [k for k in ("fts5", "rtree", "json1") if not caps.get(k)]
    if missing:
        raise RuntimeError(
            f"Your Python's SQLite ({caps['sqlite_version']}) lacks {missing}. "
            "Use the official python.org build (3.10+), which ships them enabled."
        )
    conn = connect(path)
    applied: list[int] = []
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
        done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        for version, name, sql in MIGRATIONS:
            if version in done:
                continue
            script = (
                f"BEGIN;\n{sql}\n"
                f"INSERT INTO schema_migrations(version, name, applied_at) "
                f"VALUES ({version}, '{name}', strftime('%Y-%m-%dT%H:%M:%SZ','now'));\nCOMMIT;"
            )
            try:
                conn.executescript(script)
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            applied.append(version)
    finally:
        conn.close()
    return applied


# --------------------------------------------------------------------------------------
# Helpers used by ingestion / deletion
# --------------------------------------------------------------------------------------
def upsert_tag(conn: sqlite3.Connection, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (name,))
    return int(conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()[0])


def refresh_fts(conn: sqlite3.Connection, photo_id: int) -> None:
    row = conn.execute(
        "SELECT file_name, caption, camera_make, camera_model FROM photos WHERE id = ?", (photo_id,)
    ).fetchone()
    conn.execute("DELETE FROM photos_fts WHERE rowid = ?", (photo_id,))
    if row is None:
        return
    tags = " ".join(
        r[0] for r in conn.execute(
            "SELECT t.name FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id WHERE pt.photo_id = ?",
            (photo_id,),
        )
    )
    camera = " ".join(x for x in (row["camera_make"], row["camera_model"]) if x)
    conn.execute(
        "INSERT INTO photos_fts(rowid, file_name, caption, tags, camera) VALUES (?, ?, ?, ?, ?)",
        (photo_id, row["file_name"], row["caption"] or "", tags, camera),
    )


def delete_photo(conn: sqlite3.Connection, photo_id: int) -> dict | None:
    row = conn.execute("SELECT file_path, thumb_path FROM photos WHERE id = ?", (photo_id,)).fetchone()
    if row is None:
        return None
    conn.execute("DELETE FROM object_rtree WHERE id IN (SELECT id FROM photo_objects WHERE photo_id = ?)", (photo_id,))
    conn.execute("DELETE FROM geo_rtree WHERE id = ?", (photo_id,))
    conn.execute("DELETE FROM photos_fts WHERE rowid = ?", (photo_id,))
    conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))   # cascades tags/objects/embedding
    return dict(row)


# --------------------------------------------------------------------------------------
# Planner statistics (histograms used for selectivity estimation)
# --------------------------------------------------------------------------------------
def refresh_planner_stats(conn: sqlite3.Connection) -> dict:
    n = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
    ts = [r[0] for r in conn.execute("SELECT taken_ts FROM photos WHERE taken_ts IS NOT NULL ORDER BY taken_ts")]
    quantiles = np.quantile(np.asarray(ts, dtype=np.float64), np.linspace(0, 1, 65)).tolist() if ts else []
    cameras = {
        r[0]: r[1] for r in conn.execute(
            "SELECT trim(coalesce(camera_make,'') || ' ' || coalesce(camera_model,'')) AS cam, COUNT(*) "
            "FROM photos WHERE camera_make IS NOT NULL OR camera_model IS NOT NULL GROUP BY cam"
        )
    }
    sources = {r[0]: r[1] for r in conn.execute("SELECT source, COUNT(*) FROM photos GROUP BY source")}
    object_labels = {
        r[0].lower(): r[1] for r in conn.execute(
            "SELECT label, COUNT(DISTINCT photo_id) FROM photo_objects GROUP BY label"
        )
    }
    stats = {
        "n": n,
        "dated": len(ts),
        "date_quantiles": quantiles,
        "cameras": cameras,
        "sources": sources,
        "object_labels": object_labels,
        "total_objects": conn.execute("SELECT COUNT(*) FROM photo_objects").fetchone()[0],
        "photos_with_objects": conn.execute("SELECT COUNT(DISTINCT photo_id) FROM photo_objects").fetchone()[0],
        "geotagged": conn.execute("SELECT COUNT(*) FROM geo_rtree").fetchone()[0],
        "updated_at": time.time(),
    }
    conn.execute(
        "INSERT INTO planner_stats(key, value, updated_at) VALUES ('global', ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (json.dumps(stats), stats["updated_at"]),
    )
    return stats


def load_planner_stats(conn: sqlite3.Connection) -> dict:
    row = conn.execute("SELECT value FROM planner_stats WHERE key = 'global'").fetchone()
    return json.loads(row[0]) if row else refresh_planner_stats(conn)