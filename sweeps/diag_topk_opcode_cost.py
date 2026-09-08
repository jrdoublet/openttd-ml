"""C43/E3 item 2 (docs/taches.md) : isoler le cout pur en opcodes de la fenetre de selection
(champ sel_ops du panneau VIVIER, ajoute le 2026-09-08), independamment de son effet sur la valeur
economique -- pour tester l'hypothese que le cout de calcul d'une fenetre plus large mord sur le
budget d'opcodes qui irait sinon a la construction.

Compare project_top_k=32, le defaut 64, et project_top_k_dynamic=1 (86-101 sur la carte standard).
"""
import argparse
import re
import statistics
from collections import defaultdict
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
                        default=Path("docs/diag_topk_opcode_cost_6y_5seeds.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arm_names = [
        "OpexAI[project_top_k=32,decision_log=1]",
        "OpexAI[decision_log=1]",
        "OpexAI[project_top_k_dynamic=1,decision_log=1]",
    ]
    arms = build_arms(arm_names)
    cfg = make_cfg(1970)

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=3,
        result_processor=keep,
        experiments=[
            {"seed": seed, "days": 365 * args.years, "openttd_config": cfg,
             "ais": (arms[a],), "bench_run": [a, seed, 0]}
            for a in arm_names for seed in args.seeds
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

    # arm -> path -> list de {selected, sel_ops}
    by_arm_path = defaultdict(lambda: defaultdict(list))

    for key, series in by_run.items():
        arm, _seed, _rep = key
        series.sort(key=lambda r: r["date"])
        # C41.10 (docs/taches.md, 2026-09-08) : openttd_output est identique a chaque ligne de
        # checkpoint mensuel d'une meme partie -- une seule lecture par (graine, arm), derniere
        # ligne, sous peine de compter chaque evenement une fois par mois restant.
        output = series[-1].get("openttd_output") if series else None
        for ev in parse_opex_decisions(output):
            if ev["kind"] != "VIVIER":
                continue
            f = ev["fields"]
            by_arm_path[arm][f["path"]].append({
                "considered": int(f["considered"]),
                "selected": int(f["selected"]),
                "sel_ops": int(f["sel_ops"]),
            })

    summary = {}
    for arm, paths in by_arm_path.items():
        summary[arm] = {}
        for path, records in paths.items():
            ops = [r["sel_ops"] for r in records]
            selected = [r["selected"] for r in records]
            considered = [r["considered"] for r in records]
            ops_per_selected = [r["sel_ops"] / float(r["selected"]) for r in records if r["selected"] > 0]
            summary[arm][path] = {
                "n_calls": len(records),
                "mean_sel_ops": statistics.mean(ops) if ops else None,
                "median_sel_ops": statistics.median(ops) if ops else None,
                "mean_selected": statistics.mean(selected) if selected else None,
                "mean_considered": statistics.mean(considered) if considered else None,
                "mean_ops_per_selected": (statistics.mean(ops_per_selected)
                                         if ops_per_selected else None),
            }

    payload = {
        "purpose": "Isolate the pure opcode cost of the selection window size (VIVIER sel_ops), "
                   "independent of economic outcome",
        "seeds": args.seeds, "years": args.years, "arms": arm_names,
        "summary": summary,
    }
    import json
    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    for arm in arm_names:
        print(f"=== {arm} ===")
        for path, s in summary.get(arm, {}).items():
            print(f"  path={path}: n={s['n_calls']} mean_sel_ops={s['mean_sel_ops']:.0f} "
                  f"mean_selected={s['mean_selected']:.1f} mean_considered={s['mean_considered']:.1f} "
                  f"ops_per_selected={s['mean_ops_per_selected']:.1f}")
    print("out", args.out)


if __name__ == "__main__":
    main()
