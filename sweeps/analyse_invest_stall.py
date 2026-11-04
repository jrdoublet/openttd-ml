"""Analyse datée des traces rail de référence, sans extrapoler les sondes absentes.

Exemple : python -X utf8 sweeps/analyse_invest_stall.py --input results \
  --out results/invest_stall_baseline_20261103
"""

import argparse
import collections
import csv
import json
import re
from pathlib import Path


RECORD = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-\d{1,2} ([A-Z][A-Z0-9_]+)(?:\s|$)")
FIELD = re.compile(r"(?:^|\s)([a-z][a-z0-9_]*)=([^\s]+)")


def read_logs(paths, start_year=1973, end_year=1975):
    by_month = collections.defaultdict(collections.Counter)
    for path in paths:
        campaign = path.parent.name.removesuffix("_engine")
        arm = path.name.split("_seed", 1)[0]
        seed_match = re.search(r"seed(\d+)_r\d+\.log$", path.name)
        if seed_match is None:
            continue
        seed = int(seed_match.group(1))
        with path.open(encoding="utf-8", errors="replace") as source:
            for line in source:
                match = RECORD.search(line)
                if match is None:
                    continue
                year, month, event = int(match[1]), int(match[2]), match[3]
                if year < start_year or year > end_year:
                    continue
                fields = dict(FIELD.findall(line[match.end():]))
                counts = by_month[campaign, arm, seed, year, month]
                counts["observed_events"] += 1
                if event == "VIVIER_GEN" and fields.get("mode") == "rail":
                    counts["generation_scans"] += 1
                    for name in ("produced", "kept"):
                        counts[f"candidate_{name}"] += int(fields.get(name, "0"))
                elif event == "VIVIER_REJECT":
                    counts["generation_reject_" + fields.get("reason", "unknown")] += int(fields.get("n", "0"))
                elif event == "RAIL_OPEN_REJECT":
                    counts["rail_open_reject_" + fields.get("reason", "unknown")] += 1
                elif event == "PORTFOLIO_RANK" and fields.get("mode") == "rail":
                    counts["portfolio_ranked"] += 1
                elif event == "PROJECT_DISCARD" and fields.get("mode") == "rail":
                    counts["project_reject_" + fields.get("reason", "unknown")] += 1
                elif event == "PROJECT_CHOSEN" and fields.get("mode") == "rail":
                    counts["projects_chosen"] += 1
                elif event == "RAIL_ATTEMPT":
                    counts["attempts"] += 1
                    counts["attempt_" + fields.get("reason", "unknown")] += 1
                elif event == "RAIL_SEARCH":
                    counts["search_" + fields.get("outcome", "unknown")] += 1
                elif event == "RAIL_BUILD":
                    counts["lines_built"] += 1
                    counts["trains_initial"] += int(fields.get("trains", "1"))
                elif event == "RAIL_BUILD_FAIL":
                    counts["build_failed_" + fields.get("reason", "unknown")] += 1
                elif event == "RAIL_EXPAND":
                    counts["expand_" + fields.get("action", "unknown")] += 1
                elif event == "V284":
                    counts["v284_" + fields.get("action", "unknown")] += 1
                elif event == "V217_RAIL_REFILL":
                    counts["v217_scans"] += 1
                    counts["v217_startable"] += int(fields.get("startable", "0"))
                elif event == "N75_MC":
                    counts["n75_" + fields.get("phase", "unknown")] += 1
                    if fields.get("phase") == "refill":
                        counts["n75_budget_eligible"] += int(fields.get("budget_eligible", "0"))
                elif event == "INVEST_STALL":
                    action = fields.get("event", "unknown")
                    counts["invest_" + action] += 1
                    if action == "scan":
                        counts["invest_scan_eligible"] += int(fields.get("eligible", "0"))
                        counts["invest_scan_ops"] += int(fields.get("ops", "0"))
                    elif action == "skip":
                        counts["invest_skip_" + fields.get("reason", "unknown")] += 1
                elif event == "V257_REPLACE":
                    counts["v257_replaces"] += 1
    return by_month


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results"))
    parser.add_argument("--log-glob", default="*4x6*engine/reference_seed*_r0.log")
    parser.add_argument("--start-year", type=int, default=1973)
    parser.add_argument("--end-year", type=int, default=1975)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    paths = sorted(args.input.glob(args.log_glob))
    if not paths:
        raise SystemExit(f"Aucun log de simulation correspondant à {args.log_glob}")
    months = read_logs(paths, args.start_year, args.end_year)
    fields = sorted({name for counter in months.values() for name in counter})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.with_suffix(".csv").open("w", newline="", encoding="utf8") as dest:
        writer = csv.DictWriter(dest, fieldnames=["campaign", "arm", "seed", "year", "month", *fields])
        writer.writeheader()
        for key, counts in sorted(months.items()):
            writer.writerow({**dict(zip(("campaign", "arm", "seed", "year", "month"), key)), **counts})
    years = collections.defaultdict(collections.Counter)
    for (campaign, arm, seed, year, _), counts in months.items():
        years[campaign, arm, seed, year].update(counts)
    annual = [{"campaign": campaign, "arm": arm, "seed": seed, "year": year, **counts}
              for (campaign, arm, seed, year), counts in sorted(years.items())]
    args.out.with_suffix(".json").write_text(json.dumps(annual, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"Logs={len(paths)}, monthly={len(months)}, annual={len(annual)}")
    for row in annual:
        if "rail_long_smoke_4x6_r2_20261103" not in row["campaign"] and "invest_stall_smoke_4x10_20261103" not in row["campaign"]:
            continue
        print(f"{row['arm']:>12} {row['seed']:>6} {row['year']}: candidats={row.get('candidate_produced',0)}"
              f" gardés={row.get('candidate_kept',0)} origine_desservie={row.get('generation_reject_origin_served',0)}"
              f" classés={row.get('portfolio_ranked',0)} choisis={row.get('projects_chosen',0)}"
              f" construits={row.get('lines_built',0)}"
              f" scans_IS={row.get('invest_scan',0)} pub_IS={row.get('invest_publish',0)}"
              f" trop_proche={row.get('project_reject_too_close_no_join',0)}"
              f" recherche_occupée={row.get('project_reject_search_in_progress',0)}"
              f" échec_A*={row.get('build_failed_ABND',0)+row.get('build_failed_NOPA',0)}")


if __name__ == "__main__":
    main()
