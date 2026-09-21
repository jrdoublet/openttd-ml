"""Diagnostic C41.48 : sonde passive à chaque frontière de tranche du pathfinder rail segmenté
(voir docs/04_arbitrage_rail_search.md §C41.48). Ne coupe rien ; mesure si un futur test de
domination (C41.49) aurait seulement l'occasion de se déclencher, et sur combien de frontières.
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

ARM = "OpexAI[c41_rail_domination_probe=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C41_RAIL_DOMINATION_PROBE\s*(.*)")


def parse_fields(fields):
    out = {}
    for token in fields.split():
        if "=" in token:
            key, _, value = token.partition("=")
            out[key] = value
    return out


def summarise_events(output):
    events = [parse_fields(m) for m in EVENT_RE.findall(output or "")]
    n = len(events)
    with_alt = [e for e in events if int(e.get("best_rank", -1)) >= 0]
    n_with_alt = len(with_alt)
    # best_rank=0 & mode=rail & cout identique au capital du candidat en recherche : rang 0 EST
    # le candidat lui-meme (pas encore construit, donc toujours "financable" a ses propres yeux),
    # pas une vraie alternative concurrente. Determine si C41.49 aurait meme une comparaison a
    # faire, ou si l'"alternative" est souvent illusoire.
    self_ref = sum(
        1 for e in with_alt
        if e.get("best_mode") == "rail" and e.get("best_cost") == e.get("rail_capital")
    )
    stats = {
        "frontier_events": n,
        "events_with_financeable_alt": n_with_alt,
        "events_without_alt": n - n_with_alt,
        "events_alt_is_self": self_ref,
        "events_alt_is_other_project": n_with_alt - self_ref,
    }
    for field in ("spent", "remaining", "segments", "backtracks", "prefix_len", "dist_remaining"):
        values = [int(e[field]) for e in events if field in e]
        stats[f"{field}_mean"] = (sum(values) / len(values)) if values else None
    # Descriptif seulement (pas un verdict de domination -- C41.49) : ordre de grandeur du
    # candidat rail en cours contre la meilleure alternative financable, quand il y en a une.
    for field, source in (("rail_profit", events), ("rail_capital", events),
                          ("best_score", with_alt), ("best_cost", with_alt)):
        values = [float(e[field]) for e in source if field in e]
        stats[f"{field}_mean"] = (sum(values) / len(values)) if values else None
    return stats, events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--keep-events", action="store_true",
                         help="Conserver la liste complete des evenements dans le JSON (volumineux).")
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / f"diag_c41_48_rail_domination_probe_{args.years}y_{len(args.seeds)}seeds.json"
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms([ARM]), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    for record in summary:
        stats, events = summarise_events(record.get("openttd_output", ""))
        for key, value in stats.items():
            record[f"c41_48_{key}"] = value
        if args.keep_events:
            record["c41_48_events"] = events
    failed = [record for record in summary if not record["run_ok"]]
    write_json_atomically(out, {"years": args.years, "seeds": args.seeds, "summary": summary, "failed_runs": failed})
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
