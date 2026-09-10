"""Diagnostic C54 : ordres et profits des vehicules lus par l'API en jeu.

La sonde est passive. --selftest est Python pur et ne lance jamais OpenTTD.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
                      experiments, SCRIPT_FAILURE_MARKERS, write_json_atomically)
import bench_v2

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

ARM = "OpexAI[c54_vehicle_orders_probe=1]"
SEEDS = (100, 12345, 42, 7, 999)
MODES = ("rail", "road", "air", "water")
CLASSIFICATIONS = ("jamais_positif", "devenu_negatif", "toujours_positif", "irregulier")
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C54_VEHICLE_ORDERS\s*(.*)")
CHUNK_MODE = {"0": "rail", "1": "road", "2": "water", "3": "air"}


def parse_fields(text):
    return dict(token.split("=", 1) for token in text.split() if "=" in token)


def parse_events(output):
    events = []
    presence = Counter()
    failure_reason = None
    for line in (output or "").splitlines():
        if failure_reason is None:
            failure_reason = next((marker for marker in SCRIPT_FAILURE_MARKERS if marker in line), None)
        match = EVENT_RE.search(line)
        if match is None:
            continue
        fields = match.group(1)
        item = parse_fields(fields)
        presence.update(item)
        if item.get("phase") != "vehicle":
            continue
        required = ("year", "vid", "mode", "orders", "distinct_dest", "profit_last",
                    "profit_this", "in_depot", "line")
        if all(key in item for key in required):
            for key in ("year", "vid", "engine", "age", "max_age", "orders", "distinct_dest",
                        "profit_last", "profit_this", "in_depot", "line"):
                if key in item:
                    item[key] = int(item[key])
            events.append(item)
    # Metadonnees de la MEME passe regex, pour signaler un schema de log tronque sans reparcourir stdout.
    parse_events.last_field_presence = presence
    parse_events.last_failure_reason = failure_reason
    return events


def chunk_mode_counts(chunks):
    counts = Counter()
    vehicles = (chunks or {}).get("VEHS") or {}
    iterator = vehicles.values() if isinstance(vehicles, dict) else vehicles
    for vehicle in iterator:
        if isinstance(vehicle, dict) and str(vehicle.get("type")) in CHUNK_MODE:
            counts[CHUNK_MODE[str(vehicle["type"])]] += 1
    return {mode: counts[mode] for mode in MODES}


def keep(row):
    """Conserve les comptages VEHS par checkpoint; stdout n'est analyse qu'apres summarise()."""
    return ({"run": row["experiment"]["bench_run"], "date": str(row["date"]),
             "chunk_counts": chunk_mode_counts(row.get("chunks") or {}),
             "openttd_output": row.get("output", "")},)


def classify(profits):
    if all(value <= 0 for value in profits):
        return "jamais_positif"
    if all(value > 0 for value in profits):
        return "toujours_positif"
    if profits[-1] <= 0:
        return "devenu_negatif"
    return "irregulier"


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _warn(warnings, text):
    if text not in warnings:
        warnings.append(text)


def analyse(events, chunk_snapshots, warnings, field_presence=None):
    """Agrege les numerateurs avant toute division; events est deja parse une seule fois."""
    annual, trajectories = defaultdict(list), defaultdict(list)
    for event in events:
        if event["mode"] not in MODES:
            _warn(warnings, "Champ absent/invalide: aucun mode API reconnu pour au moins un evenement C54.")
            continue
        annual[event["year"]].append(event)
        trajectories[event["vid"]].append(event)
    if not events:
        _warn(warnings, "Champ absent partout: aucun evenement C54_VEHICLE_ORDERS parse.")
    if field_presence is not None:
        for field in ("year", "vid", "mode", "orders", "distinct_dest", "profit_last", "profit_this",
                      "in_depot", "line"):
            if not field_presence.get(field):
                _warn(warnings, f"Champ absent partout: {field} dans les lignes C54.")

    annual_output = []
    for year in sorted(annual):
        by_mode = {}
        snapshot = chunk_snapshots.get(year)
        if snapshot is None:
            _warn(warnings, f"Champ absent: aucun checkpoint VEHS pour year={year}; ecart chunks=null.")
        for mode in MODES:
            rows = [row for row in annual[year] if row["mode"] == mode]
            api_n = len(rows)
            chunk_n = snapshot.get(mode) if snapshot is not None else None
            under_two = sum(row["distinct_dest"] < 2 for row in rows)
            by_mode[mode] = {
                "api_vehicle_count": api_n, "chunk_vehicle_count": chunk_n,
                "api_minus_chunks": api_n - chunk_n if chunk_n is not None else None,
                "distinct_dest_distribution": {str(key): value for key, value in
                                              sorted(Counter(row["distinct_dest"] for row in rows).items())},
                "under_2_distinct_dest": under_two,
                "under_2_distinct_dest_share": ratio(under_two, api_n),
                "in_depot": sum(row["in_depot"] == 1 for row in rows),
                "in_depot_share": ratio(sum(row["in_depot"] == 1 for row in rows), api_n),
                "orphans": sum(row["line"] == -1 for row in rows),
                "orphan_share": ratio(sum(row["line"] == -1 for row in rows), api_n),
            }
            if not rows:
                _warn(warnings, f"Categorie vide: year={year}, mode={mode}.")

        annual_output.append({"year": year, "by_mode": by_mode})

    classified, excluded = [], []
    for vid, observations in trajectories.items():
        yearly = {row["year"]: row for row in sorted(observations, key=lambda row: row["year"])}
        rows = [yearly[year] for year in sorted(yearly)]
        if len(rows) < 2:
            excluded.append({"vid": vid, "mode": rows[-1]["mode"], "years": sorted(yearly),
                             "reason": "sans_annee_pleine_de_donnees"})
            continue
        item = {"vid": vid, "mode": rows[-1]["mode"], "years": sorted(yearly),
                "profits_last": [row["profit_last"] for row in rows],
                "latest_distinct_dest": rows[-1]["distinct_dest"]}
        item["classification"] = classify(item["profits_last"])
        classified.append(item)

    trajectory_counts = {mode: {label: 0 for label in CLASSIFICATIONS} for mode in MODES}
    cross = {}
    for mode in MODES:
        mode_classified = [item for item in classified if item["mode"] == mode]
        for item in mode_classified:
            trajectory_counts[mode][item["classification"]] += 1
        cross[mode] = {}
        for label in ("jamais_positif", "toujours_positif"):
            subset = [item for item in mode_classified if item["classification"] == label]
            numerator = sum(item["latest_distinct_dest"] < 2 for item in subset)
            if not subset:
                _warn(warnings, f"Categorie vide: trajectoire {mode}/{label}.")
            cross[mode][label] = {"under_2_distinct_dest": numerator, "denominator": len(subset),
                                  "share": ratio(numerator, len(subset))}
    if not excluded:
        _warn(warnings, "Categorie vide: aucun vehicule sans annee pleine de donnees.")
    return {"annual": annual_output,
            "profit_trajectories": {"classified": classified, "classification_counts": trajectory_counts,
                                    "without_full_year": excluded,
                                    "without_full_year_count": len(excluded)},
            "decisive_cross": cross}


def snapshots_by_year(records):
    snapshots = {}
    for record in records:
        try:
            checkpoint = date.fromisoformat(record["date"])
        except (TypeError, ValueError):
            continue
        # Le dernier checkpoint de l'annee est la comparaison chunks la plus proche du rapport.
        old = snapshots.get(checkpoint.year)
        if old is None or checkpoint.isoformat() > old[0]:
            snapshots[checkpoint.year] = (checkpoint.isoformat(), record["chunk_counts"])
    return {year: item[1] for year, item in snapshots.items()}


def run_selftest():
    lines = "\n".join((
        "OPEX 1971-1-1 C54_VEHICLE_ORDERS phase=vehicle year=1971 vid=1 mode=rail engine=1 age=1 max_age=10 orders=2 distinct_dest=1 profit_last=-5 profit_this=0 in_depot=0 line=2",
        "OPEX 1972-1-1 C54_VEHICLE_ORDERS phase=vehicle year=1972 vid=1 mode=rail engine=1 age=2 max_age=10 orders=2 distinct_dest=1 profit_last=0 profit_this=0 in_depot=0 line=2",
        "OPEX 1971-1-1 C54_VEHICLE_ORDERS phase=vehicle year=1971 vid=2 mode=road engine=1 age=1 max_age=10 orders=2 distinct_dest=2 profit_last=7 profit_this=0 in_depot=0 line=2",
        "OPEX 1972-1-1 C54_VEHICLE_ORDERS phase=vehicle year=1972 vid=2 mode=road engine=1 age=2 max_age=10 orders=2 distinct_dest=2 profit_last=-1 profit_this=0 in_depot=0 line=2",
        "OPEX 1971-1-1 C54_VEHICLE_ORDERS phase=vehicle year=1971 vid=3 mode=air engine=1 age=1 max_age=10 orders=2 distinct_dest=2 profit_last=1 profit_this=0 in_depot=0 line=2",
        "OPEX 1972-1-1 C54_VEHICLE_ORDERS phase=vehicle year=1972 vid=3 mode=air engine=1 age=2 max_age=10 orders=2 distinct_dest=2 profit_last=3 profit_this=0 in_depot=0 line=2",
        "OPEX 1971-1-1 C54_VEHICLE_ORDERS phase=vehicle year=1971 vid=4 mode=water engine=1 age=1 max_age=10 orders=2 distinct_dest=2 profit_last=-2 profit_this=0 in_depot=0 line=2",
        "OPEX 1972-1-1 C54_VEHICLE_ORDERS phase=vehicle year=1972 vid=4 mode=water engine=1 age=2 max_age=10 orders=2 distinct_dest=2 profit_last=3 profit_this=0 in_depot=0 line=2",
        "OPEX 1972-1-1 C54_VEHICLE_ORDERS phase=vehicle year=1972 vid=5 mode=rail engine=1 age=1 max_age=10 orders=1 distinct_dest=1 profit_last=9 profit_this=0 in_depot=1 line=-1",
    ))
    warnings = []
    result = analyse(parse_events(lines), {}, warnings)
    counts = result["profit_trajectories"]["classification_counts"]
    assert counts["rail"]["jamais_positif"] == 1
    assert counts["road"]["devenu_negatif"] == 1
    assert counts["air"]["toujours_positif"] == 1
    assert counts["water"]["irregulier"] == 1
    assert result["annual"][0]["by_mode"]["rail"]["under_2_distinct_dest"] == 1
    assert result["profit_trajectories"]["without_full_year_count"] == 1
    assert any("Categorie vide" in warning for warning in warnings)
    weighted = (1 + 9) / (1 + 100)
    unweighted = (1 / 1 + 9 / 100) / 2
    assert weighted != unweighted
    print("selftest passed: classifications=jamais_positif, devenu_negatif, toujours_positif, irregulier; under_2=1; without_full_year=1; empty_category_warning=1; weighted_mean_differs_from_mean_of_means=1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    out = args.out or ROOT / "results" / "diag_c54_vehicle_orders_10y_5seeds.json"
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION, max_workers=args.max_workers,
        result_processor=keep, experiments=experiments(build_arms([ARM]), args.seeds, args.years, 1, 1970),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    final_by_seed = {}
    for row in rows:
        seed = row["run"][1]
        if seed not in final_by_seed or row["date"] > final_by_seed[seed]["date"]:
            final_by_seed[seed] = row
    per_seed, all_events, all_snapshots, warnings, failed = [], [], defaultdict(list), [], []
    cumulative_presence = Counter()
    for seed, record in sorted(final_by_seed.items()):
        # Une seule passe de stdout par graine, puis le texte est immediatement abandonne.
        events = parse_events(record.get("openttd_output", ""))
        presence = parse_events.last_field_presence
        failure_reason = parse_events.last_failure_reason
        run_records = [row for row in rows if tuple(row["run"][:2]) == (ARM, seed)]
        seed_warnings = []
        metrics = analyse(events, snapshots_by_year(run_records), seed_warnings, presence)
        per_seed.append({"seed": seed, "run_ok": None, "metrics": metrics,
                         "warnings": seed_warnings})
        all_events.extend(events)
        cumulative_presence.update(presence)
        for year, counts in snapshots_by_year(run_records).items():
            all_snapshots[year].append(counts)
        run_ok = failure_reason is None
        per_seed[-1]["run_ok"] = run_ok
        if not run_ok:
            failed.append({key: value for key, value in record.items() if key != "openttd_output"})
    cumulative_snapshots = {year: {mode: sum(item[mode] for item in entries) for mode in MODES}
                            for year, entries in all_snapshots.items()}
    cumulative = analyse(all_events, cumulative_snapshots, warnings, cumulative_presence)
    payload = {"years": args.years, "seeds": args.seeds, "arm": ARM, "per_seed": per_seed,
               "cumulative": cumulative, "warnings": warnings, "failed_runs": failed,
               "failed_run_count": len(failed),
               "chunk_reference_last_state": {"rail": 87, "road": 305, "air": 598},
               "note": "API AIVehicleList counts vehicles, not rail wagons; compare API/chunks before interpreting the former 77% rail claim."}
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
