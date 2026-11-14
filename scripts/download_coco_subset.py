"""Download a reproducible random subset of COCO val2017 with captions and boxes.

Output: <out>/images/*.jpg and <out>/manifest.jsonl (one JSON record per image).
The annotation archive (~240 MB) is cached in datasets/_cache and only downloaded once.
"""
import argparse
import json
import random
import time
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from tqdm import tqdm

ANN_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
IMG_URL = "http://images.cocodataset.org/val2017/{}"


def download_file(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(tmp, "wb") as fh, tqdm(total=total, unit="B", unit_scale=True, desc=dest.name) as bar:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
                bar.update(len(chunk))
    tmp.replace(dest)


def fetch_image(file_name: str, dest_dir: Path, retries: int = 3) -> bool:
    dest = dest_dir / file_name
    if dest.exists() and dest.stat().st_size > 0:
        return True
    for attempt in range(retries):
        try:
            r = requests.get(IMG_URL.format(file_name), timeout=30)
            r.raise_for_status()
            tmp = dest.with_suffix(".part")
            tmp.write_bytes(r.content)
            tmp.replace(dest)
            return True
        except requests.RequestException:
            time.sleep(1.5 * (attempt + 1))
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=1000, help="number of images (max 5000)")
    ap.add_argument("--out", type=Path, default=Path("datasets/coco_val2017_subset"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    cache = args.out.parent / "_cache"
    zpath = cache / "annotations_trainval2017.zip"
    print("Fetching annotations (cached after first run)...")
    download_file(ANN_URL, zpath)
    with zipfile.ZipFile(zpath) as z:
        caps = json.loads(z.read("annotations/captions_val2017.json"))
        inst = json.loads(z.read("annotations/instances_val2017.json"))

    cats = {c["id"]: c["name"] for c in inst["categories"]}
    images = {im["id"]: im for im in inst["images"]}
    captions = defaultdict(list)
    for a in caps["annotations"]:
        captions[a["image_id"]].append(a["caption"].strip())
    objects = defaultdict(list)
    for a in inst["annotations"]:
        if a.get("iscrowd"):
            continue
        im = images[a["image_id"]]
        x, y, w, h = a["bbox"]
        W, H = im["width"], im["height"]
        objects[a["image_id"]].append({
            "label": cats[a["category_id"]],
            "bbox": [round(x / W, 4), round(y / H, 4), round(min(1.0, (x + w) / W), 4), round(min(1.0, (y + h) / H), 4)],
            "score": 1.0,
        })

    ids = sorted(images)
    random.Random(args.seed).shuffle(ids)
    chosen = ids[: min(args.n, len(ids))]
    img_dir = args.out / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    ok: set[int] = set()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_image, images[i]["file_name"], img_dir): i for i in chosen}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="images"):
            if fut.result():
                ok.add(futures[fut])

    manifest = args.out / "manifest.jsonl"
    with open(manifest, "w", encoding="utf-8") as fh:
        for iid in chosen:
            if iid not in ok:
                continue
            im = images[iid]
            fh.write(json.dumps({
                "file": f"images/{im['file_name']}",
                "caption": (captions[iid] or [""])[0],
                "captions": captions[iid],
                "objects": objects[iid],
                "taken_at": im.get("date_captured"),
                "coco_id": iid,
                "license": im.get("license"),
                "flickr_url": im.get("flickr_url"),
                "source": "coco-val2017",
            }) + "\n")
    print(f"Done: {len(ok)}/{len(chosen)} images → {manifest}")


if __name__ == "__main__":
    main()