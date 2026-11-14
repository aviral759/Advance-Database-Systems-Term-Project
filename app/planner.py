"""Cost-based hybrid query planner and executor.

Strategies
----------
metadata_only : no semantic vector, so pure SQL (FTS5 / B-tree / R*Tree), ordered by date.
vector_only   : no predicates, so HNSW top-k (plus lexical-channel hits).
filter_first  : SQL produces the candidate set, then exact BLAS cosine over the candidates.
vector_first  : HNSW over-fetches k' = ceil(k·α/s), then predicates are verified in SQLite;
                adaptive retries (k' ×4) with exact filter-first fallback.

The choice between filter_first and vector_first uses estimated selectivity s
(histograms, exact index counts, capped probes; independence assumption) and a
calibrated linear cost model.
"""
from __future__ import annotations

import calendar
import json
import math
import re
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime

import numpy as np

from .db import load_planner_stats
from .vector_index import VectorIndex

STOPWORDS = frozenset(
    "a an and are as at be by for from in into is it of on or photo photos picture image the to with".split()
)
_WORD = re.compile(r"\w+", re.UNICODE)
_TOKEN = re.compile(r'(?P<key>[A-Za-z_]+):(?P<val>"[^"]*"|\S+)')
PROBE_CAP = 5000
TS_MIN, TS_MAX = -(2**62), 2**62


# ====================================================================== query model
@dataclass
class Filters:
    tags: list[str] = field(default_factory=list)
    camera: str | None = None
    date_from: int | None = None
    date_to: int | None = None
    near: tuple[float, float, float] | None = None          # lat, lon, radius_km
    objects: list[str] = field(default_factory=list)
    region: tuple[float, float, float, float] | None = None  # x1, y1, x2, y2 (normalised)
    text: str | None = None                                  # hard FTS5 filter
    source: str | None = None


def parse_date(value: str, end: bool = False) -> int:
    v = value.strip()
    for fmt, unit in (("%Y-%m-%d", "day"), ("%Y-%m", "month"), ("%Y", "year")):
        try:
            dt = datetime.strptime(v, fmt)
        except ValueError:
            continue
        if end:
            if unit == "day":
                dt = dt.replace(hour=23, minute=59, second=59)
            elif unit == "month":
                dt = dt.replace(day=calendar.monthrange(dt.year, dt.month)[1], hour=23, minute=59, second=59)
            else:
                dt = dt.replace(month=12, day=31, hour=23, minute=59, second=59)
        return calendar.timegm(dt.timetuple())
    raise ValueError(f"unrecognised date '{value}' (use YYYY, YYYY-MM or YYYY-MM-DD)")


def normalize_region(vals) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = (float(v) for v in vals)
    if not all(0.0 <= v <= 1.0 for v in (x1, y1, x2, y2)):
        raise ValueError("region coordinates must be within [0, 1]")
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    if x2 - x1 <= 0 or y2 - y1 <= 0:
        raise ValueError("region must have non-zero area")
    return (x1, y1, x2, y2)


def parse_query(raw: str) -> tuple[str, Filters, list[str]]:
    """Split 'dog on beach tag:dog after:2013' into semantic text + structured filters."""
    f, warnings = Filters(), []

    def repl(m: re.Match) -> str:
        key, val = m.group("key").lower(), m.group("val").strip('"')
        try:
            if key == "tag":
                f.tags.append(val.lower())
            elif key == "camera":
                f.camera = val
            elif key in ("after", "from"):
                f.date_from = parse_date(val)
            elif key in ("before", "to"):
                f.date_to = parse_date(val, end=True)
            elif key == "near":
                parts = [float(x) for x in val.split(",")]
                lat, lon = parts[0], parts[1]
                km = parts[2] if len(parts) > 2 else 25.0
                if not (-90 <= lat <= 90 and -180 <= lon <= 180 and km > 0):
                    raise ValueError("near expects lat,lon[,km]")
                f.near = (lat, lon, km)
            elif key == "object":
                f.objects.append(val.lower())
            elif key == "region":
                f.region = normalize_region(val.split(","))
            elif key == "text":
                f.text = val
            elif key == "source":
                f.source = val
            else:
                return m.group(0)          # not a filter: keep as semantic text
        except (ValueError, IndexError) as exc:
            warnings.append(f"Ignored '{m.group(0)}': {exc}")
        return " "

    text = _TOKEN.sub(repl, raw or "")
    return " ".join(text.split()), f, warnings


