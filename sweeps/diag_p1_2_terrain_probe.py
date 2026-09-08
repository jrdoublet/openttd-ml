"""P1.2 : la sonde de terrain (scan quasi-direct avant pathfinding) correle-t-elle avec l'ecart
devis/modele (P1_1_QUOTE) mieux que la seule distance ?

Etape 1+2 du protocole ecrit dans docs/taches.md : mesurer le cout opcodes du scan, verifier la
correlation, AVANT tout branchement en production. `rail_prequote=1` (P1.1) reste un contrôle
experimental rejete -- ce script le reutilise UNIQUEMENT comme harnais de mesure pour produire les
paires (P1_1_QUOTE, P1_2_TERRAIN) sur les memes candidats, jamais comme une reprise de son adoption.

Necessite -d script=4 pour capturer les panneaux OpexDecide (AILog.Info) dans openttd_output.
"""
import argparse
import json
import re
import statistics
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup, keep, make_cfg,
)
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
        _year, _month, _day, kind, rest = m2.groups()
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
                        default=Path("results/diag_p1_2_terrain_probe_6y_5seeds.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arm_name = "OpexAI[rail_prequote=1,rail_terrain_probe=1,decision_log=1]"
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

    quotes = {}   # (seed, src, dst) -> {model, quoted}
    terrain = {}  # (seed, src, dst) -> {distance, complex_segments, tiles, ops}
    scan_ops = []
    # Cout TOTAL d'une passe de prequote (jusqu'a RAIL_PREQUOTE_MAX_CANDIDATES=2 candidats),
    # tel que publie par P1_1_QUOTE_SUMMARY -- pas une soustraction fragile de champs cumules.
    quote_pass_totals = []
    quote_pass_attempted = []

    for key, series in by_run.items():
        _arm, seed, _rep = key
        series.sort(key=lambda r: r["date"])
        for row in series:
            events = parse_opex_decisions(row.get("openttd_output"))
            for ev in events:
                f = ev["fields"]
                if ev["kind"] == "P1_1_QUOTE":
                    k = (seed, f["src"], f["dst"])
                    quotes[k] = {"model": int(f["model"]), "quoted": int(f["quoted"])}
                elif ev["kind"] == "P1_1_QUOTE_SUMMARY":
                    quote_pass_totals.append(int(f["ops"]))
                    quote_pass_attempted.append(int(f["attempted"]))
                elif ev["kind"] == "P1_2_TERRAIN":
                    k = (seed, f["src"], f["dst"])
                    terrain[k] = {
                        "distance": int(f["distance"]),
                        "tiles": int(f["tiles"]),
                        "complex_tiles": int(f["complex_tiles"]),
                        "complex_segments": int(f["complex_segments"]),
                        "water_tiles": int(f["water_tiles"]),
                        "slope_tiles": int(f["slope_tiles"]),
                    }
                    scan_ops.append(int(f["ops"]))

    paired = []
    for k, t in terrain.items():
        if k not in quotes:
            continue
        q = quotes[k]
        if q["model"] <= 0:
            continue
        ratio = q["quoted"] / float(q["model"])
        paired.append({
            "seed": k[0], "src": k[1], "dst": k[2],
            "distance": t["distance"], "complex_segments": t["complex_segments"],
            "complex_tiles": t["complex_tiles"], "water_tiles": t["water_tiles"],
            "slope_tiles": t["slope_tiles"], "model": q["model"], "quoted": q["quoted"],
            "ratio": ratio,
        })

    def pearson(xs, ys):
        n = len(xs)
        if n < 2:
            return None
        mx, my = statistics.mean(xs), statistics.mean(ys)
        sx = statistics.pstdev(xs)
        sy = statistics.pstdev(ys)
        if sx == 0 or sy == 0:
            return None
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
        return cov / (sx * sy)

    ratios = [p["ratio"] for p in paired]
    corr_segments = pearson([p["complex_segments"] for p in paired], ratios)
    corr_distance = pearson([p["distance"] for p in paired], ratios)
    corr_watertiles = pearson([p["water_tiles"] for p in paired], ratios)

    payload = {
        "purpose": "P1.2 protocol steps 1+2: scan opcode cost, correlation with devis/model gap",
        "seeds": args.seeds, "years": args.years, "arm": arm_name,
        "n_terrain_events": len(terrain), "n_quote_events": len(quotes),
        "n_paired": len(paired),
        "scan_opcodes": {
            "n": len(scan_ops), "mean": statistics.mean(scan_ops) if scan_ops else None,
            "max": max(scan_ops) if scan_ops else None,
        },
        "quote_pass_total_opcodes": {
            "n": len(quote_pass_totals),
            "mean": statistics.mean(quote_pass_totals) if quote_pass_totals else None,
            "mean_attempted": (statistics.mean(quote_pass_attempted)
                               if quote_pass_attempted else None),
        },
        "correlation_complex_segments_vs_ratio": corr_segments,
        "correlation_distance_vs_ratio": corr_distance,
        "correlation_water_tiles_vs_ratio": corr_watertiles,
        "paired": paired,
    }
    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
    print("n_paired", len(paired))
    print("scan_opcodes_mean", payload["scan_opcodes"]["mean"])
    print("quote_pass_total_opcodes_mean", payload["quote_pass_total_opcodes"]["mean"],
          "for mean_attempted=", payload["quote_pass_total_opcodes"]["mean_attempted"])
    print("corr(complex_segments, ratio)", corr_segments)
    print("corr(distance, ratio)", corr_distance)
    print("corr(water_tiles, ratio)", corr_watertiles)
    print("out", args.out)


if __name__ == "__main__":
    main()
