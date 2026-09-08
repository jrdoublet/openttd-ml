"""C43/E3 famille 2 : ROAD_MIN_DISTANCE/ROAD_MAX_DISTANCE mordent-elles ? Panneau VIVIER_REJECT
(reason=road_distance_short/road_distance_long), instrumente le 2026-09-08 (candidates.nut, 4
sites : pax ville-ville, fret industrie-industrie, fret industrie-ville, feeder).

⚠️ Meme piege de denominateur que road_town_rejected (docs/taches.md, ROAD_ACCEPTANCE_FULL_UNIT) :
les rejets de distance arrivent AVANT stats.pairsInBand++ de leur propre boucle, alors que
VIVIER_GEN.produced agrege plusieurs boucles distinctes. Comptes bruts seulement, pas de ratio
contre produced/kept.

Lit openttd_output UNE SEULE FOIS par (graine, arm), depuis la derniere ligne de checkpoint --
docs/taches.md 2026-09-08 (2562e96) : cette valeur est identique a chaque ligne de checkpoint
mensuel d'une meme partie.
"""
import argparse
import re
from collections import Counter
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup, keep, make_cfg
import bench_v2

SCRIPT_DEBUG_LEVEL = "4"
_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", f"script={SCRIPT_DEBUG_LEVEL}") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

LINE_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[(\w)\] (.*)")
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_opex_decisions(output):
    events = []
    for line in (output or "").splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        _company, _level, text = m.groups()
        m2 = OPEX_RE.match(text.strip())
        if not m2:
            continue
        _y, _mo, _d, kind, rest = m2.groups()
        fields = {}
        for token in rest.split():
            if "=" in token:
                key, _, value = token.partition("=")
                fields[key] = value
        events.append({"kind": kind, "fields": fields})
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 42, 73, 100, 2026])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--out", type=Path,
                        default=Path("docs/diag_road_min_distance_6y_5seeds.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arm_name = "OpexAI[decision_log=1]"
    arms = build_arms([arm_name])
    cfg = make_cfg(1970)

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=3,
        result_processor=keep,
        experiments=[
            {"seed": seed, "days": 365 * args.years, "openttd_config": cfg,
             "ais": (arms[arm_name],), "bench_run": [arm_name, seed, 0]}
            for seed in args.seeds
        ],
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    by_run = {}
    for row in rows:
        key = tuple(row["run"])
        by_run.setdefault(key, []).append(row)

    reject_reasons = Counter()
    per_seed_short = Counter()
    per_seed_long = Counter()
    per_seed_kept = Counter()
    errors = []
    FAIL_MARKERS = ("Your script made an error", "The script died unexpectedly")

    for key, series in by_run.items():
        _arm, seed, _rep = key
        series.sort(key=lambda r: r["date"])
        output = series[-1].get("openttd_output") if series else None
        for marker in FAIL_MARKERS:
            if marker in (output or ""):
                errors.append({"seed": seed, "marker": marker})
        for ev in parse_opex_decisions(output):
            f = ev["fields"]
            if ev["kind"] == "VIVIER_GEN" and f.get("mode") == "road":
                per_seed_kept[seed] += int(f["kept"])
            elif ev["kind"] == "VIVIER_REJECT":
                reason = f["reason"]
                n = int(f["n"])
                reject_reasons[reason] += n
                if reason == "road_distance_short":
                    per_seed_short[seed] += n
                elif reason == "road_distance_long":
                    per_seed_long[seed] += n

    total_short = reject_reasons.get("road_distance_short", 0)
    total_long = reject_reasons.get("road_distance_long", 0)
    total_kept = sum(per_seed_kept.values())

    def per_seed_table(counter):
        return {seed: counter.get(seed, 0) for seed in args.seeds}

    payload = {
        "purpose": "C43/E3 famille 2 : ROAD_MIN_DISTANCE (=5) / ROAD_MAX_DISTANCE (=25), "
                   "comptes bruts via VIVIER_REJECT",
        "caveat": "Pas de ratio contre produced/kept -- meme piege de denominateur que "
                  "road_town_rejected (les rejets arrivent avant le pairsInBand++ de leur "
                  "propre boucle).",
        "seeds": args.seeds, "years": args.years, "arm": arm_name,
        "errors": errors,
        "total_kept": total_kept,
        "reject_reason_counts": dict(reject_reasons),
        "road_min_distance": {
            "constant": 5, "n_rejected_total": total_short,
            "per_seed": per_seed_table(per_seed_short),
        },
        "road_max_distance": {
            "constant": 25, "n_rejected_total": total_long,
            "per_seed": per_seed_table(per_seed_long),
        },
    }
    import json
    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    print(f"total_kept={total_kept}")
    print("reject_reason_counts:", dict(reject_reasons))
    print("ROAD_MIN_DISTANCE (short) n_rejected_total:", total_short, "per_seed:", dict(per_seed_short))
    print("ROAD_MAX_DISTANCE (long) n_rejected_total:", total_long, "per_seed:", dict(per_seed_long))
    print("errors:", errors)
    print("out", args.out)


if __name__ == "__main__":
    main()
