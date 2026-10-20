#!/usr/bin/env python3
"""Evolution V285 - reference aux annees 3, 5, 7, 10 sur JSONL mensuel.

Compteurs = flottes physiques agregees, non attribuables a un wagon V285
particulier. Le debit de passagers est le nombre livre au dernier trimestre.
"""
import argparse
import gzip
import json
from pathlib import Path
from statistics import mean, median


def read_rows(path, target_years):
    open_fn = gzip.open if path.suffix == ".gz" else open
    table = {}
    with open_fn(path, "rt", encoding="utf-8") as stream:
        for raw in stream:
            if not any(f'"date":"{year}-12-01"' in raw for year in target_years):
                continue
            obj = json.loads(raw)
            run = obj.get("run", [])
            if not run or run[0] != "OpexAI" or obj.get("company_slot") != 0:
                continue
            year = int(obj["date"][:4])
            table[(year, int(run[1]), obj["policy_id"])] = obj
    return table


def summarize(table, years, variant):
    result = {}
    for year in years:
        seeds = sorted({seed for (yr, seed, p) in table if yr == year and p == "reference"})
        pairs = [(table[(year, seed, "reference")], table[(year, seed, variant)])
                 for seed in seeds if (year, seed, variant) in table]
        stats = {"n": len(pairs)}
        for metric in ("profit_year", "company_value", "money", "primary_vehicles", "n_stations"):
            reference = [float(a[metric]) for a, _ in pairs]
            current = [float(b[metric]) for _, b in pairs]
            diffs = [b - a for a, b in zip(reference, current)]
            stats[metric] = {"reference": mean(reference), "variant": mean(current),
                             "delta": mean(diffs), "median_delta": median(diffs),
                             "wins": sum(x > 0 for x in diffs), "losses": sum(x < 0 for x in diffs)}
        for name, getter in (
            ("passenger_capacity", lambda x: x.get("capacities_by_cargo", {}).get("0", 0)),
            ("passengers_last_quarter", lambda x: (x.get("delivered_cargo_last_quarter") or [0])[0]),
            ("mail_last_quarter", lambda x: (x.get("delivered_cargo_last_quarter") or [0, 0, 0])[2]),
        ):
            ref = [float(getter(a)) for a, _ in pairs]
            var = [float(getter(b)) for _, b in pairs]
            stats[name] = {"reference": mean(ref), "variant": mean(var), "delta": mean(v - r for r, v in zip(ref, var))}
        result[str(year)] = stats
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--variant", default="v285m6")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    years = [1972, 1974, 1976, 1979]
    report = summarize(read_rows(args.jsonl, years), years, args.variant)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for year, stats in report.items():
        p = stats["profit_year"]
        c = stats["passenger_capacity"]
        d = stats["passengers_last_quarter"]
        print(f"{year} n={stats['n']} profit_delta={p['delta']:+.0f} "
              f"(W/L={p['wins']}/{p['losses']}) value_delta={stats['company_value']['delta']:+.0f} "
              f"capacity_delta={c['delta']:+.0f} delivered_pax_delta={d['delta']:+.0f}")


if __name__ == "__main__":
    main()
