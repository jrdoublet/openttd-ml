"""Diagnostic C49 etape 1 : causes prochaines des projets non batis, par annee.

La sonde est passive : elle ne modifie ni classement, ni refus, ni construction. Ce script ne
doit etre execute qu'apres validation du probe dans OpenTTD ; --selftest est pur Python.
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

ARM = "OpexAI[c49_scarcity_ledger=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C49_SCARCITY\s*(.*)")
RESOURCES = ("cash", "vehicles", "site", "decision")


def parse_fields(fields):
    return dict(token.split("=", 1) for token in fields.split() if "=" in token)


def parse_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def counts_and_shares(entry):
    counts = {resource: int(entry.get(resource, 0)) for resource in RESOURCES}
    denominator = sum(counts.values())
    return counts, {resource: ratio(counts[resource], denominator) for resource in RESOURCES}


def choose_regime(counts, previous):
    """Argmax annuel ; une egalite conserve exactement le regime precedent."""
    largest = max(counts.values())
    leaders = [resource for resource in RESOURCES if counts[resource] == largest]
    return leaders[0] if len(leaders) == 1 else previous


def build_metrics(events):
    """Construit les axes annuels et cumules en sommant toujours avant de diviser."""
    annual = {}
    for event in events:
        if event.get("phase") != "annual" or "year" not in event:
            continue
        year = int(event["year"])
        entry = annual.setdefault(year, {"passes": 0, "none": 0, "event_count": 0,
                                         **{key: 0 for key in RESOURCES}, "regime": "cash"})
        entry["event_count"] += 1
        entry["passes"] += int(event.get("passes", 0))
        entry["none"] += int(event.get("none", 0))
        for resource in RESOURCES:
            entry[resource] += int(event.get(resource, 0))
        entry["regime"] = event.get("regime", entry["regime"])

    by_year = []
    cumulative = {"passes": 0, "none": 0, **{key: 0 for key in RESOURCES}}
    regimes = []
    previous_regime = "cash"
    for year in sorted(annual):
        entry = annual[year]
        counts, shares = counts_and_shares(entry)
        cumulative["passes"] += entry["passes"]
        cumulative["none"] += entry["none"]
        for resource in RESOURCES:
            cumulative[resource] += counts[resource]
        # Une graine porte le regime publie par l'IA. Pour le cumul multi-graines, il faut le
        # recalculer sur les numerateurs agreges, jamais retenir le dernier log vu.
        regime = entry["regime"] if entry["event_count"] == 1 else choose_regime(counts, previous_regime)
        previous_regime = regime
        regimes.append(regime)
        by_year.append({"year": year, "passes": entry["passes"], "none": entry["none"],
                        "counts": counts, "shares": shares, "regime": regime})
    cumulative_counts, cumulative_shares = counts_and_shares(cumulative)
    changes = sum(left != right for left, right in zip(regimes, regimes[1:]))
    return {
        "by_year": by_year,
        "cumulative": {"passes": cumulative["passes"], "none": cumulative["none"],
                       "counts": cumulative_counts, "shares": cumulative_shares},
        "regime_change_count": changes,
        "regime_changed": changes > 0,
    }


def run_selftest():
    """Deux annees : quatre ressources, none, changement de regime et hysteresis sur egalite."""
    changing = "\n".join((
        "OPEX 1971-1-1 C49_SCARCITY phase=annual year=1971 passes=8 cash=4 vehicles=1 site=1 decision=1 none=1 regime=cash",
        "OPEX 1972-1-1 C49_SCARCITY phase=annual year=1972 passes=8 cash=1 vehicles=4 site=2 decision=1 none=1 regime=vehicles",
    ))
    tied = "\n".join((
        "OPEX 1971-1-1 C49_SCARCITY phase=annual year=1971 passes=8 cash=4 vehicles=1 site=1 decision=1 none=1 regime=cash",
        "OPEX 1972-1-1 C49_SCARCITY phase=annual year=1972 passes=10 cash=4 vehicles=4 site=1 decision=1 none=0 regime=cash",
    ))
    changed = build_metrics(parse_events(changing))
    retained = build_metrics(parse_events(tied))
    assert len(changed["by_year"]) == 2
    assert changed["by_year"][0]["counts"] == {"cash": 4, "vehicles": 1, "site": 1, "decision": 1}
    assert changed["by_year"][0]["none"] == 1
    assert changed["by_year"][1]["regime"] == "vehicles"
    assert changed["regime_change_count"] == 1
    assert retained["by_year"][1]["regime"] == "cash"
    assert retained["regime_change_count"] == 0
    assert choose_regime({"cash": 4, "vehicles": 4, "site": 1, "decision": 1}, "cash") == "cash"
    print("selftest passed: 2 years; resources=cash,vehicles,site,decision,none; regime change=cash->vehicles; tie retained=cash")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[100, 12345, 42, 7, 999])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / "diag_c49_scarcity_ledger_6y_5seeds.json"
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
    per_seed, all_events = [], []
    for record in summary:
        # Une seule analyse du stdout par graine : ne jamais reparcourir cette sortie pour un total.
        events = parse_events(record.get("openttd_output", ""))
        all_events.extend(events)
        metrics = build_metrics(events)
        per_seed.append({"seed": record["seed"], "run_ok": record["run_ok"], "metrics": metrics})
    failed = [{key: value for key, value in record.items() if key != "openttd_output"}
              for record in summary if not record["run_ok"]]
    seeds_with_regime_change = sum(item["metrics"]["regime_changed"] for item in per_seed)
    payload = {
        "years": args.years, "seeds": args.seeds, "arm": ARM,
        "per_seed": per_seed, "cumulative": build_metrics(all_events),
        "seeds_with_regime_change": seeds_with_regime_change,
        "failed_runs": failed, "failed_run_count": len(failed),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "regime_changes", seeds_with_regime_change, "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
