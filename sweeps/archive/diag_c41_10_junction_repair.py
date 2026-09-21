"""C41.10 : verifie que la reparation transactionnelle de raccord agit sur le seul cas connu
(graine 7, ligne 18, vehicule 115, docs/taches.md C41.9) et n'agit PAS sur les 24 autres pertes
sans coupure locale. Memes graines que le diagnostic C41.9
(results/diag_c41_rail_lost_connectivity_6y_5seeds.json) pour reproduire le meme cas :
[42, 100, 7, 999, 12345], 6 ans.

Arm : OpexAI[c41_rail_lost_connectivity_probe=1,c41_rail_lost_junction_repair=1] -- la sonde
donne les six points par perte (a/b/a2/b2/depot/depot2), la reparation son propre panneau
C41_RAIL_JUNCTION_ARM/C41_RAIL_JUNCTION_REPAIR (code par point : -3 illisible, -2 ambigu/rien a
faire, 0 test refuse, 1 pose+connexion confirmees, 2 pose acceptee mais toujours deconnecte).
"""
import argparse
import json
import re
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
        y, mo, d, kind, rest = m2.groups()
        fields = {}
        for token in rest.split():
            if "=" in token:
                key, _, value = token.partition("=")
                fields[key] = value
        events.append({"date": f"{y}-{mo}-{d}", "kind": kind, "fields": fields})
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--out", type=Path,
                        default=Path("results/diag_c41_10_junction_repair_6y_5seeds.json"))
    parser.add_argument("--checkpoint", type=Path,
                        help="recompose le rapport depuis un checkpoint JSONL deja termine")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    arm_name = "OpexAI[c41_rail_lost_connectivity_probe=1,c41_rail_lost_junction_repair=1]"
    if args.checkpoint is None:
        bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
        if bench_v2.CHECKPOINT_PATH.exists():
            bench_v2.CHECKPOINT_PATH.unlink()
        enable_savegame_cleanup()
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
    else:
        with args.checkpoint.open() as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        rows = [row for row in rows if row["run"][1] in args.seeds]
        expected_rows = args.years * 12
        by_seed = {}
        for row in rows:
            by_seed.setdefault(row["run"][1], 0)
            by_seed[row["run"][1]] += 1
        incomplete = [seed for seed in args.seeds if by_seed.get(seed, 0) != expected_rows]
        if incomplete:
            raise ValueError("checkpoint incomplet pour les graines: " + ", ".join(map(str, incomplete)))

    by_run = {}
    for row in rows:
        key = tuple(row["run"])
        by_run.setdefault(key, []).append(row)

    connectivity = []
    arms_events = []
    repairs = []
    errors = []
    FAIL_MARKERS = ("Your script made an error", "The script died unexpectedly")

    for key, series in by_run.items():
        _arm, seed, _rep = key
        series.sort(key=lambda r: r["date"])
        # openttdlab attache le MEME openttd_output complet (capture unique du sous-processus)
        # a chaque ligne de checkpoint mensuel d'une meme partie -- verifie empiriquement le
        # 2026-09-08 (longueur identique sur les 72 lignes d'une partie de 6 ans). Le lire une
        # fois par (graine, arm), jamais par ligne, sous peine de compter chaque evenement une
        # fois par mois restant (bug trouve et corrige dans ce script avant tout autre calcul).
        output = series[-1].get("openttd_output") or "" if series else ""
        for marker in FAIL_MARKERS:
            if marker in output:
                errors.append({"seed": seed, "marker": marker})
        for ev in parse_opex_decisions(output):
            f = dict(ev["fields"])
            f["seed"] = seed
            f["date"] = ev["date"]
            if ev["kind"] == "C41_RAIL_LOST_CONNECTIVITY":
                connectivity.append(f)
            elif ev["kind"] == "C41_RAIL_JUNCTION_ARM":
                arms_events.append(f)
            elif ev["kind"] == "C41_RAIL_JUNCTION_REPAIR":
                repairs.append(f)

    def has_missing_link(rec):
        for pfx in ("a", "b", "a2", "b2", "depot", "depot2"):
            branches = int(rec.get(pfx + "_branches", 0))
            links = int(rec.get(pfx + "_links", -1))
            if branches > 0 and links == 0:
                return True
        return False

    missing_link_events = [r for r in connectivity if has_missing_link(r)]

    payload = {
        "seeds": args.seeds, "years": args.years, "arm": arm_name,
        "n_connectivity_events": len(connectivity),
        "n_missing_link_events": len(missing_link_events),
        "n_junction_arms": len(arms_events),
        "n_junction_repairs": len(repairs),
        "errors": errors,
        "missing_link_events": missing_link_events,
        "arm_events": arms_events,
        "repair_events": repairs,
    }
    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    print(f"n_connectivity_events={len(connectivity)} n_missing_link_events={len(missing_link_events)}")
    print(f"n_junction_arms={len(arms_events)} n_junction_repairs={len(repairs)}")
    print("errors:", errors)
    print("missing_link_events:", missing_link_events)
    print("repair_events:", repairs)
    print("out", args.out)


if __name__ == "__main__":
    main()
