"""P2 hors-échantillon par graine : audit des lignes, jamais calibration de politique.

Sources exigées : un manifest/bundle figé, l'analyse AIR_BUILD→LINE_REVENUE
existante et les journaux originaux de ce même bundle. Pas de jeu, pas de Docker.
Les coefficients exploratoires ne sont jamais déclarés prêts à être appliqués :
le réalisé LINE_REVENUE n'isole pas les externalités réseau ni les transactions
de flotte cachées. Les exercices d'une même ligne/graine ne sont PAS iid.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import random
import re
import statistics

from analyse_score_cold_p2 import audit_lines, fields, can_apply, order, service_key
from analyse_score_cold_execution_p2 import opex_event


SEED = re.compile(r"seed(\d+)_r\d+\.log$")
ARMS = ("newpair", "hubsite", "hubhub")


def parse_seed(filename):
    match = SEED.search(str(filename))
    if not match:
        raise ValueError(f"nom de journal non appariable à une graine : {filename}")
    return int(match.group(1))


def construction_amort(log):
    """Une dépense annualisée de l'équipement construit, pas les externalités."""
    result = {}
    for line in log:
        record = fields(line, "C121_BUILD")
        if record and "actual_amort" in record and "line" in record:
            key = record["line"]
            if key in result:
                raise ValueError(f"duplicate C121_BUILD line={key}")
            result[key] = record
    return result


def extract_provisional(execution, logs):
    """Une seule année (la première) par ligne, + profils de sensibilité."""
    observations = []
    counts = Counter()
    seeds = set()
    for name, payload in sorted(execution["sources"].items()):
        seed = parse_seed(name)
        if seed in seeds:
            raise ValueError(f"duplicate seed {seed}")
        seeds.add(seed)
        if seed not in logs:
            raise ValueError(f"missing original engine log for seed {seed}")
        data = logs[seed]
        amorts = construction_amort(iter(data))
        purchases = payload["purchases"]
        counts["all_mature_line_years"] += len(payload["mature_annual"])
        chosen = {}
        for row in payload["mature_annual"]:
            if not row["provisional_comparable"]:
                continue
            counts["provisional_line_years"] += 1
            line = str(row["line"])
            purchase = purchases[line]
            detail = amorts.get(line)
            if detail is None or purchase["c121_actual_n"] != detail["actual_n"]:
                counts["amort_missing_or_build_mismatch"] += 1
                continue
            if row["arm"] != detail["arm"] or purchase["engine"] != detail["engine"]:
                counts["amort_arm_engine_mismatch"] += 1
                continue
            predicted = float(row["pred_prof"])
            if predicted <= 0:
                counts["bad_predicted_profit"] += 1
                continue
            realized = float(row["real_prof"])
            actual_amort = float(detail["actual_amort"])
            candidate = {
                "seed": seed,
                "line": line,
                "arm": row["arm"],
                "exercise": row["exercise"],
                "age": row["exercise"] - int(purchase["date"][:4]) + 1,
                "candidate_same_as_purchase": row["model_same_at_election_and_purchase"],
                "predicted": predicted,
                "realized": realized,
                "construction_annual_amort": actual_amort,
                "raw_ratio": realized / predicted,
                "amort_adjusted_ratio": (realized - actual_amort) / predicted,
            }
            key = seed, line
            if key not in chosen or candidate["exercise"] < chosen[key]["exercise"]:
                chosen[key] = candidate
        observations.extend(chosen.values())
    counts["unique_provisional_lines"] = len(observations)
    counts["distinct_development_seeds"] = len(seeds)
    return observations, dict(counts)


def arm_summary(observations, metric="amort_adjusted_ratio"):
    result = {}
    for arm in ARMS:
        rows = [row for row in observations if row["arm"] == arm]
        per_seed = defaultdict(list)
        for row in rows:
            per_seed[row["seed"]].append(row[metric])
        seed_medians = {seed: statistics.median(values)
                        for seed, values in sorted(per_seed.items())}
        result[arm] = {
            "lines": len(rows),
            "seeds": len(seed_medians),
            "per_seed_lines": {str(s): len(per_seed[s]) for s in sorted(per_seed)},
            "per_seed_medians": {str(k): v for k, v in seed_medians.items()},
            "median_of_seed_medians": (statistics.median(seed_medians.values())
                                       if seed_medians else None),
            "median_of_lines_descriptive_only": (statistics.median([r[metric] for r in rows])
                                                  if rows else None),
        }
    return result