def fts_query(text: str, op: str = "AND", drop_stop: bool = False) -> str:
    toks = [t for t in _WORD.findall((text or "").lower()) if len(t) > 1]
    if drop_stop:
        toks = [t for t in toks if t not in STOPWORDS]
    toks = list(dict.fromkeys(toks))[:16]
    return f" {op} ".join(f'"{t}"' for t in toks)


# ====================================================================== predicates
@dataclass
class Predicate:
    kind: str
    sql: str
    params: list
    label: str
    meta: dict = field(default_factory=dict)


def geo_box(lat: float, lon: float, km: float) -> list[float]:
    dlat = km / 111.32
    dlon = min(180.0, km / (111.32 * max(math.cos(math.radians(lat)), 1e-6)))
    return [lat - dlat, lat + dlat, lon - dlon, lon + dlon]


def build_predicates(f: Filters) -> tuple[list[Predicate], list[str]]:
    preds, warnings = [], []
    for t in f.tags:
        preds.append(Predicate(
            "tag",
            "p.id IN (SELECT pt.photo_id FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id WHERE t.name = ?)",
            [t], f"tag = '{t}'", {"tag": t}))
    if f.camera:
        like = f"%{f.camera}%"
        preds.append(Predicate("camera", "(p.camera_make LIKE ? OR p.camera_model LIKE ?)",
                               [like, like], f"camera ~ '{f.camera}'", {"camera": f.camera}))
    if f.date_from is not None or f.date_to is not None:
        lo = f.date_from if f.date_from is not None else TS_MIN
        hi = f.date_to if f.date_to is not None else TS_MAX
        preds.append(Predicate("date", "p.taken_ts BETWEEN ? AND ?", [lo, hi],
                               "taken_ts in range", {"lo": lo, "hi": hi}))
    if f.near:
        lat, lon, km = f.near
        box = geo_box(lat, lon, km)
        preds.append(Predicate(
            "near",
            "p.id IN (SELECT id FROM geo_rtree WHERE min_lat >= ? AND max_lat <= ? AND min_lon >= ? AND max_lon <= ?)"
            " AND haversine_km(p.gps_lat, p.gps_lon, ?, ?) <= ?",
            [*box, lat, lon, km], f"within {km:g} km of ({lat:.4f}, {lon:.4f})", {"box": box}))
    region_params = None
    if f.region:
        x1, y1, x2, y2 = f.region
        region_params = [x1, x2, y1, y2]
    for label in f.objects:
        if region_params:
            preds.append(Predicate(
                "object",
                "p.id IN (SELECT o.photo_id FROM photo_objects o JOIN object_rtree r ON r.id = o.id "
                "WHERE o.label = ? AND r.min_x >= ? AND r.max_x <= ? AND r.min_y >= ? AND r.max_y <= ?)",
                [label, *region_params], f"object '{label}' inside region",
                {"label": label, "region_params": region_params}))
        else:
            preds.append(Predicate("object", "p.id IN (SELECT o.photo_id FROM photo_objects o WHERE o.label = ?)",
                                   [label], f"object '{label}'", {"label": label}))
    if region_params and not f.objects:
        preds.append(Predicate(
            "region",
            "p.id IN (SELECT o.photo_id FROM object_rtree r JOIN photo_objects o ON o.id = r.id "
            "WHERE r.min_x >= ? AND r.max_x <= ? AND r.min_y >= ? AND r.max_y <= ?)",
            region_params, "any object inside region", {"region_params": region_params}))
    if f.text:
        q = fts_query(f.text, "AND")
        if q:
            preds.append(Predicate("text", "p.id IN (SELECT rowid FROM photos_fts WHERE photos_fts MATCH ?)",
                                   [q], f"FTS5 MATCH {q}", {"fts": q}))
        else:
            warnings.append(f"text:'{f.text}' has no searchable tokens; ignored")
    if f.source:
        preds.append(Predicate("source", "p.source = ?", [f.source], f"source = '{f.source}'", {"source": f.source}))
    return preds, warnings


