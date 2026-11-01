#!/usr/bin/env python3
"""Rapport descriptif ROAD seul : parite Opex/AAAHogEx de 1 a 5 ans.

Lit le resultat fige et ses checkpoints mensuels. Aucune simulation, aucun
changement de reglage. Les annees sans deux observations restent absentes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import mean, median


ROOT = Path(__file__).resolve().parents[1]
ARMS = ("OpexAI", "AAAHogEx")


def read_annual_checkpoints(path: Path, start_year: int, years: int, policy_id: str | None = None):
    """Dernier checkpoint de decembre pour chaque compagnie, graine et an."""
    annual = {}
    observations = Counter()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                record = json.loads(line)
                arm, seed, rep = record["run"]
                date = record["date"]
                year = int(date[:4])
                seed = int(seed)
            except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError):
                continue
            if (arm not in ARMS or rep != 0 or year not in range(start_year, start_year + years)
                    or (policy_id is not None and record.get("duel_policy_id") != policy_id)):
                continue
            observations[(arm, seed, year)] += 1
            if date[5:7] != "12":
                continue
            key = (arm, seed, year)
            if key not in annual or date > annual[key]["date"]:
                annual[key] = record
    return annual, observations


def valid_number(record, field):
    value = record.get(field)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def analyse(result: dict, annual: dict, observations: Counter, policy_id: str | None = None):
    seeds = [int(seed) for seed in result["seeds"]]
    years = range(int(result["start_year"]), int(result["start_year"]) + int(result["years"]))
    games = {(int(g["seed"]), int(g["repeat"])): g for g in result.get("games", [])
             if policy_id is None or g.get("policy_id") == policy_id}
    summary = {(r["arm"], int(r["seed"])): r for r in result.get("summary", [])
               if r.get("arm") in ARMS and r.get("repeat") == 0
               and (policy_id is None or r.get("duel_policy_id") == policy_id)}
    rows = []
    for year in years:
        included = []
        missing = []
        invalid = []
        for seed in seeds:
            pair = [annual.get((arm, seed, year)) for arm in ARMS]
            if any(row is None for row in pair):
                missing.append(seed)
                continue
            profits = [valid_number(row, "profit_year") for row in pair]
            if any(p is None for p in profits):
                invalid.append(seed)
                continue
            included.append((seed, pair, profits))
        op = [entry[2][0] for entry in included]
        aaa = [entry[2][1] for entry in included]
        deltas = [a - b for a, b in zip(op, aaa)]
        measured = {}
        for field in ("company_value", "money", "current_loan", "n_vehicles", "n_stations",
                      "observed_opcodes_total", "observed_opcode_samples"):
            measured[field] = {}
            for idx, arm in enumerate(ARMS):
                values = [valid_number(pairs[idx], field) for _, pairs, _ in included]
                values = [value for value in values if value is not None]
                measured[field][arm] = mean(values) if values else None
        measured["road_lines"] = {}
        measured["road_vehicles_qualified"] = {}
        measured["largest_road_line_fleet"] = {}
        measured["mean_vehicles_per_road_line"] = {}
        for idx, arm in enumerate(ARMS):
            line_counts = []
            qualified_counts = []
            largest = []
            fleet_per_line = []
            for _, pairs, _ in included:
                rec = pairs[idx]
                telemetry = rec.get("line_telemetry")
                if isinstance(telemetry, dict) and telemetry.get("ok"):
                    lines = [line for line in telemetry.get("lines", [])
                             if line.get("mode") == "road"]
                    line_counts.append(len(lines))
                    counts = [line["vehicles"] for line in lines
                              if isinstance(line.get("vehicles"), int)]
                    if counts:
                        largest.append(max(counts))
                        fleet_per_line.append(mean(counts))
                vehicles_by_mode = rec.get("primary_vehicles_by_mode")
                if isinstance(vehicles_by_mode, dict) and isinstance(vehicles_by_mode.get("road"), int):
                    qualified_counts.append(vehicles_by_mode["road"])
            measured["road_lines"][arm] = mean(line_counts) if line_counts else None
            measured["road_vehicles_qualified"][arm] = mean(qualified_counts) if qualified_counts else None
            measured["largest_road_line_fleet"][arm] = mean(largest) if largest else None
            measured["mean_vehicles_per_road_line"][arm] = mean(fleet_per_line) if fleet_per_line else None
        # A negative or zero AAA denominator is a valid observation but cannot
        # establish profit parity through a ratio of means.
        aaa_mean = mean(aaa) if aaa else None
        op_mean = mean(op) if op else None
        ratio = op_mean / aaa_mean if aaa_mean is not None and aaa_mean > 0 else None
        wins = sum(delta > 0 for delta in deltas)
        ties = sum(delta == 0 for delta in deltas)
        year_data = {
            "year": year,
            "years_elapsed": year - int(result["start_year"]) + 1,
            "pairs": len(included), "expected_pairs": len(seeds),
            "missing_seeds": missing, "invalid_profit_seeds": invalid,
            "opex_mean_profit_year": op_mean, "aaa_mean_profit_year": aaa_mean,
            "profit_ratio_of_means": ratio, "gap_gbp_per_year": mean(deltas) if deltas else None,
            "median_paired_gap": median(deltas) if deltas else None,
            "wins": wins, "losses": len(deltas) - wins - ties, "ties": ties,
            "target_100_pct_reached": (ratio >= 1.0) if ratio is not None and len(included) == len(seeds) else None,
            "financial_and_physical": measured,
            "checkpoints": sum(observations.get((arm, seed, year), 0) for arm in ARMS for seed in seeds),
        }
        rows.append(year_data)
    game_ok = sum(bool(g.get("game_ok")) for g in games.values())
    return {
        "campaign": result["campaign_id"], "policy_id": policy_id,
        "bundle": result.get("source_bundle_sha256"),
        "years": list(rows), "games_ok": game_ok, "games_total": len(games),
        "failed_runs": len(result.get("failed_runs", [])),
        "requested_seeds": len(seeds),
        "conditions": {
            "reference": result.get("policies"),
            "aaahogex_settings": result.get("aaahogex_settings"),
            "start_year": result["start_year"], "map_size": result["map_size"],
        },
    }


def markdown(report):
    label = report['campaign'] + (" / " + report['policy_id'] if report.get('policy_id') else "")
    lines = [f"# ROAD seul : objectif 100 % chaque annee — {label}", "",
             f"Bundle `{report['bundle']}`. "
             f"Parties terminees saines : {report['games_ok']}/{report['games_total']}; "
             f"echecs declares : {report['failed_runs']}.", "",
             "| Horizon | Paires / attendues | OpexAI £/an | AAAHogEx £/an | Opex/AAA | Écart moyen £/an | Victoires | 100 % atteint ? |",
             "|---:|---:|---:|---:|---:|---:|---:|:---:|"]
    for row in report["years"]:
        fmt = lambda n: f"{n:,.0f}".replace(",", " ") if n is not None else "ND"
        ratio = f"{100 * row['profit_ratio_of_means']:.1f} %" if row["profit_ratio_of_means"] is not None else "ND"
        reached = row["target_100_pct_reached"]
        flag = "oui" if reached is True else "non" if reached is False else "non qualifie"
        lines.append(f"| {row['years_elapsed']} an(s) ({row['year']}) | {row['pairs']}/{row['expected_pairs']} | "
                     f"{fmt(row['opex_mean_profit_year'])} | {fmt(row['aaa_mean_profit_year'])} | "
                     f"{ratio} | {fmt(row['gap_gbp_per_year'])} | {row['wins']}/{row['pairs']} | {flag} |")
    lines.extend(["", "Les ratios sont des ratios de profits annuels moyens sur les memes graines, "
                  "pas une moyenne de ratios individuels. Un horizon incomplet reste non qualifie.", "",
                  "| Horizon | Caisse Opex/AAA £ | Véhicules routiers qualifiés Opex/AAA | Gares Opex/AAA | Lignes ROAD mesurées Opex/AAA |",
                  "|---:|---:|---:|---:|---:|"])
    for row in report["years"]:
        data = row["financial_and_physical"]
        def pair(field):
            a, b = (data[field][arm] for arm in ARMS)
            return (f"{a:,.0f}/{b:,.0f}".replace(",", " ")) if a is not None and b is not None else "ND"
        lines.append(f"| {row['years_elapsed']} | {pair('money')} | {pair('road_vehicles_qualified')} | "
                     f"{pair('n_stations')} | {pair('road_lines')} |")
    lines.extend(["", "| Horizon | Opcodes observés cumulés Opex/AAA | Échantillons Opex/AAA |",
                  "|---:|---:|---:|"])
    for row in report["years"]:
        data = row["financial_and_physical"]
        def pair(field):
            a, b = (data[field][arm] for arm in ARMS)
            return (f"{a:,.0f}/{b:,.0f}".replace(",", " ")) if a is not None and b is not None else "ND"
        lines.append(f"| {row['years_elapsed']} | {pair('observed_opcodes_total')} | {pair('observed_opcode_samples')} |")
    lines.extend(["", "| Horizon | Plus grande flotte par ligne ROAD (moyenne par graine) Opex/AAA | Véhicules moyens par ligne Opex/AAA |",
                  "|---:|---:|---:|"])
    for row in report["years"]:
        data = row["financial_and_physical"]
        def pair(field):
            a, b = (data[field][arm] for arm in ARMS)
            return f"{a:.1f}/{b:.1f}" if a is not None and b is not None else "ND"
        lines.append(f"| {row['years_elapsed']} | {pair('largest_road_line_fleet')} | {pair('mean_vehicles_per_road_line')} |")
    lines.extend(["", "La cible n'est mesuree qu'aux horizons complets. Ce tableau est descriptif : "
                  "il ne qualifie aucune modification du comportement de l'IA.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--policy", default=None, help="Filter a paired experiment to its exact policy ID")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    base = ROOT / "results" / args.campaign
    result = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    if len(result.get("policies", [])) > 1 and args.policy is None:
        parser.error("Paired campaign: --policy is required to prevent OFF/ON mixing")
    annual, observations = read_annual_checkpoints(base.with_suffix(".jsonl"), result["start_year"],
                                                    result["years"], args.policy)
    report = analyse(result, annual, observations, args.policy)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