def candidate_factors(training, metric, *, min_seeds=3, min_lines=4):
    """Exploration conservatrice : interdit toute famille sans support multi-seed."""
    summary = arm_summary(training, metric)
    factors = {}
    for arm, report in summary.items():
        if report["seeds"] < min_seeds or report["lines"] < min_lines:
            continue
        factor = report["median_of_seed_medians"]
        if factor is None or factor <= 0:
            continue
        factors["air:" + arm] = factor
    return factors


def witness_constructions(log, flip):
    """Constat du bras témoin, JAMAIS achat contrefactuel simulé."""
    old_key = flip["before_key"]
    new_key = flip["after_key"]
    expected_date = (int(flip["year"]), int(flip["month"]), int(flip["day"]))
    first_old = None
    new_purchases = 0
    for row in log:
        built = opex_event(row, "AIR_BUILD")
        if built is None:
            continue
        built_date, values = built
        build_key = (values.get("src"), values.get("dst"), values.get("arm"),
                     values.get("engine"))
        if build_key == (new_key[3], new_key[4], new_key[2], new_key[6]):
            new_purchases += 1
        if build_key == (old_key[3], old_key[4], old_key[2], old_key[6]):
            if built_date >= date(*expected_date):
                if first_old is None:
                    first_old = built_date.isoformat()
    return {"witness_legacy_air_build_date": first_old,
            "witness_alternative_air_build_count": new_purchases,
            "counterfactual_built": None}


def pass_exposure(log):
    """Mesure séparée de l'espace des choix réellement finançables et même tier."""
    passes = defaultdict(lambda: {"rows": [], "heads": []})
    for line in log:
        row = fields(line, "SCORE_COLD_P2_CAND")
        if row:
            passes[row["pass"]]["rows"].append(row)
        head = fields(line, "SCORE_COLD_P2_HEAD")
        if head:
            passes[head["pass"]]["heads"].append(head)
    stat = Counter()
    for entry in passes.values():
        if len(entry["heads"]) != 1:
            continue
        head = entry["heads"][0]
        rows = entry["rows"]
        if len(rows) != int(head.get("eligible", -1)) or head.get("dedupe") != "0":
            continue
        if head.get("fallback") == "1":
            rows = [r for r in rows if r["phase"] == "fallback"]
        if not rows:
            continue
        selected = order(rows)[0]
        stat["complete_nonempty_passes"] += 1
        challengers = [r for r in rows if r is not selected
                       and r["tier"] == selected["tier"]
                       and service_key(r) != service_key(selected)]
        if challengers:
            stat["same_tier_different_service_challenger_passes"] += 1
        if any(r["mode"] == "rail" for r in challengers):
            stat["same_tier_rail_challenger_passes"] += 1
        if any(can_apply(r) and r["mode"] == "air" for r in challengers):
            stat["same_tier_eligible_air_challenger_passes"] += 1
        if selected["mode"] == "air":
            stat["air_head_passes"] += 1
        elif selected["mode"] == "rail":
            stat["rail_head_passes"] += 1
        stat["tier_" + str(selected["tier"]) + "_head_passes"] += 1
    return dict(stat)


def clustered_bootstrap(observations, *, resamples=20000, seed=0):
    """Rééchantillonne les GRAINES (et donc toutes leurs lignes corrélées)."""
    seed_ids = sorted({r["seed"] for r in observations})
    medians = {}
    for arm in ARMS:
        medians[arm] = {}
        for sid in seed_ids:
            values = [r["amort_adjusted_ratio"] for r in observations
                      if r["seed"] == sid and r["arm"] == arm]
            if values:
                medians[arm][sid] = statistics.median(values)
    rng = random.Random(seed)
    sampled = {arm: [] for arm in ARMS}
    pair_ratios = []
    for _ in range(resamples):
        drawn = rng.choices(seed_ids, k=len(seed_ids))
        values = {arm: [medians[arm][sid] for sid in drawn if sid in medians[arm]]
                  for arm in ARMS}
        for arm in ARMS:
            if values[arm]:
                sampled[arm].append(statistics.median(values[arm]))
        if values["newpair"] and values["hubsite"]:
            pair_ratios.append(statistics.median(values["newpair"]) /
                               statistics.median(values["hubsite"]))

    def interval(values):
        if not values:
            return None
        x = sorted(values)
        return [x[int(.025 * len(x))], x[min(len(x) - 1, int(.975 * len(x)))]]

    return {
        "method": "paired map-seed cluster bootstrap; median of seed medians; no iid lines",
        "resamples": resamples,
        "seed": seed,
        "by_family": {arm: {
            "support_seed_count": len(medians[arm]),
            "nonempty_resamples": len(sampled[arm]),
            "ci95": interval(sampled[arm]),
        } for arm in ARMS},
        "newpair_over_hubsite": {
            "ci95": interval(pair_ratios),
            "resamples_valid": len(pair_ratios),
            "fraction_above_1": sum(ratio > 1 for ratio in pair_ratios) /
                                len(pair_ratios) if pair_ratios else None,
        },
    }


