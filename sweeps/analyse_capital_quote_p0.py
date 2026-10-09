#!/usr/bin/env python3
"""Regroupe les devis/reels CQ des DERNIERS checkpoints de parties P0.

Entree : checkpoint JSONL du harnais C66.4 apres extraction
`capital_quote_by_mode`. Une absence de SIGN est inconnue. Les couts d'echecs
au retour ne sont jamais interpretes comme pertes definitives.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def analyze(rows):
    latest = {}
    for row in rows:
        run = row.get("run")
        if not isinstance(run, (list, tuple)) or len(run) < 3 or run[0] != "OpexAI":
            continue
        key = (row.get("policy_id"), int(run[1]), int(run[2]))
        if key not in latest or str(row.get("date", "")) > str(latest[key].get("date", "")):
            latest[key] = row

    aggregates = defaultdict(lambda: defaultdict(lambda: {
        "games_with_measures": 0, "success_events": 0, "failed_events": 0,
        "quoted_success": 0, "actual_success": 0,
        "actual_failed_at_return": 0, "max_samples_learned": 0,
    }))
    unknown = defaultdict(int)
    by_game = []
    for (policy, seed, repeat), row in sorted(latest.items()):
        metrics = row.get("capital_quote_by_mode")
        if metrics is None:
            unknown[policy] += 1
            continue
        by_game.append({"policy_id": policy, "seed": seed, "repeat": repeat,
                        "last_checkpoint": row.get("date"),
                        "by_mode": metrics})
        for mode, value in metrics.items():
            out = aggregates[policy][mode]
            out["games_with_measures"] += 1
            for key in ("success_events", "failed_events", "quoted_success",
                        "actual_success", "actual_failed_at_return"):
                out[key] += value.get(key, 0)
            out["max_samples_learned"] += value.get("max_samples_learned", 0)
    by_policy = {}
    for policy, modes in aggregates.items():
        by_policy[policy] = {}
        for mode, data in modes.items():
            quotes = data["quoted_success"]
            actual = data["actual_success"]
            by_policy[policy][mode] = {
                **data,
                "ratio_actual_to_quote_success": actual / quotes if quotes > 0 else None,
                "delta_real_minus_quote_success": actual - quotes,
            }
    return {
        "last_checkpoint_games": len(latest),
        "games_without_extracted_signs": dict(unknown),
        "by_policy_and_mode": by_policy,
        "by_game": by_game,
        "not_observable_from_CQ": [
            "wrongly_declared_unaffordable_without_counterfactual_build",
            "company_cash_immobilized_by_reserved_liquidity",
            "net_loss_for_failed_builds_with_retained_assets_or_delayed_refunds",
            "terrain_homogeneity_within_mode_families",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8") as f:
        result = analyze(json.loads(line) for line in f if line.strip())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"last_checkpoint_games": result["last_checkpoint_games"],
                      "games_without_extracted_signs": result["games_without_extracted_signs"],
                      "by_policy_and_mode": result["by_policy_and_mode"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
