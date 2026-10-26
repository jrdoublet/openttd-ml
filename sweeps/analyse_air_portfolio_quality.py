"""Analyse hors ligne de la qualite du portefeuille AIR OpexAI vs AAAHogEx.

Source attendue : campagne C66 avec line_telemetry. Aucun revenu/cout de ligne
n'est reconstruit : seuls les profits VEHS observes au checkpoint sont utilises.
"""

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from analyse_early_slot_lines import aggregate_markets


def _mean(values):
    return round(statistics.mean(values), 6) if values else None


def _median(values):
    return round(statistics.median(values), 6) if values else None


def analyse(payload, policy_id="early_slot"):
    # Un relevé mensuel ne doit pas remplacer arbitrairement le dernier relevé
    # annuel lorsque l'ordre physique des snapshots change. Les répétitions de
    # graine sont des parties distinctes, même si leurs lignes locales coïncident.
    latest = {}
    for snap in ((payload.get("line_telemetry") or {}).get("snapshots") or []):
        if snap.get("duel_policy_id") != policy_id:
            continue
        try:
            stamp = date.fromisoformat(snap["date"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("checkpoint AIR sans date valide") from exc
        if stamp.year != snap.get("year"):
            raise ValueError(f"checkpoint AIR avec annee contradictoire : {snap['date']}")
        key = (snap.get("arm"), snap.get("seed"), snap.get("repeat", 0), snap.get("year"))
        previous = latest.get(key)
        if previous is None or stamp > previous[0]:
            latest[key] = (stamp, snap)
        elif stamp == previous[0] and snap != previous[1]:
            raise ValueError(f"checkpoints AIR contradictoires : {key} {stamp}")
    by_key = {key: aggregate_markets(snap.get("lines"), "air")
              for key, (_, snap) in latest.items()}
    games_by_arm = defaultdict(set)
    for arm, seed, repeat, year in by_key:
        if year is not None:
            games_by_arm[arm].add((seed, repeat))

    annual = []
    for year in sorted({year for _, _, _, year in by_key if year is not None}):
        for arm in ("OpexAI", "AAAHogEx"):
            per_seed = []
            for seed, repeat in sorted(games_by_arm[arm]):
                if (arm, seed, repeat, year) not in by_key:
                    continue
                markets = list(by_key[(arm, seed, repeat, year)].values())
                profits = [m["profit_this_year_gbp"] for m in markets]
                vehicles = sum(m["vehicles"] for m in markets)
                capacity = sum(sum((m.get("capacity_by_cargo") or {}).values()) for m in markets)
                total_profit = sum(profits)
                per_seed.append({
                    "markets": len(markets),
                    "vehicles": vehicles,
                    "capacity": capacity,
                    "profit": total_profit,
                    "profit_per_market": total_profit / len(markets) if markets else None,
                    "profit_per_vehicle": total_profit / vehicles if vehicles else None,
                    "median_market_profit": statistics.median(profits) if profits else None,
                    "positive_markets": sum(value > 0 for value in profits),
                    "nonpositive_markets": sum(value <= 0 for value in profits),
                    "top5_profit_share": (
                        sum(sorted(profits, reverse=True)[:5]) / total_profit
                        if total_profit else None
                    ),
                })
            fields = per_seed[0].keys() if per_seed else ()
            annual.append({
                "year": year,
                "arm": arm,
                "seeds": len({seed for seed, repeat in games_by_arm[arm]
                              if (arm, seed, repeat, year) in by_key}),
                "games": len(per_seed),
                "mean": {
                    field: _mean([row[field] for row in per_seed if row[field] is not None])
                    for field in fields
                },
                "median": {
                    field: _median([row[field] for row in per_seed if row[field] is not None])
                    for field in fields
                },
            })

    final_year = max((year for _, _, _, year in by_key if year is not None), default=None)
    cohorts = []
    if final_year is not None:
        for arm in ("OpexAI", "AAAHogEx"):
            rows = []
            for seed, repeat in sorted(games_by_arm[arm]):
                first_seen = {}
                for year in sorted({year for a, s, r, year in by_key
                                    if a == arm and s == seed and r == repeat}):
                    for market_key in by_key.get((arm, seed, repeat, year), {}):
                        first_seen.setdefault(market_key, year)
                final = by_key.get((arm, seed, repeat, final_year), {})
                for market_key, market in final.items():
                    rows.append({
                        "seed": seed,
                        "repeat": repeat,
                        "market_key": market_key,
                        "first_seen_year": first_seen[market_key],
                        "profit": market["profit_this_year_gbp"],
                        "vehicles": market["vehicles"],
                    })
            for start in range(min((r["first_seen_year"] for r in rows), default=final_year), final_year + 1, 2):
                end = min(start + 1, final_year)
                group = [row for row in rows if start <= row["first_seen_year"] <= end]
                if not group:
                    continue
                profit = sum(row["profit"] for row in group)
                vehicles = sum(row["vehicles"] for row in group)
                cohorts.append({
                    "arm": arm,
                    "cohort": f"{start}-{end}",
                    "markets": len(group),
                    "profit_per_market": round(profit / len(group), 6),
                    "median_market_profit": _median([row["profit"] for row in group]),
                    "profit_per_vehicle": round(profit / vehicles, 6) if vehicles else None,
                    "vehicles_per_market": round(vehicles / len(group), 6),
                })

    return {
        "source_campaign": payload.get("campaign_id"),
        "policy_id": policy_id,
        "profit_scope": (
            "Somme VEHS profit_this_year/256 des vehicules encore presents au checkpoint; "
            "aucun revenue/running_cost de ligne reconstruit."
        ),
        "annual": annual,
        "final_year_cohorts": cohorts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--policy-id", default="early_slot")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = analyse(payload, args.policy_id)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("year arm markets veh/mkt profit/mkt median_mkt profit/veh top5share")
    for row in report["annual"]:
        m = row["mean"]
        markets = m["markets"]
        veh_per_market = m["vehicles"] / markets if markets else None
        print(
            row["year"], row["arm"],
            f"{markets:.2f}", f"{veh_per_market:.2f}",
            f"{m['profit_per_market']:.0f}", f"{m['median_market_profit']:.0f}",
            f"{m['profit_per_vehicle']:.0f}", f"{m['top5_profit_share']:.3f}",
        )


if __name__ == "__main__":
    main()
