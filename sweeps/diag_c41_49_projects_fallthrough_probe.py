"""Diagnostic C41.49 (etape 0, reformule 2026-09-10) : correle, frontiere par frontiere, la sonde
C41.48 (une alternative financable existe-t-elle a la frontiere de tranche segmentee ?) avec la
nouvelle sonde passive dans _tryBuildProjects (le fallthrough du portefeuille essaie-t-il/batit-il
deja un candidat non-rail pendant cette meme passe ?). Voir docs/04_arbitrage_rail_search.md
§C41.49 pour le contrat. Ne coupe rien, n'ecrit aucune regle de decision -- seulement une mesure.
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

ARM = "OpexAI[c41_rail_domination_probe=1,c41_projects_fallthrough_probe=1]"
EVENT_RE = re.compile(
    r"OPEX \d+-\d+-\d+ (C41_RAIL_DOMINATION_PROBE|C41_PROJECTS_FALLTHROUGH_PROBE)\s*(.*)"
)


def parse_fields(fields):
    out = {}
    for token in fields.split():
        if "=" in token:
            key, _, value = token.partition("=")
            out[key] = value
    return out


def correlate(output):
    """Associe chaque frontiere C41.48 (dans l'ordre chronologique du flux de log, qui suit
    l'ordre d'appel puisque _continueRailSearch() -- donc le log frontiere -- s'execute
    TOUJOURS avant le dispatch de la tache "projects" dans la meme passe de _runNextTask,
    main.nut. Au plus une paire entry/exit du fallthrough peut donc s'intercaler avant la
    frontiere suivante, et elle appartient forcement a CETTE passe. """
    results = []
    pending = None

    def flush():
        if pending is not None:
            results.append(pending)

    for tag, fields_text in EVENT_RE.findall(output or ""):
        fields = parse_fields(fields_text)
        if tag == "C41_RAIL_DOMINATION_PROBE":
            flush()
            pending = {"frontier": fields, "entry": False, "exit": None}
        else:  # C41_PROJECTS_FALLTHROUGH_PROBE
            if pending is None:
                continue
            if fields.get("phase") == "entry":
                pending["entry"] = True
            elif fields.get("phase") == "exit":
                pending["exit"] = fields
    flush()
    return results


def classify(result):
    frontier = result["frontier"]
    has_alt = int(frontier.get("best_rank", -1)) >= 0
    if not result["entry"]:
        bucket = "no_projects_turn"
    elif result["exit"] is None:
        # "projects" a ete dispatchee (entry loggee) mais le garde d'entree de la boucle
        # (this._projects == null ou best.len() == 0, ou PORTFOLIO_DYNAMIC_BATCH -- eteint ici)
        # a saute directement par-dessus le balayage : aucune tentative n'a ete possible.
        bucket = "entered_no_scan"
    else:
        attempted = int(result["exit"].get("attempted", 0))
        built = int(result["exit"].get("built", 0))
        if built > 0:
            bucket = "captured_built"
        elif attempted > 0:
            bucket = "attempted_not_built"
        else:
            bucket = "ran_no_nonrail_candidate"
    return has_alt, bucket


def summarise_events(output):
    correlated = correlate(output)
    n = len(correlated)
    buckets = {}
    buckets_with_alt = {}
    n_with_alt = 0
    for result in correlated:
        has_alt, bucket = classify(result)
        buckets[bucket] = buckets.get(bucket, 0) + 1
        if has_alt:
            n_with_alt += 1
            buckets_with_alt[bucket] = buckets_with_alt.get(bucket, 0) + 1

    exits = [r["exit"] for r in correlated if r["exit"] is not None]
    attempted_values = [int(e.get("attempted", 0)) for e in exits]
    built_values = [int(e.get("built", 0)) for e in exits]

    stats = {
        "frontier_events": n,
        "frontier_events_with_alt": n_with_alt,
        "projects_turns_same_pass": len(exits) + sum(1 for r in correlated if r["exit"] is None and r["entry"]),
        "projects_turns_with_scan": len(exits),
        "nonrail_attempted_sum": sum(attempted_values),
        "nonrail_built_sum": sum(built_values),
    }
    for bucket, count in buckets.items():
        stats[f"bucket_all_{bucket}"] = count
    for bucket, count in buckets_with_alt.items():
        stats[f"bucket_with_alt_{bucket}"] = count
    return stats, correlated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--keep-events", action="store_true",
                         help="Conserver la correlation complete dans le JSON (volumineux).")
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / f"diag_c41_49_projects_fallthrough_probe_{args.years}y_{len(args.seeds)}seeds.json"
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
        stats, correlated = summarise_events(record.get("openttd_output", ""))
        for key, value in stats.items():
            record[f"c41_49_{key}"] = value
        if args.keep_events:
            record["c41_49_correlated"] = correlated
    failed = [record for record in summary if not record["run_ok"]]
    write_json_atomically(out, {"years": args.years, "seeds": args.seeds, "summary": summary, "failed_runs": failed})
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