def analyze(execution, manifest, engine_dir, campaign=None, validation_seeds=None):
    """LOSO sur 5 graines ; jamais régler/évaluer sur la même graine."""
    src_bundle = manifest["source_bundle"]["sha256"]
    seeds = sorted({parse_seed(name) for name in execution["sources"]})
    if len(seeds) < 2:
        raise ValueError("need independent seeds")
    if validation_seeds is not None and set(seeds) & set(validation_seeds):
        raise ValueError("development seeds intersect reserved economic validation seeds")
    if campaign is not None:
        if campaign["campaign_id"] != manifest["campaign_id"] or (
            campaign["source_bundle_sha256"] != src_bundle
        ):
            raise ValueError("campaign/manifest provenance mismatch")
        manifest_games = {(g["policy_id"], g["seed"]) for g in manifest["games"]}
        for policy in ("reference", "scores_p2_shadow"):
            if any((policy, seed) not in manifest_games for seed in seeds):
                raise ValueError(f"incomplete campaign policy {policy}")
        effective = {p["id"]: p["settings"]["effective"] for p in manifest["policies"]}
        for policy, shadow in (("reference", 0), ("scores_p2_shadow", 1)):
            if effective[policy].get("score_cold_prior_shadow") != shadow:
                raise ValueError(f"not a 0/1 shadow-only trial: {policy}")
            if effective[policy].get("decision_log") != 1:
                raise ValueError(f"decision_log must be ON for joins: {policy}")
        if len({g["source_bundle_sha256"] for g in campaign["games"]}) != 1:
            raise ValueError("mixed source bundles")
    raw_logs = {}
    for name in execution["sources"]:
        seed = parse_seed(name)
        path = engine_dir / name
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open(encoding="utf8", errors="replace") as stream:
            raw_logs[seed] = list(stream)
    observations, counts = extract_provisional(execution, raw_logs)
    summary = {
        "source_bundle_sha256": src_bundle,
        "campaign_id": manifest["campaign_id"],
        "seeds": seeds,
        "counts": counts,
        "reserved_40_validation_seeds_checked": validation_seeds is not None,
        "development_validation_seed_overlap": sorted(set(seeds) & set(validation_seeds or [])),
        "raw_ratio_by_family": arm_summary(observations, "raw_ratio"),
        "amort_adjusted_ratio_by_family": arm_summary(observations),
        "amort_adjusted_cluster_bootstrap": clustered_bootstrap(observations),
        "equal_candidate_purchase_lines": sum(r["candidate_same_as_purchase"] for r in observations),
        "provenance": "C121_BUILD actual_amort; LINE_REVENUE annual real_prof; P2 election→purchase join",
        "holdout_by_seed": {},
        "calibration_ready": False,
        "behavior_policy_justified": False,
        "economic_profit_5y_effect_observed": False,
        "uncontrolled": [
            "C121 hub externality and competing-lines cannibalization cannot be allocated to LINE_REVENUE",
            "A matched vehicle count and logged FLEET_PROJECT exclude neither silent buy/sell nor crash",
            "The 5 independent development seeds are not an independent economic 40x5 validation",
            "Replaying a real C77 head never proves that alternative can actually be built",
            "No same-bundle rail freight/passenger outcome is available for reliable cross-modal factors",
        ],
    }
    for heldout in seeds:
        training = [row for row in observations if row["seed"] != heldout]
        test = [row for row in observations if row["seed"] == heldout]
        diag = {"train_line_count": len(training), "heldout_line_count": len(test),
                "heldout_families": dict(Counter(row["arm"] for row in test)),
                "baseline": audit_lines(raw_logs[heldout])["counts"],
                "exposure": pass_exposure(raw_logs[heldout])}
        for variant, metric in (("raw", "raw_ratio"), ("amort_adjusted", "amort_adjusted_ratio"),
                                ("amort_same_price", "amort_adjusted_ratio")):
            fit = [r for r in training if variant != "amort_same_price"
                   or r["candidate_same_as_purchase"]]
            factors = candidate_factors(fit, metric)
            replay = audit_lines(raw_logs[heldout], factors)
            enriched_flips = [dict(flip, witness=witness_constructions(raw_logs[heldout], flip))
                              for flip in replay["flips"]]
            heldout_test_errors = [abs(row[metric] - factors["air:" + row["arm"]])
                                   for row in test if "air:" + row["arm"] in factors]
            same_test_baseline_errors = [abs(row[metric] - 1.0)
                                         for row in test if "air:" + row["arm"] in factors]
            diag[variant] = {
                "train_seed_count_by_family": {arm: x["seeds"] for arm, x in arm_summary(fit, metric).items()},
                "factors": factors, "replay_counts": replay["counts"],
                "head_changes": enriched_flips,
                "heldout_abs_ratio_errors": {
                    "lines_covered": len(heldout_test_errors),
                    "predicted_median": (statistics.median(heldout_test_errors)
                                          if heldout_test_errors else None),
                    "neutral_1_median": (statistics.median(same_test_baseline_errors)
                                         if same_test_baseline_errors else None),
                },
                "heldout_line_count": len(test),
            }
            if variant == "amort_adjusted":
                # Uniquement sensibilite a shrinkage PREDECLARE, aucune valeur
                # optimisee sur les flips: alpha=0 signifie la politique OFF.
                diag["shrinkage_sensitivity_NOT_policy"] = {}
                for alpha in (0.0, 0.25, 0.5, 0.75, 1.0):
                    shrunk = {arm: 1.0 + alpha * (value - 1.0)
                              for arm, value in factors.items()}
                    replay_alpha = audit_lines(raw_logs[heldout], shrunk)
                    diag["shrinkage_sensitivity_NOT_policy"][str(alpha)] = {
                        "head_flips": replay_alpha["counts"].get("head_flips", 0),
                        "distinct_service_C77": replay_alpha["counts"].get(
                            "actionable_same_tier_od_flips", 0),
                    }
        summary["holdout_by_seed"][str(heldout)] = diag
    summary["LOSO_flips_by_profile"] = {
        kind: {"head_flips": sum(fold[kind]["replay_counts"].get("head_flips", 0)
                                 for fold in summary["holdout_by_seed"].values()),
               "distinct_service_C77": sum(fold[kind]["replay_counts"].get(
                   "actionable_same_tier_od_flips", 0) for fold in summary["holdout_by_seed"].values()),
               "baseline_mismatch": sum(fold[kind]["replay_counts"].get(
                   "baseline_mismatch", 0) for fold in summary["holdout_by_seed"].values())}
        for kind in ("raw", "amort_adjusted", "amort_same_price")
    }
    summary["shrinkage_flips_sensitivity_NOT_selected"] = {
        str(alpha): sum(fold["shrinkage_sensitivity_NOT_policy"][str(alpha)]["head_flips"]
                        for fold in summary["holdout_by_seed"].values())
        for alpha in (0.0, 0.25, 0.5, 0.75, 1.0)
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--validation-gate", type=Path, required=True,
                        help="Read ONLY the 40 pre-registered seed IDs; never use gate outcomes to fit.")
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(json.loads(args.execution.read_text(encoding="utf8")),
                     json.loads(args.manifest.read_text(encoding="utf8")), args.engine_dir,
                     json.loads(args.campaign.read_text(encoding="utf8")),
                     json.loads(args.validation_gate.read_text(encoding="utf8"))["seeds"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf8")
    print("P2 OOS:", result["counts"], "holdout flips", result["LOSO_flips_by_profile"],
          "calibration_ready", result["calibration_ready"])


if __name__ == "__main__":
    main()
