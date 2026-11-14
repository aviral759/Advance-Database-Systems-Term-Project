"""Bulk-ingest a COCO manifest or a plain folder of images directly (no HTTP round-trips).

If the API server is running, click "Reload index from SQLite" on the System tab
(or POST /api/admin/reload) afterwards so it picks up the new vectors.
"""
import argparse
import json
import random
import sys
import time
from collections import Counter
from itertools import islice
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tqdm import tqdm                      # noqa: E402

from app import db                         # noqa: E402
from app.context import build_context      # noqa: E402
from app.ingest import IngestItem          # noqa: E402

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
# Demo-only coordinates. Items that get them are tagged "synthetic-geo" so this is never hidden.
DEMO_CITIES = [
    ("London", 51.5074, -0.1278), ("New York", 40.7128, -74.0060), ("Tokyo", 35.6762, 139.6503),
    ("Paris", 48.8566, 2.3522), ("Sydney", -33.8688, 151.2093), ("Cape Town", -33.9249, 18.4241),
    ("Sao Paulo", -23.5505, -46.6333), ("Berlin", 52.5200, 13.4050), ("San Francisco", 37.7749, -122.4194),
    ("Singapore", 1.3521, 103.8198),
]


def synthetic_gps(rng: random.Random) -> tuple[float, float]:
    _, lat, lon = rng.choice(DEMO_CITIES)
    return round(lat + rng.uniform(-0.15, 0.15), 6), round(lon + rng.uniform(-0.15, 0.15), 6)


def iter_manifest(path: Path, rng: random.Random, synthetic_geo: bool):
    base = path.parent
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            img = base / rec["file"]
            if not img.exists():
                continue
            tags, gps = [], None
            if synthetic_geo:
                gps = synthetic_gps(rng)
                tags.append("synthetic-geo")
            yield IngestItem(data=img.read_bytes(), file_name=img.name, caption=rec.get("caption", ""),
                             tags=tags, objects=rec.get("objects", []), taken_at=rec.get("taken_at"),
                             gps=gps, source=rec.get("source", "coco-val2017"))


def iter_folder(folder: Path, rng: random.Random, synthetic_geo: bool):
    for p in sorted(folder.rglob("*")):
        if p.suffix.lower() not in IMAGE_EXT:
            continue
        tags, gps = [], None
        if synthetic_geo:
            gps = synthetic_gps(rng)
            tags.append("synthetic-geo")
        yield IngestItem(data=p.read_bytes(), file_name=p.name, tags=tags, gps=gps, source="folder")


def batched(it, n):
    it = iter(it)
    while batch := list(islice(it, n)):
        yield batch


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--manifest", type=Path)
    src.add_argument("--folder", type=Path)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--synthetic-geo", action="store_true", help="assign labelled demo GPS coordinates")
    ap.add_argument("--no-autotag", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    if args.manifest:
        total = sum(1 for line in open(args.manifest, encoding="utf-8") if line.strip())
        items = iter_manifest(args.manifest, rng, args.synthetic_geo)
    else:
        total = sum(1 for p in args.folder.rglob("*") if p.suffix.lower() in IMAGE_EXT)
        items = iter_folder(args.folder, rng, args.synthetic_geo)
    if args.limit:
        items, total = islice(items, args.limit), min(total, args.limit)

    ctx = build_context()
    counts: Counter = Counter()
    t0 = time.perf_counter()
    with tqdm(total=total, desc="ingest", unit="img") as bar:
        for batch in batched(items, args.batch):
            res = ctx.ingestor.ingest(batch, autotag=not args.no_autotag, save_index=False, refresh_stats=False)
            counts.update(r["status"] for r in res)
            bar.update(len(batch))
    ctx.vindex.save()
    with db.get_conn() as conn:
        db.refresh_planner_stats(conn)
    dt = time.perf_counter() - t0
    print(f"\n{dict(counts)} in {dt:.1f}s  ({sum(counts.values()) / max(dt, 1e-9):.1f} img/s)")
    print(f"Index now holds {len(ctx.vindex)} vectors.")
    print("If the server is running: System tab → 'Reload index from SQLite' (or POST /api/admin/reload).")


if __name__ == "__main__":
    main()