"""Diagnostic C41.47 : libérer _railSearch dès le premier blocage trésorerie (voir
docs/04_arbitrage_rail_search.md §C41.47). Mesure le délai élection→construction rail
(PROJECT_CHOSEN mode=rail → RAIL_BUILD) et le nombre de RAIL_EXPAND, avec et sans le correctif,
appariés par graine. Nécessite decision_log=1 pour PROJECT_CHOSEN/RAIL_BUILD/RAIL_EXPAND.
"""
import argparse
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, keep, summarise, write_json_atomically,
)
import bench_v2

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

ARMS = {
    "control": "OpexAI[decision_log=1,c41_rail_cash_release=0]",
    "treatment": "OpexAI[decision_log=1,c41_rail_cash_release=1]",
}
OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) (\S+)\s*(.*)")


def parse_fields(fields):
    out = {}
    for token in fields.split():
        if "=" in token:
            key, _, value = token.partition("=")
            out[key] = value
    return out


def day_index(year, month, day):
    return int(year) * 365 + (int(month) - 1) * 30 + int(day)


def election_to_build_delays(output):
    """Pour chaque ligne rail construite, delai (jours approx) depuis son PROJECT_CHOSEN
    mode=rail le plus recent au moment du RAIL_BUILD. Pas d'identifiant partage entre
    PROJECT_CHOSEN et RAIL_BUILD (src/dst peuvent differer si le join a change) : on prend le
    dernier PROJECT_CHOSEN mode=rail vu avant chaque RAIL_BUILD, ce qui borne le delai par
    au-dessus quand plusieurs candidats rail sont en file (accepte, cf. analyse manuelle
    equivalente sur diag_1v1_shared_timeline_2y_seed42.json).
    """
    delays = []
    last_chosen_day = None
    cash_releases = 0
    rail_expands = 0
    rail_builds = 0
    for line in (output or "").splitlines():
        # search(), pas match() : chaque ligne porte un prefixe horodate/dbg avant "OPEX ...".
        m = OPEX_RE.search(line)
        if not m:
            continue
        year, month, day, kind, fields = m.groups()
        d = day_index(year, month, day)
        f = parse_fields(fields)
        if kind == "PROJECT_CHOSEN" and f.get("mode") == "rail":
            last_chosen_day = d
        elif kind == "RAIL_BUILD":
            rail_builds += 1
            if last_chosen_day is not None:
                delays.append(d - last_chosen_day)
                last_chosen_day = None
        elif kind == "RAIL_EXPAND":
            rail_expands += 1
        elif kind == "C41_RAIL_CASH_RELEASE":
            cash_releases += 1
    return {"delays": delays, "rail_builds": rail_builds, "rail_expands": rail_expands,
            "cash_releases": cash_releases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / f"diag_c41_47_rail_cash_release_{args.years}y_{len(args.seeds)}seeds.json"
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms(list(ARMS.values())), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    label_by_arm = {v: k for k, v in ARMS.items()}
    for record in summary:
        arm = record.get("arm")
        record["c41_47_label"] = label_by_arm.get(arm, arm)
        stats = election_to_build_delays(record.get("openttd_output", ""))
        record["c41_47_delays"] = stats["delays"]
        record["c41_47_rail_builds"] = stats["rail_builds"]
        record["c41_47_rail_expands"] = stats["rail_expands"]
        record["c41_47_cash_releases"] = stats["cash_releases"]
        record["c41_47_delay_mean"] = (sum(stats["delays"]) / len(stats["delays"])) if stats["delays"] else None
    failed = [record for record in summary if not record["run_ok"]]
    write_json_atomically(out, {"years": args.years, "seeds": args.seeds, "summary": summary, "failed_runs": failed})
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
