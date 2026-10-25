"""V228: descriptive 256²/1024² reference audit on a frozen OpexAI bundle.

Each input must be an independent C66.3 one-arm OpexAI-vs-AAAHogEx campaign.
No A/B verdict or causal calibration is produced: changing map size changes
the generated world, even when the seed number is reused.
"""

import argparse
import json
import math
import re
from pathlib import Path
from statistics import mean, median

CANONICAL_SEEDS = (
    42, 100, 7, 999, 2026, 1, 17, 73, 314, 512,
    1024, 1337, 4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309,
)


def read_reference(path, expected_start_year=1970):
    """Require a healthy complete 20x10 campaign at the expected start year.

    The historical 256²/1024² comparison continues to default to 1970.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    last_year = expected_start_year + 9
    checkpoint = f"{last_year}-12-01"
    if not data.get("source_bundle_sha256"):
        raise ValueError(f"empreinte du bundle manquante : {path}")
    if data.get("failed_runs") != []:
        raise ValueError(f"failed_runs absent ou non vide : {path}")
    seeds = data.get("seeds", [])
    if (len(seeds) != 20 or sorted(seeds) != sorted(CANONICAL_SEEDS)
            or data.get("years") != 10 or data.get("repeats") != 1):
        raise ValueError(f"V228 requiert 20 graines canoniques × 10 ans × 1 repetition : {path}")
    if data.get("start_year") != expected_start_year or data.get("expected_last_year") != last_year:
        raise ValueError(f"horizon {expected_start_year}-{last_year} different : {path}")
    campaign = data.get("campaign_id")
    policy = data.get("policy_id")
    if (not isinstance(campaign, str) or not campaign
            or policy != "reference"
            or data.get("expected_last_checkpoint") != checkpoint
            or not re.fullmatch(r"[0-9a-f]{64}", data.get("manifest_sha256") or "")):
        raise ValueError(f"identite ou manifeste C66.3 invalide : {path}")
    if (data.get("arms") != ["OpexAI", "AAAHogEx"]
            or len(data.get("policies", [])) != 1
            or data["policies"][0].get("id") != policy
            or data["policies"][0].get("role") != "reference"):
        raise ValueError(f"V228 requiert un seul duel OpexAI/AAAHogEx : {path}")
    # Checking only summary is insufficient: a truncated or failed game can
    # otherwise be presented alongside forty seemingly complete company rows.
    seen_games = set()
    for game in data.get("games", []):
        key = (game.get("seed"), game.get("repeat"))
        companies = game.get("companies", {})
        game_id = f"{campaign}:policy={policy}:s{key[0]}:r0"
        if (key[0] not in seeds or key[1] != 0 or key in seen_games
                or game.get("game_id") != game_id
                or game.get("campaign_id") != campaign
                or game.get("policy_id") != policy
                or game.get("source_bundle_sha256") != data["source_bundle_sha256"]
                or not game.get("game_ok") or game.get("game_status") != "complete"
                or game.get("expected_last_checkpoint") != checkpoint
                or game.get("unattributed_errors")
                or set(companies) != {"OpexAI", "AAAHogEx"}
                or any(not company.get("run_ok") or not company.get("horizon_complete")
                       or company.get("status") != "complete"
                       for company in companies.values())):
            raise ValueError(f"partie manquante ou malsaine : {key}")
        seen_games.add(key)
    if seen_games != {(seed, 0) for seed in seeds}:
        raise ValueError(f"20 parties moteur manquantes : {path}")
    games = {}
    for entry in data.get("summary", []):
        key = (entry.get("seed"), entry.get("arm"))
        if key[0] not in seeds or key[1] not in ("OpexAI", "AAAHogEx") or key in games:
            raise ValueError(f"jeu inattendu, duplique ou absent : {key}")
        if (entry.get("repeat") != 0 or not entry.get("run_ok")
                or entry.get("last_year") != last_year
                or entry.get("expected_last_year") != last_year
                or entry.get("last_date") != checkpoint
                or entry.get("expected_last_checkpoint") != checkpoint
                or entry.get("profit_year_quarters_valid") != 4
                or entry.get("profit_year_coverage") != "complete"
                or entry.get("status") != "complete"
                or not entry.get("horizon_complete") or not entry.get("game_ok")
                or not entry.get("include_in_economic_stats")
                or entry.get("source_bundle_sha256") != data["source_bundle_sha256"]
                or entry.get("campaign_id") != campaign
                or entry.get("game_id") != f"{campaign}:policy={policy}:s{key[0]}:r0"
                or entry.get("duel_policy_id") != policy
                or entry.get("policy_id") != (policy if key[1] == "OpexAI" else "AAAHogEx")
                or entry.get("company_slot") != (0 if key[1] == "OpexAI" else 1)
                or entry.get("script_errors") != []
                or entry.get("unattributed_errors") != []):
            raise ValueError(f"jeu incomplet ou malsain : {key}")
        if (any(not isinstance(entry.get(name), (int, float)) or not math.isfinite(entry[name])
                for name in ("company_value", "profit_year", "n_vehicles"))
                or entry["company_value"] <= 0 or entry["n_vehicles"] < 0):
            raise ValueError(f"bilan economique manquant : {key}")
        games[key] = entry
    if len(games) != 40 or any((seed, arm) not in games for seed in seeds for arm in ("OpexAI", "AAAHogEx")):
        raise ValueError(f"40 bilans OpexAI/AAAHogEx manquants : {path}")
    return data, games


def summarize_map(data, games):
    opex = [games[(seed, "OpexAI")] for seed in data["seeds"]]
    aaa = [games[(seed, "AAAHogEx")] for seed in data["seeds"]]
    mean_op = mean(p["profit_year"] for p in opex)
    mean_aa = mean(p["profit_year"] for p in aaa)
    if any(rival["profit_year"] <= 0 for rival in aaa):
        raise ValueError("ratio V228 indefini : profit terminal AAAHogEx non positif")
    ratio_per_seed = [100 * op["profit_year"] / rival["profit_year"]
                      for op, rival in zip(opex, aaa)]
    return {
        "map_size_exponent": data["map_size"],
        "pairs": len(opex),
        "profit_year_mean_opex": round(mean_op, 2),
        "profit_year_mean_aaahogex": round(mean_aa, 2),
        "opex_to_aaa_ratio_of_means_pct": round(100 * mean_op / mean_aa, 3) if mean_aa > 0 else None,
        "paired_ratio_median_pct": round(median(ratio_per_seed), 3) if ratio_per_seed else None,
        "paired_ratios_eligible": len(ratio_per_seed),
        "opex_wins": sum(op["profit_year"] > rival["profit_year"] for op, rival in zip(opex, aaa)),
        "mean_opex_vehicles": round(mean(p["n_vehicles"] for p in opex), 2),
        "mean_aaa_vehicles": round(mean(p["n_vehicles"] for p in aaa), 2),
        "opex_company_value_floor_1_count": sum(p["company_value"] == 1 for p in opex),
    }


def compare(map256, map1024):
    small, small_games = read_reference(map256)
    large, large_games = read_reference(map1024)
    if (small.get("map_size"), large.get("map_size")) != (8, 10):
        raise ValueError("V228 requiert les cartes 256² et 1024² dans cet ordre")
    for field in ("source_bundle_sha256", "policy_id", "policies", "arms", "design",
                  "aaahogex_settings", "openttd_version", "opengfx_version"):
        if small.get(field) != large.get(field):
            raise ValueError(f"bundle ou reglage divergent : {field}")
    if sorted(small["seeds"]) != sorted(large["seeds"]):
        raise ValueError("listes de graines non appariees")
    return {
        "interpretation": ("Deux references monobras distinctes; comparaison descriptive entre cartes, "
                           "sans porte V102, contrefactuel de construction ni preuve de rendement."),
        "bundle": small["source_bundle_sha256"],
        "seeds": sorted(small["seeds"]),
        "map256": summarize_map(small, small_games),
        "map1024": summarize_map(large, large_games),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map256", type=Path, required=True)
    parser.add_argument("--map1024", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("ne pas ecraser un diagnostic existant")
    result = compare(args.map256, args.map1024)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"map256": result["map256"], "map1024": result["map1024"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