def where_clause(preds: list[Predicate]) -> tuple[str, list]:
    if not preds:
        return "1=1", []
    return " AND ".join(f"({p.sql})" for p in preds), [x for p in preds for x in p.params]


# ====================================================================== selectivity
def _probe(conn, sql: str, params) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM ({sql} LIMIT {PROBE_CAP})", list(params)).fetchone()[0])


def estimate_selectivity(conn, stats: dict, preds: list[Predicate]) -> tuple[list[dict], float]:
    n = max(int(stats.get("n", 0)), 1)
    rows, combined = [], 1.0
    for p in preds:
        m = p.meta
        if p.kind == "tag":
            cnt = conn.execute(
                "SELECT COUNT(*) FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id WHERE t.name = ?", (m["tag"],)
            ).fetchone()[0]
            s, method = cnt / n, "exact count (idx_photo_tags_tag)"
        elif p.kind == "camera":
            needle = m["camera"].lower()
            cnt = sum(c for name, c in stats.get("cameras", {}).items() if needle in name.lower())
            s, method = cnt / n, "camera histogram"
        elif p.kind == "date":
            q = stats.get("date_quantiles") or []
            if not q:
                s = 0.0
            else:
                grid = np.linspace(0.0, 1.0, len(q))
                lo = float(np.interp(m["lo"], q, grid, left=0.0, right=1.0))
                hi = float(np.interp(m["hi"], q, grid, left=0.0, right=1.0))
                s = max(0.0, hi - lo) * stats.get("dated", 0) / n
            method = f"equi-depth histogram ({max(len(q) - 1, 0)} buckets)"
        elif p.kind == "near":
            cnt = _probe(conn, "SELECT id FROM geo_rtree WHERE min_lat >= ? AND max_lat <= ? "
                               "AND min_lon >= ? AND max_lon <= ?", m["box"])
            s = cnt * (math.pi / 4) / n
            method = "R*Tree bbox probe × π/4" + (" (capped)" if cnt >= PROBE_CAP else "")
        elif p.kind == "object":
            s = stats.get("object_labels", {}).get(m["label"], 0) / n
            method = "object-label histogram"
            if m.get("region_params"):
                tot = max(int(stats.get("total_objects", 0)), 1)
                cnt = _probe(conn, "SELECT id FROM object_rtree WHERE min_x >= ? AND max_x <= ? "
                                   "AND min_y >= ? AND max_y <= ?", m["region_params"])
                s *= min(1.0, cnt / tot)
                method += " × R*Tree region probe"
        elif p.kind == "region":
            tot = max(int(stats.get("total_objects", 0)), 1)
            cnt = _probe(conn, "SELECT id FROM object_rtree WHERE min_x >= ? AND max_x <= ? "
                               "AND min_y >= ? AND max_y <= ?", m["region_params"])
            s = min(1.0, cnt / tot) * stats.get("photos_with_objects", 0) / n
            method = "R*Tree region probe"
        elif p.kind == "text":
            cnt = _probe(conn, "SELECT rowid FROM photos_fts WHERE photos_fts MATCH ?", [m["fts"]])
            s, method = cnt / n, "FTS5 capped probe"
        elif p.kind == "source":
            s, method = stats.get("sources", {}).get(m["source"], 0) / n, "source histogram"
        else:
            s, method = 1.0, "unknown"
        s = min(max(s, 0.0), 1.0)
        combined *= s
        rows.append({"predicate": p.label, "kind": p.kind, "method": method,
                     "selectivity": round(s, 6), "estimated_rows": round(s * n, 1)})
    return rows, min(max(combined, 0.0), 1.0)


