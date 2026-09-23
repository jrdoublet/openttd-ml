"""Diagnostic C69 etape 1 : sonde passive P/max(C, F*tau), aucune decision changee.

Capture les lignes `C69_BOTTLENECK` (phases build, c3_check, annual_calibration) et calcule les
criteres C2 (exposition), C3 (ensemble ou ordre), C4 (ampleur) et C5 (calibration par mode) de
docs/11_goulot_decision.md §10. C1 se lit dans la trajectoire de K_dec par annee, a rapprocher
du registre C49. --selftest est pur Python.
"""
import argparse
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

ARM = "OpexAI[probe_portfolio=1]"
EVENT_RE = re.compile(r"OPEX (\d+)-\d+-\d+ C69_BOTTLENECK\s*(.*)")
C49_RE = re.compile(r"OPEX \d+-\d+-\d+ C49_SCARCITY\s*(.*)")
# Fenetre C2-C4 : annees 2 a 6 (la premiere annee est celle de l'amorcage, F = 0).
FIRST_YEAR_EXCLUDED = 1


def parse_fields(fields):
    return dict(token.split("=", 1) for token in fields.split() if "=" in token)


def parse_events(output):
    events = []
    for year, fields in EVENT_RE.findall(output or ""):
        event = parse_fields(fields)
        event["_log_year"] = int(year)
        events.append(event)
    return events


def parse_c49(output):
    return [parse_fields(fields) for fields in C49_RE.findall(output or "")]


