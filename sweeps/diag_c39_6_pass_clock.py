"""Diagnostic C39.6 : repond aux deux questions ouvertes par le facteur ~15 mesure entre le cout
en opcodes d'une tranche A* rail (~146 k, C41.46) et le temps de jeu qu'une passe de
_runNextTask lui fait perdre (~3,6 j pendant une recherche rail contre ~0,74 j hors --
docs/05_cadence_projects_rail_search.md §4.3) : (1) les jours perdus sont-ils dans la tranche A*
elle-meme ou dans la tache de file jouee dans la MEME passe ? (2) si c'est la tache de file,
laquelle ? Purement observatoire : aucun dueCycle, aucune borne, aucune decision modifiee.
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

ARM = "OpexAI[c39_pass_clock_ledger=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C39_PASS_CLOCK\s*(.*)")
DAYS_PER_YEAR = 365
SUM_FIELDS = ("passes", "days", "ticks", "ops", "slice_days", "slice_ticks", "slice_ops")


def parse_fields(fields):
    out = {}
    for token in fields.split():
        if "=" in token:
            key, _, value = token.partition("=")
            out[key] = value
    return out


def parse_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def split_key(key):
    # cle = "<nom de tache>|slice" ou "<nom de tache>|noslice" (main.nut _runNextTaskWithSlackLedger).
    task, sep, slice_status = key.rpartition("|")
    if not sep:
        return key, "noslice"
    return task, slice_status


def aggregate_buckets(events):
    """Cumule les lignes annuelles par (tache, slice/noslice). Une meme cle peut apparaitre
    plusieurs fois (une ligne par annee de partie), il faut donc sommer, jamais ecraser."""
    buckets = {}
    for event in events:
        if event.get("phase") != "annual":
            continue
        task, slice_status = split_key(event.get("key", "idle|noslice"))
        entry = buckets.setdefault((task, slice_status),
            {field: 0 for field in SUM_FIELDS})
        for field in SUM_FIELDS:
            entry[field] += int(event.get(field, 0))
    return buckets


def aggregate_year_buckets(events):
    """Cumule les lignes annuelles par (annee, tache, slice/noslice)."""
    buckets = {}
    for event in events:
        if event.get("phase") != "annual" or "year" not in event:
            continue
        year = int(event["year"])
        task, slice_status = split_key(event.get("key", "idle|noslice"))
        entry = buckets.setdefault((year, task, slice_status),
            {field: 0 for field in SUM_FIELDS})
        for field in SUM_FIELDS:
            entry[field] += int(event.get(field, 0))
    return buckets


def per_pass(entry, field):
    return entry[field] / entry["passes"] if entry["passes"] else None


def sum_entries(entries):
    total = {field: 0 for field in SUM_FIELDS}
    for entry in entries:
        for field in SUM_FIELDS:
            total[field] += entry[field]
    return total


def by_year(year_buckets):
    rows = []
    years = sorted({year for year, _, _ in year_buckets})
    for year in years:
        sides = {}
        for status in ("slice", "noslice"):
            entry = sum_entries(entry for (entry_year, _, entry_status), entry in year_buckets.items()
                                if entry_year == year and entry_status == status)
            sides[status] = {
                "passes": entry["passes"], "days": entry["days"],
                "ticks": entry["ticks"], "ops": entry["ops"],
                "days_per_pass": per_pass(entry, "days"),
            }
        total = sum_entries(
            entry for (entry_year, _, _), entry in year_buckets.items() if entry_year == year)
        slice_dpp = sides["slice"]["days_per_pass"]
        noslice_dpp = sides["noslice"]["days_per_pass"]
        rows.append({
            "year": year,
            "passes": total["passes"], "days": total["days"],
            "ticks": total["ticks"], "ops": total["ops"],
            "slice": sides["slice"], "noslice": sides["noslice"],
            "slice_to_noslice_days_per_pass_ratio": (
                slice_dpp / noslice_dpp if slice_dpp is not None and noslice_dpp else None),
        })
    return rows


def by_year_task(year_buckets):
    rows = []
    pairs = {(year, task) for year, task, _ in year_buckets}
    for year, task in pairs:
        sides = {}
        for status in ("slice", "noslice"):
            entry = year_buckets.get((year, task, status),
                {field: 0 for field in SUM_FIELDS})
            sides[status] = {
                "passes": entry["passes"], "days": entry["days"], "ops": entry["ops"],
                "days_per_pass": per_pass(entry, "days"),
                "ops_per_pass": per_pass(entry, "ops"),
            }
        total = sum_entries(year_buckets.get((year, task, status),
            {field: 0 for field in SUM_FIELDS}) for status in ("slice", "noslice"))
        rows.append({
            "year": year, "task": task,
            "passes": total["passes"], "days": total["days"], "ops": total["ops"],
            "days_per_pass": per_pass(total, "days"),
            "ops_per_pass": per_pass(total, "ops"),
            "slice": sides["slice"], "noslice": sides["noslice"],
        })
    rows.sort(key=lambda row: (row["year"], -row["days"], row["task"]))
    return rows


def select_growth_years(year_buckets):
    """Ecarte une derniere annee inachevee : une annee complete couvre pres du maximum annuel."""
    coverage = {}
    for (year, _, _), entry in year_buckets.items():
        total = coverage.setdefault(year, {"days": 0, "ticks": 0})
        total["days"] += entry["days"]
        total["ticks"] += entry["ticks"]
    if not coverage:
        return None, None
    max_days = max(value["days"] for value in coverage.values())
    max_ticks = max(value["ticks"] for value in coverage.values())
    full_years = [year for year in sorted(coverage)
                  if (not max_days or coverage[year]["days"] >= 0.9 * max_days)
                  and (not max_ticks or coverage[year]["ticks"] >= 0.9 * max_ticks)]
    # If the data are too sparse for the coverage heuristic, retain observed endpoints.
    candidates = full_years or sorted(coverage)
    return candidates[0], candidates[-1]


def task_growth(year_buckets):
    from_year, to_year = select_growth_years(year_buckets)
    if from_year is None:
        return from_year, to_year, []
    tasks = {task for _, task, _ in year_buckets}
    rows = []
    for task in tasks:
        first = sum_entries(year_buckets.get((from_year, task, status),
            {field: 0 for field in SUM_FIELDS}) for status in ("slice", "noslice"))
        last = sum_entries(year_buckets.get((to_year, task, status),
            {field: 0 for field in SUM_FIELDS}) for status in ("slice", "noslice"))
        first_dpp, last_dpp = per_pass(first, "days"), per_pass(last, "days")
        first_opp, last_opp = per_pass(first, "ops"), per_pass(last, "ops")
        # A task absent in either endpoint has no meaningful growth value.
        present_both = first["passes"] > 0 and last["passes"] > 0
        rows.append({
            "task": task,
            "ops_per_pass_from": first_opp if present_both else None,
            "ops_per_pass_to": last_opp if present_both else None,
            "ops_per_pass_growth": (last_opp / first_opp
                if present_both and first_opp not in (None, 0) else None),
            "days_per_pass_from": first_dpp if present_both else None,
            "days_per_pass_to": last_dpp if present_both else None,
            "days_per_pass_growth": (last_dpp / first_dpp
                if present_both and first_dpp not in (None, 0) else None),
        })
    rows.sort(key=lambda row: (row["ops_per_pass_growth"] is None,
                               -(row["ops_per_pass_growth"] or 0), row["task"]))
    return from_year, to_year, rows


def throughput_by_year(year_buckets):
    rows = []
    for year in sorted({year for year, _, _ in year_buckets}):
        total = sum_entries(entry for (entry_year, _, _), entry in year_buckets.items()
                            if entry_year == year)
        rows.append({
            "year": year, "passes": total["passes"], "days": total["days"],
            "passes_per_100_days": (100 * total["passes"] / total["days"]
                if total["days"] else None),
        })
    return rows


def by_slice_status(buckets):
    totals = {
        "slice": {field: 0 for field in ("passes", "days", "ticks", "ops")},
        "noslice": {field: 0 for field in ("passes", "days", "ticks", "ops")},
    }
    for (_, slice_status), entry in buckets.items():
        target = totals[slice_status]
        for field in ("passes", "days", "ticks", "ops"):
            target[field] += entry[field]
    total_days = totals["slice"]["days"] + totals["noslice"]["days"]
    total_ticks = totals["slice"]["ticks"] + totals["noslice"]["ticks"]
    total_ops = totals["slice"]["ops"] + totals["noslice"]["ops"]
    for status in ("slice", "noslice"):
        totals[status]["share_days"] = (
            totals[status]["days"] / total_days if total_days else None)
        totals[status]["share_ticks"] = (
            totals[status]["ticks"] / total_ticks if total_ticks else None)
        totals[status]["share_ops"] = (
            totals[status]["ops"] / total_ops if total_ops else None)
    return totals


def days_per_pass_by_task(buckets):
    """Repond a la question 2 (laquelle tache de file gonfle le cycle) : trie par jours totaux
    decroissants, avec le ratio par-passe en jours/ticks/opcodes pour comparer les grandeurs."""
    rows = []
    for (task, slice_status), entry in buckets.items():
        passes = entry["passes"]
        rows.append({
            "task": task,
            "slice_status": slice_status,
            "passes": passes,
            "days_total": entry["days"],
            "days_per_pass": entry["days"] / passes if passes else None,
            "ticks_total": entry["ticks"],
            "ticks_per_pass": entry["ticks"] / passes if passes else None,
            "ops_total": entry["ops"],
            "ops_per_pass": entry["ops"] / passes if passes else None,
        })
    rows.sort(key=lambda row: row["days_total"], reverse=True)
    return rows


def slice_decomposition(buckets):
    """Repond a la question 1 (tranche A* seule contre tache de file dans la meme passe), en
    jours/ticks/opcodes, restreint aux passes ou une tranche a tourne (slice_status == "slice")."""
    result = {}
    for unit, total_field, slice_field in (
        ("days", "days", "slice_days"),
        ("ticks", "ticks", "slice_ticks"),
        ("ops", "ops", "slice_ops"),
    ):
        pass_total = sum(entry[total_field] for (task, status), entry in buckets.items()
                          if status == "slice")
        slice_total = sum(entry[slice_field] for (task, status), entry in buckets.items()
                           if status == "slice")
        task_total = pass_total - slice_total
        result[unit] = {
            "pass_total": pass_total,
            "slice_total": slice_total,
            "task_total": task_total,
            "slice_share": slice_total / pass_total if pass_total else None,
            "task_share": task_total / pass_total if pass_total else None,
        }
    return result


def coverage_control(buckets, years, seed_count):
    measured_days = sum(entry["days"] for entry in buckets.values())
    expected_days = years * DAYS_PER_YEAR * seed_count
    return {
        "measured_days": measured_days,
        "expected_days": expected_days,
        "share": measured_days / expected_days if expected_days else None,
    }


def build_metrics(events, years, seed_count):
    buckets = aggregate_buckets(events)
    year_buckets = aggregate_year_buckets(events)
    growth_from_year, growth_to_year, growth = task_growth(year_buckets)
    return {
        "by_slice_status": by_slice_status(buckets),
        "days_per_pass_by_task": days_per_pass_by_task(buckets),
        "slice_decomposition": slice_decomposition(buckets),
        "coverage_control": coverage_control(buckets, years, seed_count),
        "by_year": by_year(year_buckets),
        "by_year_task": by_year_task(year_buckets),
        "growth_from_year": growth_from_year,
        "growth_to_year": growth_to_year,
        "task_growth": growth,
        "throughput_by_year": throughput_by_year(year_buckets),
    }


def run_selftest():
    """Verification sans processus externe des agregations annuelles et de leur ponderation."""
    output = "\n".join((
        "OPEX 1970-12-31 C39_PASS_CLOCK phase=annual year=1970 key=alpha|slice passes=2 days=20 ticks=200 ops=100 slice_days=10 slice_ticks=100 slice_ops=50",
        "OPEX 1970-12-31 C39_PASS_CLOCK phase=annual year=1970 key=alpha|noslice passes=2 days=10 ticks=100 ops=40 slice_days=0 slice_ticks=0 slice_ops=0",
        "OPEX 1970-12-31 C39_PASS_CLOCK phase=annual year=1970 key=beta|slice passes=8 days=80 ticks=800 ops=30 slice_days=40 slice_ticks=400 slice_ops=15",
        "OPEX 1971-12-31 C39_PASS_CLOCK phase=annual year=1971 key=alpha|slice passes=10 days=50 ticks=500 ops=1000 slice_days=25 slice_ticks=250 slice_ops=500",
        "OPEX 1971-12-31 C39_PASS_CLOCK phase=annual year=1971 key=alpha|noslice passes=10 days=50 ticks=500 ops=500 slice_days=0 slice_ticks=0 slice_ops=0",
        "OPEX 1971-12-31 C39_PASS_CLOCK phase=annual year=1971 key=beta|noslice passes=1 days=10 ticks=100 ops=20 slice_days=0 slice_ticks=0 slice_ops=0",
    ))
    metrics = build_metrics(parse_events(output), 2, 1)
    annual = {row["year"]: row for row in metrics["by_year"]}
    assert annual[1970]["passes"] == 12 and annual[1970]["days"] == 110
    assert annual[1970]["slice"]["days_per_pass"] == 10
    assert annual[1970]["noslice"]["days_per_pass"] == 5
    assert annual[1970]["slice_to_noslice_days_per_pass_ratio"] == 2
    alpha = next(row for row in metrics["task_growth"] if row["task"] == "alpha")
    assert metrics["growth_from_year"] == 1970 and metrics["growth_to_year"] == 1971
    assert alpha["ops_per_pass_from"] == 35
    assert alpha["ops_per_pass_to"] == 75
    assert alpha["ops_per_pass_growth"] == 75 / 35
    throughput = {row["year"]: row for row in metrics["throughput_by_year"]}
    assert throughput[1971] == {"year": 1971, "passes": 21, "days": 110,
                                "passes_per_100_days": 21 * 100 / 110}
    alpha_total = next(row for row in metrics["days_per_pass_by_task"]
                       if row["task"] == "alpha" and row["slice_status"] == "slice")
    # (20 + 50) / (2 + 10), not the unweighted mean of 10 and 5.
    assert alpha_total["days_per_pass"] == 70 / 12
    assert alpha_total["days_per_pass"] != (10 + 5) / 2
    print("selftest passed")


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

    out = args.out or ROOT / "results" / "diag_c39_6_pass_clock_6y_5seeds.json"
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
        per_seed.append({
            "seed": record["seed"],
            "run_ok": record["run_ok"],
            "metrics": build_metrics(events, args.years, 1),
        })
    failed = [{key: value for key, value in record.items() if key != "openttd_output"}
              for record in summary if not record["run_ok"]]
    payload = {
        "years": args.years,
        "seeds": args.seeds,
        "arm": ARM,
        "per_seed": per_seed,
        "cumulative": build_metrics(all_events, args.years, len(args.seeds)),
        "failed_runs": failed,
        "failed_run_count": len(failed),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