# ====================================================================== cost model
@dataclass
class CostModel:
    sql_fixed_ms: float = 0.25        # statement prepare + first row
    sql_row_ms: float = 0.0015        # per candidate id materialised from SQLite
    gather_row_ms: float = 0.0004     # numpy fancy-index per row
    dot_ms_per_dim: float = 6e-7      # per (row × dim) multiply-add
    hnsw_fixed_ms: float = 0.05
    hnsw_ef_ms: float = 0.004         # marginal cost per unit of efSearch
    verify_id_ms: float = 0.002       # per HNSW id verified against predicates
    safety: float = 1.5               # α: over-fetch factor for vector-first
    degenerate_ratio: float = 0.35    # vector-first pointless above this share of N
    calibrated: bool = False

    def filter_first(self, n_candidates: float, dim: int) -> float:
        return self.sql_fixed_ms + n_candidates * (self.sql_row_ms + self.gather_row_ms + dim * self.dot_ms_per_dim)

    def k_prime(self, k: int, selectivity: float, n_vectors: int) -> int:
        if n_vectors <= 0:
            return 0
        s = max(selectivity, 1.0 / n_vectors)
        return int(min(n_vectors, math.ceil(k * self.safety / s)))

    def vector_first(self, k: int, selectivity: float, n_vectors: int, ef_base: int) -> tuple[float, int, int]:
        kp = self.k_prime(k, selectivity, n_vectors)
        ef = max(ef_base, kp)
        cost = self.hnsw_fixed_ms + self.hnsw_ef_ms * ef + self.sql_fixed_ms + kp * self.verify_id_ms
        return cost, kp, ef


# ====================================================================== tracing
class Trace:
    def __init__(self):
        self.buckets = {b: 0.0 for b in ("planning", "sqlite", "faiss", "exact", "fusion", "fetch")}
        self.steps: list[dict] = []

    @contextmanager
    def step(self, bucket: str, op: str, detail: str = ""):
        rec = {"op": op, "bucket": bucket, "detail": detail, "rows": None, "ms": 0.0}
        t = time.perf_counter()
        try:
            yield rec
        finally:
            rec["ms"] = round((time.perf_counter() - t) * 1000, 3)
            self.buckets[bucket] = self.buckets.get(bucket, 0.0) + rec["ms"]
            self.steps.append(rec)


LEX_SQL = ("SELECT rowid, bm25(photos_fts, 0.5, 4.0, 3.0, 1.0) AS r FROM photos_fts "
           "WHERE photos_fts MATCH ? ORDER BY r LIMIT ?")
FETCH_SQL = """
SELECT p.id, p.file_name, p.width, p.height, p.taken_at, p.camera_make, p.camera_model,
       p.caption, p.source, p.gps_lat, p.gps_lon,
       (SELECT group_concat(t.name, '|') FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id
         WHERE pt.photo_id = p.id) AS tags
FROM photos p WHERE p.id IN (SELECT value FROM json_each(?))
"""
STRATEGY_NAMES = ("metadata_only", "vector_only", "filter_first", "vector_first", "empty")