def c1_years(events, c49_events):
    """C1 : annee ou K_dec depasse le capital median des lignes aeriennes elues, contre annee ou
    `cash` passe sous `decision` dans le registre C49. `decision` = tentees + non tentees."""
    builds = [e for e in events if e.get("phase") == "build"]
    kdec, air_c = {}, {}
    for e in builds:
        year = e["_log_year"]
        kdec.setdefault(year, []).append(to_float(e.get("K_dec")))
        if e.get("actual_mode") == "air":
            air_c.setdefault(year, []).append(to_float(e.get("actual_C")))
    all_air = [c for values in air_c.values() for c in values]
    air_median = median_or_none(all_air)
    kdec_year = None
    if air_median is not None:
        for year in sorted(kdec):
            if (median_or_none(kdec[year]) or 0) > air_median:
                kdec_year = year
                break
    c49_year = None
    for e in sorted((e for e in c49_events if e.get("phase") == "annual"), key=lambda e: int(e["year"])):
        decision = int(e.get("decision_attempted", 0)) + int(e.get("decision_unattempted", 0))
        if int(e.get("cash", 0)) < decision:
            # Le registre annuel est publie au 1er janvier de l'annee suivante (year = annee close).
            c49_year = int(e["year"])
            break
    gap = abs(kdec_year - c49_year) if kdec_year is not None and c49_year is not None else None
    return {"air_capital_median": air_median, "kdec_crosses_air_year": kdec_year,
            "c49_cash_below_decision_year": c49_year, "c1_gap_years": gap}


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def median_or_none(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def build_metrics(events):
    builds = [e for e in events if e.get("phase") == "build"]
    checks = [e for e in events if e.get("phase") == "c3_check"]
    calibration = [e for e in events if e.get("phase") == "annual_calibration"]
    start = min((e["_log_year"] for e in builds), default=None)
    window = [e for e in builds if start is not None and e["_log_year"] > start + FIRST_YEAR_EXCLUDED - 1]

    diff = [e for e in window if e.get("diff") == "1"]
    exposure = len(diff) / len(window) if window else None

    diff_passes = {e.get("pass") for e in diff}
    window_checks = [e for e in checks if e.get("pass") in diff_passes]
    built_anyway = sum(e.get("built_next") == "1" for e in window_checks)
    built_share = built_anyway / len(window_checks) if window_checks else None

    ratios = []
    for e in diff:
        actual_p, c69_p = to_float(e.get("actual_P")), to_float(e.get("c69_P"))
        if actual_p and c69_p is not None and actual_p > 0:
            ratios.append(c69_p / actual_p)

    kdec_by_year = {}
    for e in builds:
        kdec_by_year.setdefault(e["_log_year"], []).append(to_float(e.get("K_dec")))
    kdec_by_year = {year: median_or_none(values) for year, values in sorted(kdec_by_year.items())}
    f_by_year = {}
    for e in builds:
        f_by_year.setdefault(e["_log_year"], []).append(to_float(e.get("F")))
    f_by_year = {year: median_or_none(values) for year, values in sorted(f_by_year.items())}

    by_mode = {}
    for e in calibration:
        by_mode.setdefault(e.get("mode"), []).append(to_float(e.get("med_real_pred_prof")))
    by_mode = {mode: median_or_none(values) for mode, values in by_mode.items()}
    positive = [value for value in by_mode.values() if value and value > 0]
    spread = max(positive) / min(positive) if len(positive) >= 2 else None

    first_diff_year = min((e["_log_year"] for e in diff), default=None)
    return {
        "build_passes": len(builds),
        "window_build_passes": len(window),
        "diff_passes": len(diff),
        "c2_exposure": exposure,
        "c3_checked": len(window_checks),
        "c3_built_anyway_share": built_share,
        "c4_median_p_ratio": median_or_none(ratios),
        "first_diff_year": first_diff_year,
        "f_median_by_year": f_by_year,
        "kdec_median_by_year": kdec_by_year,
        "c5_median_real_pred_prof_by_mode": by_mode,
        "c5_spread_max_over_min": spread,
    }


def run_selftest():
    output = "\n".join([
        "OPEX 1970-3-1 C69_BOTTLENECK phase=build pass=1 year=1970 F=0 F_veh=0 tau=0 K_dec=0 actual_mode=road actual_P=100 actual_C=10 c69_mode=road c69_P=100 c69_C=10 c69_rank_in_actual=0 diff=0",
        "OPEX 1971-3-1 C69_BOTTLENECK phase=build pass=2 year=1971 F=100 F_veh=0 tau=30 K_dec=3000 actual_mode=road actual_P=100 actual_C=10 c69_mode=air c69_P=300 c69_C=50 c69_rank_in_actual=2 diff=1",
        "OPEX 1971-4-1 C69_BOTTLENECK phase=c3_check pass=2 built_next=1 passes_waited=1 target=air|1",
        "OPEX 1972-3-1 C69_BOTTLENECK phase=build pass=3 year=1972 F=200 F_veh=0 tau=30 K_dec=6000 actual_mode=road actual_P=100 actual_C=10 c69_mode=road c69_P=100 c69_C=10 c69_rank_in_actual=0 diff=0",
        "OPEX 1974-1-1 C69_BOTTLENECK phase=annual_calibration year=1974 profit_year=1973 mode=air n=4 n_prof=4 n_rev=4 med_real_pred_prof=1.0 med_real_pred_rev=1.0",
        "OPEX 1974-1-1 C69_BOTTLENECK phase=annual_calibration year=1974 profit_year=1973 mode=road n=4 n_prof=4 n_rev=4 med_real_pred_prof=0.5 med_real_pred_rev=1.0",
    ])
    metrics = build_metrics(parse_events(output))
    assert metrics["build_passes"] == 3 and metrics["window_build_passes"] == 2
    assert metrics["diff_passes"] == 1 and metrics["c2_exposure"] == 0.5
    assert metrics["c3_built_anyway_share"] == 1.0 and metrics["c4_median_p_ratio"] == 3.0
    assert metrics["first_diff_year"] == 1971 and metrics["c5_spread_max_over_min"] == 2.0
    print("selftest passed: parse, C2=0.5, C3=1.0, C4=3.0, C5=2.0")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[100, 12345, 42, 7, 999])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--starting-year", type=int, default=1970)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--arm", default=ARM, help="bras OpexAI[...] ; doit activer probe_portfolio")
    parser.add_argument("--extra-tags", nargs="*", default=[],
                        help="autres canaux OPEX a recopier dans --raw (ex. C39_PASS_CLOCK)")
    parser.add_argument("--grep", default=None, help="recopie dans --raw les lignes du journal contenant ce texte")
    parser.add_argument("--raw", type=Path, default=None, help="Ecrit les lignes C69_BOTTLENECK brutes (jsonl)")
    parser.add_argument("--no-checkpoint", action="store_true",
                        help="checkpoint vers /dev/null : chaque ligne mensuelle recopie tout le journal, "
                             "soit plusieurs Go avec les sondes verbeuses (probe_events)")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--seeds non vide ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / "diag_c69_bottleneck_probe_6y_5seeds.json"
    bench_v2.CHECKPOINT_PATH = Path("/dev/null") if args.no_checkpoint else out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms([args.arm]), args.seeds, args.years, 1, args.starting_year),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    per_seed = []
    for record in summary:
        events = parse_events(record.get("openttd_output", ""))
        c49_events = parse_c49(record.get("openttd_output", ""))
        if args.raw:
            import json
            with open(args.raw, "a") as fh:
                for event in events:
                    fh.write(json.dumps({"seed": record["seed"], **event}) + "\n")
                if args.grep:
                    for text in (record.get("openttd_output", "") or "").splitlines():
                        if args.grep in text:
                            fh.write(json.dumps({"seed": record["seed"], "grep": text.strip()[-200:]}) + "\n")
                for tag in args.extra_tags:
                    tag_re = re.compile(r"OPEX ((\d+)-\d+-\d+) " + re.escape(tag) + r"\s*(.*)")
                    for date, year, fields in tag_re.findall(record.get("openttd_output", "")):
                        extra = parse_fields(fields)
                        fh.write(json.dumps({"seed": record["seed"], "tag": tag,
                                             "_log_year": int(year), "_log_date": date,
                                             **extra}) + "\n")
        per_seed.append({"seed": record["seed"], "run_ok": record["run_ok"],
                         "n_events": len(events), "metrics": build_metrics(events),
                         "c1": c1_years(events, c49_events),
                         "company_value": record.get("company_value"),
                         "profit_year": record.get("profit_year")})
    failed = [{key: value for key, value in record.items() if key != "openttd_output"}
              for record in summary if not record["run_ok"]]
    write_json_atomically(out, {"years": args.years, "seeds": args.seeds, "arm": args.arm,
                                "per_seed": per_seed, "failed_runs": failed,
                                "failed_run_count": len(failed)})
    print("failed", len(failed), "out", out)
    for item in per_seed:
        m = item["metrics"]
        print("seed", item["seed"], "events", item["n_events"], "builds", m["build_passes"],
              "C2", m["c2_exposure"], "C3", m["c3_built_anyway_share"], "C4", m["c4_median_p_ratio"],
              "first_diff", m["first_diff_year"], "C1", item["c1"])
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
