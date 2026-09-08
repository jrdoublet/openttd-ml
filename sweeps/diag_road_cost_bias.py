"""La route a-t-elle un biais de cout comme le rail (x1,7 corrige par P1/capital_calibration) ?
Jamais mesure -- aucune sonde equivalente a air_cost_probe n'existe pour la route.

Trouvaille : le chemin portefeuille (_tryBuildRoadProject, main.nut ~2570) journalise DEJA le
cout modele (PROJECT_CHOSEN mode=road ... cost=candidate.capital) et le cout reel
(ROAD_BUILD ... cost=result.cost, mesure par delta de solde bancaire dans OpexBuildRoadRoute,
main.nut:1259) -- sans jamais les comparer. Aucun nouveau code de jeu : appariement hors-ligne des
deux panneaux existants par (src, dst), sur le defaut courant avec decision_log=1 seul.
"""
import argparse
import re
import statistics
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
                        default=Path("docs/diag_road_cost_bias_6y_5seeds.json"))
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

    pairs = []
    for key, series in by_run.items():
        _arm, seed, _rep = key
        series.sort(key=lambda r: r["date"])
        pending_model = {}
        for row in series:
            for ev in parse_opex_decisions(row.get("openttd_output")):
                f = ev["fields"]
                if ev["kind"] == "PROJECT_CHOSEN" and f.get("mode") == "road":
                    k = (f["src"], f["dst"])
                    pending_model[k] = int(f["cost"])
                elif ev["kind"] == "ROAD_BUILD":
                    k = (f["src"], f["dst"])
                    if k in pending_model:
                        model = pending_model.pop(k)
                        real = int(f["cost"])
                        if model > 0:
                            pairs.append({"seed": seed, "src": f["src"], "dst": f["dst"],
                                          "model": model, "real": real,
                                          "ratio": real / float(model)})

    ratios = [p["ratio"] for p in pairs]
    payload = {
        "purpose": "Road capital model bias: real cost (bank delta) vs model estimate, "
                   "paired from existing PROJECT_CHOSEN/ROAD_BUILD telemetry, no new game code",
        "seeds": args.seeds, "years": args.years, "arm": arm_name,
        "n_pairs": len(pairs),
        "ratio_mean": statistics.mean(ratios) if ratios else None,
        "ratio_median": statistics.median(ratios) if ratios else None,
        "ratio_stdev": statistics.stdev(ratios) if len(ratios) > 1 else None,
        "ratio_min": min(ratios) if ratios else None,
        "ratio_max": max(ratios) if ratios else None,
        "pairs": pairs,
    }
    import json
    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
    print("n_pairs", len(pairs))
    print("ratio_mean", payload["ratio_mean"], "median", payload["ratio_median"],
          "stdev", payload["ratio_stdev"], "min", payload["ratio_min"], "max", payload["ratio_max"])
    print("out", args.out)


if __name__ == "__main__":
    main()