# ====================================================================== planner
class QueryPlanner:
    def __init__(self, vindex: VectorIndex, ef_search: int = 64, cost_model: CostModel | None = None):
        self.vindex, self.ef_search = vindex, ef_search
        self.cost = cost_model or CostModel()

    # ------------------------------------------------------------------ calibration
    def calibrate(self, conn) -> dict:
        cm, dim = self.cost, self.vindex.dim
        rng = np.random.default_rng(7)
        mat = rng.standard_normal((20000, dim), dtype=np.float32)
        q = mat[0].copy()
        _ = mat @ q
        t = time.perf_counter()
        for _ in range(5):
            _ = mat @ q
        cm.dot_ms_per_dim = max((time.perf_counter() - t) * 1000 / 5 / (20000 * dim), 1e-9)
        idx = rng.integers(0, 20000, 20000)
        t = time.perf_counter()
        for _ in range(5):
            _ = mat[idx]
        cm.gather_row_ms = max((time.perf_counter() - t) * 1000 / 5 / 20000, 1e-7)
        t = time.perf_counter()
        rows = conn.execute("SELECT id FROM photos").fetchall()
        if len(rows) >= 500:
            cm.sql_row_ms = max((time.perf_counter() - t) * 1000 / len(rows), 1e-6)
        if len(self.vindex) >= 1000:
            qs = self.vindex.sample_vectors(8)

            def bench(ef: int) -> float:
                t0 = time.perf_counter()
                for qv in qs:
                    self.vindex.search(qv, 10, ef=ef)
                return (time.perf_counter() - t0) * 1000 / len(qs)

            bench(32)
            t_lo, t_hi = bench(32), bench(512)
            slope = max((t_hi - t_lo) / 480.0, 1e-6)
            cm.hnsw_ef_ms, cm.hnsw_fixed_ms = slope, max(t_lo - slope * 32, 0.005)
        cm.calibrated = True
        return asdict(cm)

    # ------------------------------------------------------------------ main entry
    def search(self, conn, *, qvec: np.ndarray | None, filters: Filters, k: int, mode: str = "auto",
               lexical_text: str = "", lexical_weight: float = 0.0, exclude_ids=(), warnings=()):
        t0 = time.perf_counter()
        tr = Trace()
        exclude = {int(i) for i in exclude_ids}
        k_fetch = k + len(exclude)
        n_vec = len(self.vindex)
        plan: dict = {"mode_requested": mode, "k": k, "n_vectors": n_vec, "predicates": [],
                      "estimates": None, "warnings": list(warnings), "sql": [], "sqlite_query_plan": []}

        with tr.step("planning", "parse filters → SQL predicates") as st:
            preds, pw = build_predicates(filters)
            plan["warnings"] += pw
            where_sql, where_params = where_clause(preds)
            st["rows"] = len(preds)

        # ---- lexical channel (BM25 over FTS5), fused with cosine later
        lex: dict[int, float] = {}
        lq = fts_query(lexical_text, "OR", drop_stop=True) if (lexical_text and lexical_weight > 0) else ""
        if lq:
            with tr.step("sqlite", "FTS5 lexical channel (BM25)", lq) as st:
                lrows = conn.execute(LEX_SQL, (lq, max(50, 4 * k))).fetchall()
                st["rows"] = len(lrows)
            raw = {int(r[0]): -float(r[1]) for r in lrows}
            top = max(raw.values(), default=0.0)
            if top > 0:
                lex = {i: max(v, 0.0) / top for i, v in raw.items()}
            plan["sql"].append(LEX_SQL)

        # ---- choose strategy
        kp = 0
        if qvec is None:
            strategy, reason = "metadata_only", "No semantic query: pure relational retrieval ordered by capture date."
        elif n_vec == 0:
            strategy, reason = "empty", "The vector index is empty. Ingest photos first."
        elif not preds:
            if mode == "filter_first":
                strategy, reason = "filter_first", "Forced: exact brute-force cosine over all vectors (ground truth)."
            else:
                strategy, reason = "vector_only", "No structured predicates: HNSW top-k directly."
        else:
            with tr.step("planning", "selectivity estimation + cost model") as st:
                stats = load_planner_stats(conn)
                pred_rows, s = estimate_selectivity(conn, stats, preds)
                n_rows = int(stats.get("n", n_vec))
                est_rows = s * n_rows
                c_ff = self.cost.filter_first(est_rows, self.vindex.dim)
                c_vf, kp, ef = self.cost.vector_first(k_fetch, s, n_vec, self.ef_search)
                degenerate = kp >= self.cost.degenerate_ratio * n_vec
                st["rows"] = len(pred_rows)
            plan["predicates"] = pred_rows
            plan["estimates"] = {
                "selectivity": round(s, 6), "estimated_rows": round(est_rows, 1), "n_rows": n_rows,
                "filter_first_ms": round(c_ff, 4), "vector_first_ms": round(c_vf, 4),
                "k_prime": kp, "ef_search": ef, "degenerate": degenerate,
                "assumption": "predicate independence (selectivities multiplied)",
                "formula": {
                    "filter_first": "C_ff = C_sql + N·s·(c_row + c_gather + d·c_dot)",
                    "vector_first": "C_vf = C_hnsw + c_ef·max(ef, k') + C_sql + k'·c_verify,  k' = ⌈k·α / s⌉",
                },
            }
            if mode in ("filter_first", "vector_first"):
                strategy, reason = mode, "Forced by request."
            elif degenerate:
                strategy = "filter_first"
                reason = (f"Vector-first would need k'={kp} ({kp / max(n_vec, 1):.0%} of the index) "
                          f"to expect {k_fetch} survivors, so it is degenerate and filter-first is chosen.")
            elif c_ff <= c_vf:
                strategy = "filter_first"
                reason = f"Estimated filter-first {c_ff:.3f} ms ≤ vector-first {c_vf:.3f} ms (s≈{s:.4f})."
            else:
                strategy = "vector_first"
                reason = f"Estimated vector-first {c_vf:.3f} ms < filter-first {c_ff:.3f} ms (s≈{s:.4f})."

        if preds:
            filter_sql = f"SELECT p.id FROM photos p WHERE {where_sql}"
            plan["sql"].insert(0, filter_sql)
            plan["sqlite_query_plan"] = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + filter_sql, where_params)]

        # ---- execute
        cos: dict[int, float] = {}
        final: dict[int, float] = {}
        if strategy == "metadata_only":
            with tr.step("sqlite", "SQL filter + ORDER BY taken_ts DESC", where_sql) as st:
                sql = (f"SELECT p.id FROM photos p WHERE {where_sql} "
                       "ORDER BY p.taken_ts IS NULL, p.taken_ts DESC, p.id DESC LIMIT ?")
                ids = [int(r[0]) for r in conn.execute(sql, [*where_params, k_fetch])]
                st["rows"] = len(ids)
            ordered = [i for i in ids if i not in exclude][:k]
        elif strategy == "empty":
            ordered = []
        else:
            if strategy == "vector_only":
                cos = self._vector_only(qvec, k_fetch, lex, tr)
            elif strategy == "filter_first":
                cos = self._filter_first(conn, qvec, where_sql, where_params, k_fetch, lex, tr)
            else:
                cos, attempts, fell_back = self._vector_first(
                    conn, qvec, where_sql, where_params, k_fetch, kp, n_vec, lex, tr)
                plan["vector_first_attempts"] = attempts
                if fell_back:
                    plan["strategy_fallback"] = "filter_first"
                    reason += " Fell back to exact filter-first after 3 under-filled HNSW attempts."
            with tr.step("fusion", "score fusion: s = cos + w·bm25_norm", f"w={lexical_weight}") as st:
                final = {i: c + lexical_weight * lex.get(i, 0.0) for i, c in cos.items() if i not in exclude}
                ordered = sorted(final, key=final.get, reverse=True)[:k]
                st["rows"] = len(final)

        with tr.step("fetch", "fetch result rows (json_each)") as st:
            rows = {int(r["id"]): r for r in conn.execute(FETCH_SQL, (json.dumps(ordered),))} if ordered else {}
            st["rows"] = len(rows)

        results = []
        for rank, pid in enumerate(ordered, 1):
            r = rows.get(pid)
            if r is None:
                continue
            item = dict(r)
            item["tags"] = [t for t in (item.pop("tags") or "").split("|") if t]
            item["rank"] = rank
            if pid in final:
                item.update(score=round(final[pid], 5), cosine=round(cos[pid], 5), lexical=round(lex.get(pid, 0.0), 5))
            else:
                item.update(score=None, cosine=None, lexical=None)
            results.append(item)

        timings = {b: round(v, 3) for b, v in tr.buckets.items()}
        timings["total"] = round((time.perf_counter() - t0) * 1000, 3)
        plan.update(strategy=strategy, reason=reason, steps=tr.steps, timings_ms=timings,
                    returned=len(results), lexical_query=lq or None, lexical_weight=lexical_weight)
        return results, plan

    # ------------------------------------------------------------------ strategies
    def _vector_only(self, qvec, k_fetch, lex, tr) -> dict[int, float]:
        with tr.step("faiss", "HNSW top-k search", f"k={k_fetch}, efSearch={max(self.ef_search, k_fetch)}") as st:
            ids, sc = self.vindex.search(qvec, k_fetch)
            st["rows"] = len(ids)
        cos = {int(i): float(s) for i, s in zip(ids, sc)}
        extra = [i for i in lex if i not in cos]
        if extra:
            with tr.step("exact", "exact cosine for lexical-only hits") as st:
                f_ids, f_sc = self.vindex.exact_scores(qvec, extra)
                cos.update(zip(f_ids.tolist(), f_sc.tolist()))
                st["rows"] = len(f_ids)
        return cos

    def _filter_first(self, conn, qvec, where_sql, where_params, k_fetch, lex, tr) -> dict[int, float]:
        with tr.step("sqlite", "SQL filter scan (B-tree / FTS5 / R*Tree)", where_sql) as st:
            cand = np.fromiter((r[0] for r in conn.execute(f"SELECT p.id FROM photos p WHERE {where_sql}",
                                                           where_params)), dtype=np.int64)
            st["rows"] = len(cand)
        with tr.step("exact", "brute-force cosine over candidates (BLAS)") as st:
            ids, sc = self.vindex.exact_scores(qvec, cand)
            keep = min(len(ids), 2 * k_fetch + 32)
            top = np.argpartition(-sc, keep - 1)[:keep] if 0 < keep < len(ids) else np.arange(len(ids))
            cos = {int(ids[j]): float(sc[j]) for j in top}
            if lex and len(ids):
                mask = np.isin(ids, np.fromiter(lex.keys(), dtype=np.int64))
                for j in np.nonzero(mask)[0]:
                    cos[int(ids[j])] = float(sc[j])
            st["rows"] = len(ids)
        return cos

    def _vector_first(self, conn, qvec, where_sql, where_params, k_fetch, kp, n_vec, lex, tr):
        attempts: list[dict] = []
        cos: dict[int, float] = {}
        kp = max(int(kp), k_fetch)
        for attempt in range(1, 4):
            with tr.step("faiss", f"HNSW over-fetch (attempt {attempt})",
                         f"k'={kp}, efSearch={max(self.ef_search, kp)}") as st:
                ids, sc = self.vindex.search(qvec, kp)
                st["rows"] = len(ids)
            with tr.step("sqlite", "verify predicates on HNSW candidates") as st:
                ok = self._verify(conn, ids.tolist(), where_sql, where_params)
                st["rows"] = len(ok)
            cos = {int(i): float(s) for i, s in zip(ids, sc) if int(i) in ok}
            attempts.append({"attempt": attempt, "k_prime": kp, "hnsw_returned": int(len(ids)), "survivors": len(cos)})
            if len(cos) >= k_fetch or kp >= n_vec:
                break
            kp = min(n_vec, kp * 4)
        else:
            return self._filter_first(conn, qvec, where_sql, where_params, k_fetch, lex, tr), attempts, True
        extra = [i for i in lex if i not in cos]
        if extra:
            with tr.step("sqlite", "verify predicates on lexical hits") as st:
                ok = self._verify(conn, extra, where_sql, where_params)
                st["rows"] = len(ok)
            if ok:
                with tr.step("exact", "exact cosine for lexical hits") as st:
                    f_ids, f_sc = self.vindex.exact_scores(qvec, sorted(ok))
                    cos.update(zip(f_ids.tolist(), f_sc.tolist()))
                    st["rows"] = len(f_ids)
        return cos, attempts, False

    @staticmethod
    def _verify(conn, ids, where_sql, where_params) -> set[int]:
        if not ids:
            return set()
        sql = f"SELECT p.id FROM photos p WHERE p.id IN (SELECT value FROM json_each(?)) AND {where_sql}"
        return {int(r[0]) for r in conn.execute(sql, [json.dumps([int(i) for i in ids]), *where_params])}