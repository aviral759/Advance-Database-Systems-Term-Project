"""FAISS HNSW index manager.

* IndexIDMap2(IndexHNSWFlat, inner product). Vectors are L2-normalised, so IP = cosine.
* A dense in-RAM matrix mirrors the index so that the filter-first strategy can do exact
  BLAS scoring over an arbitrary candidate subset.
* HNSW does not support removal: deletes are tombstoned and purged by compact().
* SQLite (photo_embeddings) is the source of truth; the .index file is a cache that is
  validated with a signature and rebuilt automatically if stale.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

import faiss
import numpy as np

log = logging.getLogger(__name__)


class VectorIndex:
    def __init__(self, dim: int, path: Path, m: int = 32, ef_construction: int = 200, ef_search: int = 64):
        self.dim, self.path = dim, Path(path)
        self.m, self.ef_construction, self.ef_search = m, ef_construction, ef_search
        self.model_id = ""
        self._lock = threading.RLock()
        self._ids = np.empty(0, dtype=np.int64)
        self._mat = np.empty((0, dim), dtype=np.float32)
        self._deleted: set[int] = set()
        self._reset_index()

    # ------------------------------------------------------------------ construction
    def _reset_index(self) -> None:
        base = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_INNER_PRODUCT)
        base.hnsw.efConstruction = self.ef_construction
        base.hnsw.efSearch = self.ef_search
        self._hnsw = base
        self.index = faiss.IndexIDMap2(base)

    @property
    def _meta_path(self) -> Path:
        return self.path.with_suffix(".meta.json")

    def _signature(self) -> dict:
        return {
            "model_id": self.model_id, "dim": self.dim, "m": self.m,
            "ntotal": int(len(self._ids)),
            "id_sum": int(self._ids.sum()) if len(self._ids) else 0,
            "id_max": int(self._ids.max()) if len(self._ids) else 0,
        }

    def load_from_db(self, conn, model_id: str) -> dict:
        rows = conn.execute(
            "SELECT photo_id, vector FROM photo_embeddings WHERE model = ? AND dim = ? ORDER BY photo_id",
            (model_id, self.dim),
        ).fetchall()
        foreign = conn.execute(
            "SELECT COUNT(*) FROM photo_embeddings WHERE model != ? OR dim != ?", (model_id, self.dim)
        ).fetchone()[0]
        ids = np.fromiter((r[0] for r in rows), dtype=np.int64, count=len(rows))
        mat = (np.frombuffer(b"".join(r[1] for r in rows), dtype=np.float32).reshape(len(rows), self.dim).copy()
               if rows else np.empty((0, self.dim), np.float32))
        with self._lock:
            self._ids, self._mat, self.model_id = ids, mat, model_id
            self._deleted.clear()
            loaded = False
            if self.path.exists() and self._meta_path.exists():
                try:
                    meta = json.loads(self._meta_path.read_text())
                    if meta == self._signature():
                        idx = faiss.read_index(str(self.path))
                        self.index = idx if isinstance(idx, faiss.IndexIDMap2) else faiss.downcast_index(idx)
                        self._hnsw = faiss.downcast_index(self.index.index)
                        self._hnsw.hnsw.efSearch = self.ef_search
                        loaded = True
                except Exception as exc:  # corrupted cache -> rebuild
                    log.warning("Could not load FAISS index (%s); rebuilding", exc)
            if not loaded:
                self._rebuild()
        if foreign:
            log.warning("%d embeddings belong to another model and were skipped; re-ingest to use them.", foreign)
        return {"vectors": len(ids), "loaded_from_disk": loaded, "skipped_foreign": foreign}

    def _rebuild(self) -> None:
        self._reset_index()
        if len(self._ids):
            self.index.add_with_ids(self._mat, self._ids)
        self.save()

    # ------------------------------------------------------------------ mutation
    def add(self, ids, vecs) -> None:
        ids = np.asarray(ids, dtype=np.int64)
        vecs = np.ascontiguousarray(vecs, dtype=np.float32).reshape(-1, self.dim)
        if not len(ids):
            return
        with self._lock:
            self.index.add_with_ids(vecs, ids)
            self._ids = np.concatenate([self._ids, ids])
            self._mat = np.vstack([self._mat, vecs])
            if len(self._ids) > 1 and not np.all(np.diff(self._ids) > 0):
                order = np.argsort(self._ids, kind="stable")
                self._ids, self._mat = self._ids[order], self._mat[order]

    def remove(self, photo_id: int) -> None:
        with self._lock:
            self._deleted.add(int(photo_id))

    def compact(self) -> dict:
        with self._lock:
            removed = len(self._deleted)
            if removed:
                keep = ~np.isin(self._ids, np.fromiter(self._deleted, dtype=np.int64))
                self._ids, self._mat = self._ids[keep], self._mat[keep]
                self._deleted.clear()
            self._rebuild()
        return {"removed": removed, "vectors": len(self._ids)}

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            faiss.write_index(self.index, str(tmp))
            os.replace(tmp, self.path)
            self._meta_path.write_text(json.dumps(self._signature()))

    # ------------------------------------------------------------------ queries
    def __len__(self) -> int:
        return int(len(self._ids) - len(self._deleted))

    def search(self, q: np.ndarray, k: int, ef: int | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Approximate top-k by inner product via HNSW."""
        q = np.ascontiguousarray(q, dtype=np.float32).reshape(1, -1)
        with self._lock:
            n = int(self.index.ntotal)
            if n == 0 or k <= 0:
                return np.empty(0, np.int64), np.empty(0, np.float32)
            kk = int(min(n, k + len(self._deleted)))
            self._hnsw.hnsw.efSearch = int(max(ef or self.ef_search, kk))
            dist, idx = self.index.search(q, kk)
            deleted = np.fromiter(self._deleted, dtype=np.int64) if self._deleted else None
        ids, scores = idx[0], dist[0]
        mask = ids >= 0
        if deleted is not None:
            mask &= ~np.isin(ids, deleted)
        return ids[mask][:k], scores[mask][:k]

    def exact_scores(self, q: np.ndarray, ids) -> tuple[np.ndarray, np.ndarray]:
        """Exact cosine for a candidate id subset (filter-first path)."""
        ids = np.asarray(ids, dtype=np.int64)
        with self._lock:
            if not len(self._ids) or not len(ids):
                return np.empty(0, np.int64), np.empty(0, np.float32)
            pos = np.searchsorted(self._ids, ids)
            pos_c = np.clip(pos, 0, len(self._ids) - 1)
            valid = (pos < len(self._ids)) & (self._ids[pos_c] == ids)
            if self._deleted:
                valid &= ~np.isin(ids, np.fromiter(self._deleted, dtype=np.int64))
            scores = self._mat[pos_c[valid]] @ np.asarray(q, dtype=np.float32).ravel()
        return ids[valid], scores

    def get_vector(self, photo_id: int) -> np.ndarray | None:
        with self._lock:
            if photo_id in self._deleted or not len(self._ids):
                return None
            pos = int(np.searchsorted(self._ids, photo_id))
            if pos < len(self._ids) and self._ids[pos] == photo_id:
                return self._mat[pos].copy()
        return None

    def sample_vectors(self, n: int, seed: int = 0) -> np.ndarray:
        with self._lock:
            if not len(self._ids):
                return np.empty((0, self.dim), np.float32)
            rows = np.random.default_rng(seed).choice(len(self._ids), size=min(n, len(self._ids)), replace=False)
            return self._mat[rows].copy()

    def stats(self) -> dict:
        return {
            "type": "IndexIDMap2(IndexHNSWFlat)",
            "metric": "inner product (cosine on L2-normalised vectors)",
            "dim": self.dim, "M": self.m,
            "ef_construction": self.ef_construction, "ef_search": self.ef_search,
            "ntotal": int(self.index.ntotal), "active": len(self), "tombstones": len(self._deleted),
            "index_file_bytes": self.path.stat().st_size if self.path.exists() else 0,
            "model_id": self.model_id,
        }