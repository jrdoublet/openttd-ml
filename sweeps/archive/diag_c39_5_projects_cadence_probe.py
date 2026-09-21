"""Diagnostic C39.5 : mesure passive de la cadence de dispatch de `projects`, de ses
abstentions et du delai de captation des projets finançables. Voir
docs/05_cadence_projects_rail_search.md. Ne compare aucune arm et ne change aucune decision.
"""
import argparse
import math
import re
import statistics
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

ARM = "OpexAI[c39_projects_cadence_probe=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C39_PROJECTS_CADENCE\s*(.*)")


def parse_fields(fields):
    out = {}
    for token in fields.split():
        if "=" in token:
            key, _, value = token.partition("=")
            out[key] = value
    return out


def parse_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def percentile90(values):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.9 * len(ordered)) - 1]


def distribution(values):
    values = [value for value in values if value != -1]
    if not values:
        return {"n": 0, "median": None, "p90": None, "max": None}
    return {
        "n": len(values),
        "median": statistics.median(values),
        "p90": percentile90(values),
        "max": max(values),
    }


def share(count, total):
    return count / total if total else None


def dispatch_summary(events):
    dispatches = [event for event in events if event.get("phase") == "dispatch"]
    d1 = {}
    for rail_search in (0, 1):
        subset = [event for event in dispatches if int(event.get("rail_search", 0)) == rail_search]
        d1[f"rail_search_{rail_search}"] = {
            "days_since_last": distribution([int(event.get("days_since_last", -1)) for event in subset]),
            "ticks_since_last": distribution([int(event.get("ticks_since_last", -1)) for event in subset]),
        }
    cycles = [int(event.get("cycles_since_last", -1)) for event in dispatches]
    usable_cycles = [value for value in cycles if value != -1]
    return {
        "dispatch_lines": len(dispatches),
        "d1": d1,
        "cycles_since_last": {
            "n": len(usable_cycles),
            "equals_1": sum(value == 1 for value in usable_cycles),
            "share_equals_1": share(sum(value == 1 for value in usable_cycles), len(usable_cycles)),
            "greater_than_1": sum(value > 1 for value in usable_cycles),
            "share_greater_than_1": share(sum(value > 1 for value in usable_cycles), len(usable_cycles)),
        },
        "d3": {
            "invalidated": share(sum(int(event.get("invalidated", 0)) == 1 for event in dispatches), len(dispatches)),
            # best_len == -1 : this._projects est null (aucun portefeuille construit).
            "best_len_missing": share(sum(int(event.get("best_len", -1)) == -1 for event in dispatches), len(dispatches)),
            # best_len == 0 : le portefeuille existe mais son vivier best est vide.
            "best_len_empty": share(sum(int(event.get("best_len", -1)) == 0 for event in dispatches), len(dispatches)),
            # <= 0 : les deux causes reunies, gardee pour rester comparable a la mesure deja publiee (55.3 %).
            "best_len_none_usable": share(sum(int(event.get("best_len", -1)) <= 0 for event in dispatches), len(dispatches)),
            "financeable_zero": share(sum(int(event.get("financeable", 0)) == 0 for event in dispatches), len(dispatches)),
        },
    }


def capture_summary(events, nonrail_only, rail_search):
    built = [event for event in events if event.get("phase") == "built"]
    if nonrail_only:
        built = [event for event in built if event.get("mode") != "rail"]
    if rail_search is not None:
        built = [event for event in built if int(event.get("rail_search", 0)) == rail_search]
    delays = [int(event.get("days_since_financeable", -1)) for event in built]
    unmarked = sum(delay == -1 for delay in delays)
    # C39.5b : days_since_top / turns_since_top isolent le chiffre decisif -- turns_since_top
    # proche de 1 veut dire "batie au premier tour utile" (delai = cadence uniquement) ; plus
    # grand, la cadence n'explique pas le delai (file par rang ou concurrence caisse).
    days_since_top = [int(event.get("days_since_top", -1)) for event in built]
    never_top = sum(delay == -1 for delay in days_since_top)
    turns_since_financeable = [int(event.get("turns_since_financeable", -1)) for event in built]
    turns_since_top = [int(event.get("turns_since_top", -1)) for event in built]
    return {
        "built_lines": len(built),
        "unmarked_built": unmarked,
        "unmarked_share": share(unmarked, len(built)),
        "days_since_financeable": distribution(delays),
        "days_since_top": distribution(days_since_top),
        "never_top_built": never_top,
        "never_top_share": share(never_top, len(built)),
        "turns_since_financeable": distribution(turns_since_financeable),
        "turns_since_top": distribution(turns_since_top),
    }


def event_summary(events):
    result = dispatch_summary(events)
    result["built_lines"] = sum(event.get("phase") == "built" for event in events)
    result["d2"] = {}
    for name, nonrail_only in (("all_modes", False), ("nonrail_only", True)):
        result["d2"][name] = {
            "all": capture_summary(events, nonrail_only, None),
            "rail_search_0": capture_summary(events, nonrail_only, 0),
            "rail_search_1": capture_summary(events, nonrail_only, 1),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[100, 12345, 42, 7, 999])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / f"diag_c39_5_projects_cadence_probe_{args.years}y_{len(args.seeds)}seeds.json"
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
    per_seed = []
    all_events = []
    for record in summary:
        events = parse_events(record.get("openttd_output", ""))
        all_events.extend(events)
        per_seed.append({"seed": record["seed"], "run_ok": record["run_ok"], "metrics": event_summary(events)})
    failed = [record for record in summary if not record["run_ok"]]
    payload = {
        "years": args.years,
        "seeds": args.seeds,
        "arm": ARM,
        "per_seed": per_seed,
        "cumulative": event_summary(all_events),
        "failed_runs": failed,
        "failed_run_count": len(failed),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
