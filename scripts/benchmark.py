"""Benchmark FILTER-FIRST vs VECTOR-FIRST vs AUTO across a log-spaced selectivity sweep.

Tags are chosen to approximate target selectivities (0.3% → 100%) so the crossover
point between the two strategies is visible. For each (query, tag) pair it records:
median latency per strategy, vector-first recall@k against exact filter-first, the
planner's choice, whether that choice was the measured-fastest, and regret
(auto ÷ fastest). Output: console table + data/benchmark.csv.
"""
import argparse
import csv
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db                          # noqa: E402
from app.config import settings             # noqa: E402
from app.context import build_context       # noqa: E402
from app.planner import Filters             # noqa: E402

QUERIES = [
    "people playing sports outdoors", "food on a plate", "an animal standing in a grassy field",
    "a city street with cars", "a cozy indoor room",
]
DEFAULT_TARGETS = [0.003, 0.01, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0]


def pick_tags(tag_rows, n, targets):
    """For each target selectivity choose the closest unused tag (within a factor of 2.5)."""
    chosen, used = [], set()
    for tgt in targets:
        best = min(((name, cnt) for name, cnt in tag_rows if name not in used),
                   key=lambda r: abs(math.log(r[1] / n) - math.log(tgt)), default=None)
        if best and abs(math.log(best[1] / n) - math.log(tgt)) <= math.log(2.5):
            chosen.append(best)
            used.add(best[0])
    return sorted(chosen, key=lambda r: r[1])


def run(planner, conn, qvec, f, k, mode, reps):
    lat, res, plan = [], [], {}
    for _ in range(reps):
        res, plan = planner.search(conn, qvec=qvec, filters=f, k=k, mode=mode)
        lat.append(plan["timings_ms"]["total"])
    return [r["id"] for r in res], plan, statistics.median(lat)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=24)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--targets", type=str, default=",".join(map(str, DEFAULT_TARGETS)),
                    help="comma-separated target selectivities")
    args = ap.parse_args()
    targets = [float(x) for x in args.targets.split(",") if x.strip()]

    ctx = build_context()
    rows = []
    with db.get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        tag_rows = [(r[0], r[1]) for r in conn.execute(
            "SELECT t.name, COUNT(*) AS c FROM photo_tags pt JOIN tags t ON t.id = pt.tag_id "
            "GROUP BY t.id HAVING c >= 2 ORDER BY c")]
        if not tag_rows:
            sys.exit("No tags found. Ingest a dataset first.")
        tags = pick_tags(tag_rows, n, targets)
        print(f"N = {n} photos, k = {args.k}, reps = {args.reps}, queries = {len(QUERIES)}")
        print("Selected tags: " + ", ".join(f"{t} ({c / n:.1%})" for t, c in tags) + "\n")

        # warm-up (model, caches, BLAS threads)
        warm = ctx.embedder.encode_texts(["warm up"])[0]
        for mode in ("filter_first", "vector_first"):
            ctx.planner.search(conn, qvec=warm, filters=Filters(tags=[tags[0][0]]), k=args.k, mode=mode)

        hnsw_recalls = []
        for q in QUERIES:
            qvec = ctx.embedder.encode_texts([q])[0]
            exact, _, _ = run(ctx.planner, conn, qvec, Filters(), args.k, "filter_first", 1)
            approx, _, _ = run(ctx.planner, conn, qvec, Filters(), args.k, "auto", 1)
            hnsw_recalls.append(len(set(exact) & set(approx)) / max(len(exact), 1))
            for name, cnt in tags:
                f = Filters(tags=[name])
                truth, _, t_ff = run(ctx.planner, conn, qvec, f, args.k, "filter_first", args.reps)
                vf, _, t_vf = run(ctx.planner, conn, qvec, f, args.k, "vector_first", args.reps)
                _, plan_auto, t_auto = run(ctx.planner, conn, qvec, f, args.k, "auto", args.reps)
                fastest = "filter_first" if t_ff <= t_vf else "vector_first"
                rows.append({
                    "query": q, "tag": name, "selectivity": round(cnt / n, 5),
                    "filter_first_ms": round(t_ff, 3), "vector_first_ms": round(t_vf, 3), "auto_ms": round(t_auto, 3),
                    "auto_choice": plan_auto["strategy"], "fastest": fastest,
                    "correct_choice": int(plan_auto["strategy"] == fastest),
                    "estimated_selectivity": plan_auto["estimates"]["selectivity"] if plan_auto.get("estimates") else None,
                    "vector_first_recall": round(len(set(vf) & set(truth)) / max(len(truth), 1), 3),
                    "regret": round(t_auto / max(min(t_ff, t_vf), 1e-9), 3),
                })

    header = f"{'tag':<16}{'sel':>8}{'FF ms':>9}{'VF ms':>9}{'AUTO ms':>9}  {'choice':<13}{'fastest':<13}{'VF rec':>7}{'regret':>8}"
    print(header)
    print("-" * len(header))
    crossover = None
    for name, cnt in tags:
        sub = [r for r in rows if r["tag"] == name]
        ff = statistics.mean(r["filter_first_ms"] for r in sub)
        vf = statistics.mean(r["vector_first_ms"] for r in sub)
        choices = [r["auto_choice"] for r in sub]
        choice = max(set(choices), key=choices.count)
        fastest = "filter_first" if ff <= vf else "vector_first"
        if crossover is None and fastest == "vector_first":
            crossover = cnt / n
        print(f"{name[:15]:<16}{cnt / n:>8.2%}{ff:>9.3f}{vf:>9.3f}{statistics.mean(r['auto_ms'] for r in sub):>9.3f}  "
              f"{choice:<13}{fastest:<13}{statistics.mean(r['vector_first_recall'] for r in sub):>7.3f}"
              f"{statistics.mean(r['regret'] for r in sub):>8.2f}")

    accuracy = statistics.mean(r["correct_choice"] for r in rows)
    print(f"\nPlanner picked the measured-fastest strategy in {accuracy:.0%} of {len(rows)} runs.")
    print(f"Mean regret: {statistics.mean(r['regret'] for r in rows):.3f}x   "
          f"Max regret: {max(r['regret'] for r in rows):.3f}x")
    print(f"Observed crossover (vector-first becomes faster): "
          f"{'≈ ' + format(crossover, '.1%') if crossover else 'not reached in this sweep'}")
    print(f"Unfiltered HNSW recall@{args.k} vs exact: {statistics.mean(hnsw_recalls):.3f}")

    out = settings.data_dir / "benchmark.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()