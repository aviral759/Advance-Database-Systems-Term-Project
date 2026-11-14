"""Builds the long-lived application context (model, index, planner, ingestor)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from . import db
from .config import Settings, settings as default_settings
from .embeddings import Embedder, ZeroShotTagger, build_embedder
from .ingest import Ingestor
from .planner import QueryPlanner
from .vector_index import VectorIndex

log = logging.getLogger(__name__)


@dataclass
class AppContext:
    settings: Settings
    embedder: Embedder
    tagger: ZeroShotTagger
    vindex: VectorIndex
    planner: QueryPlanner
    ingestor: Ingestor


def build_context(settings: Settings = default_settings) -> AppContext:
    applied = db.init_db()
    if applied:
        log.info("Applied migrations: %s", applied)
    embedder = build_embedder(settings)
    tagger = ZeroShotTagger(embedder, top_k=settings.autotag_top_k, min_prob=settings.autotag_min_prob)
    vindex = VectorIndex(embedder.dim, settings.index_path, settings.hnsw_m,
                         settings.hnsw_ef_construction, settings.hnsw_ef_search)
    planner = QueryPlanner(vindex, settings.hnsw_ef_search)
    with db.get_conn() as conn:
        info = vindex.load_from_db(conn, embedder.model_id)
        log.info("Vector index: %s", info)
        db.refresh_planner_stats(conn)
        planner.calibrate(conn)
    return AppContext(settings, embedder, tagger, vindex, planner, Ingestor(settings, embedder, tagger, vindex))