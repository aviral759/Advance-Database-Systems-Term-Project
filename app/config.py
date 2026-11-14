"""Environment-driven settings. Every value can be overridden with an HPS_* variable."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    model_name: str
    pretrained: str
    device: str
    fake_embedder: bool
    hnsw_m: int
    hnsw_ef_construction: int
    hnsw_ef_search: int
    thumb_size: int
    max_upload_mb: int
    demo_token: str
    read_only: bool
    autotag_top_k: int
    autotag_min_prob: float

    @property
    def db_path(self) -> Path:
        return self.data_dir / "library.db"

    @property
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def thumbs_dir(self) -> Path:
        return self.data_dir / "thumbs"

    @property
    def index_path(self) -> Path:
        return self.data_dir / "faiss_hnsw.index"

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.images_dir, self.thumbs_dir):
            p.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    return Settings(
        data_dir=Path(_env("HPS_DATA_DIR", str(ROOT / "data"))).resolve(),
        model_name=_env("HPS_CLIP_MODEL", "ViT-B-32"),
        pretrained=_env("HPS_CLIP_PRETRAINED", "laion2b_s34b_b79k"),
        device=_env("HPS_DEVICE", "auto"),
        fake_embedder=_env("HPS_FAKE_EMBEDDER", "0") == "1",
        hnsw_m=int(_env("HPS_HNSW_M", "32")),
        hnsw_ef_construction=int(_env("HPS_HNSW_EF_CONSTRUCTION", "200")),
        hnsw_ef_search=int(_env("HPS_HNSW_EF_SEARCH", "64")),
        thumb_size=int(_env("HPS_THUMB_SIZE", "384")),
        max_upload_mb=int(_env("HPS_MAX_UPLOAD_MB", "25")),
        demo_token=_env("HPS_DEMO_TOKEN", ""),
        read_only=_env("HPS_READ_ONLY", "0") == "1",
        autotag_top_k=int(_env("HPS_AUTOTAG_TOP_K", "5")),
        autotag_min_prob=float(_env("HPS_AUTOTAG_MIN_PROB", "0.08")),
    )


settings = load_settings()