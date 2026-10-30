"""Health/provenance-gated ranking of new ESTIM31 AIR x RAIL duels.

The sole economic score is 100*mean(variant Opex profit_year) /
mean(variant AAAHogEx profit_year), each from the *same* variant duel.
No value, Wilcoxon, bootstrap or gain_short gate applies here.
"""
import argparse
import json
from pathlib import Path
from statistics import mean

from sweeps.estim31_combo2_prepare_20261030 import DEST, DESIGNS


def analyze(name, seeds=5, years=5):
    directory = DEST / name
    campaign = f"estim31combo2_{name}_{seeds}x{years}_20261030_r3"
    summary_file = directory / "results" / (campaign + ".json")
    journal_file = directory / "results" / (campaign + ".jsonl")
    if not (summary_file.is_file() and journal_file.is_file()):
        return None, "not_complete"
    summary = json.loads(summary_file.read_text("utf8"))
    games = summary.get("games") or []
    if summary.get("failed_runs") or len(games) != seeds * 2:
        return None, "failed_or_missing_games"
    if any(not g.get("game_ok") or g.get("game_status") != "complete"
           or g.get("source_bundle_sha256") != summary.get("source_bundle_sha256")
           for g in games):
        return None, "unhealthy_or_wrong_source"
    final_date = f"{1970 + years - 1}-12-01"
    arms = {"reference": {}, f"combo2_{name}": {}}
    sha = summary["source_bundle_sha256"]
    with journal_file.open(encoding="utf8") as lines:
        for raw in lines:
            row = json.loads(raw)
            policy = row.get("duel_policy_id")
            if policy not in arms or row.get("date") != final_date:
                continue
            key = tuple(row["run"][:3])
            if key in arms[policy] or row.get("source_bundle_sha256") != sha:
                return None, "duplicate_checkpoint_or_source_mismatch"
            arms[policy][key] = row
    if len(arms["reference"]) != seeds * 2 or len(arms[f"combo2_{name}"]) != seeds * 2:
        return None, "missing_final_checkpoints"
    means = {}
    for policy, rows in arms.items():
        opex = [r["profit_year"] for key, r in rows.items() if key[0] == "OpexAI"]
        aaa = [r["profit_year"] for key, r in rows.items() if key[0] == "AAAHogEx"]
        if len(opex) != seeds or len(aaa) != seeds or any(x is None for x in opex + aaa):
            return None, "missing_profit_year"
        means[policy] = {"opex": mean(opex), "aaa": mean(aaa),
                         "ratio_pct": 100 * sum(opex) / sum(aaa)}
    policy = f"combo2_{name}"
    values = arms[policy]
    ours = [r for key, r in values.items() if key[0] == "OpexAI"]
    return {"name": name, "years": years, "seeds": seeds,
            "configuration": json.loads((directory / "design.json").read_text("utf8"))["configuration"],
            "variant": means[policy], "reference_same_bundle": means["reference"],
            "ratio_delta_points_vs_same_bundle": means[policy]["ratio_pct"] - means["reference"]["ratio_pct"],
            "source_bundle_sha256": sha,
            "healthy_games": len(games), "year": final_date,
            "opex_train_mean": mean(r["primary_vehicles_by_mode"]["rail"] for r in ours),
            "opex_aircraft_mean": mean(r["air_primary_vehicles"] for r in ours),
            "opex_airports_mean": mean(r["air_airports"] for r in ours)}, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, choices=(5, 40), default=5)
    parser.add_argument("--years", type=int, choices=(5, 10), default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    done, pending = [], {}
    for name in DESIGNS:
        result, error = analyze(name, args.seeds, args.years)
        if error:
            pending[name] = error
        else:
            done.append(result)
    done.sort(key=lambda result: result["variant"]["ratio_pct"], reverse=True)
    for result in done:
        print(f"RANK {result['name']}: {result['variant']['ratio_pct']:.6f}% "
              f"(Opex {result['variant']['opex']:.0f}, AAA {result['variant']['aaa']:.0f}); "
              f"delta same-bundle {result['ratio_delta_points_vs_same_bundle']:+.4f} points")
    print("HEALTHY", len(done), "PENDING", pending)
    if args.output:
        args.output.write_text(json.dumps({"completed": done, "pending": pending},
                                          indent=2, ensure_ascii=False) + "\n", "utf8")


if __name__ == "__main__":
    main()
