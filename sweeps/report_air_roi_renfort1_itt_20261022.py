"""Rapport reproductible de la campagne AIR-ROI-RENFORT-1 ITT 20x6.

Lit le bilan C66 et les logs moteur du même bundle. Ne modifie aucune partie,
aucun résultat du banc et aucune politique. Toutes les comparaisons d'épisodes
emploient l'auditeur ITT ; les unités indépendantes sont les graines.

Attention : l'exécution écrit ``<campaign>_itt_report.json`` dans
``--results-dir`` et peut donc régénérer un rapport historique existant.
Choisir un répertoire de sortie contrôlé contenant une copie des entrées.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
from statistics import mean, median

from audit_air_roi_renfort1_itt import (analyze, add_months, cluster_itt,
                                       game_date, log_records, number, integer)
from datetime import date


def summary(values):
    values = sorted(x for x in values if x is not None)
    return {
        "count": len(values),
        "mean": mean(values) if values else None,
        "median": median(values) if values else None,
        "min": values[0] if values else None,
        "max": values[-1] if values else None,
    }


def paired_ci(deltas, replays=20000, seed=0):
    """IC percentile sur des deltas de graines appariées, une répétition/graine."""
    if len(deltas) < 2:
        return None
    rng = random.Random(seed)
    samples = [mean(deltas[rng.randrange(len(deltas))] for _ in deltas)
               for _ in range(replays)]
    samples.sort()
    return [samples[int(.025 * (replays - 1))], samples[int(.975 * (replays - 1))]]


def descriptive_ratio(episodes, numerator_key, denominator_key, replays=20000, seed=0):
    """Ratio Wald descriptif : les rééchantillonnages gardent les grappes entières."""
    by_seed = defaultdict(list)
    for ep in episodes:
        if ep["p"] == 50 and ep["seed"] is not None and ep["arm"] in ("treatment", "deferred"):
            by_seed[ep["seed"]].append(ep)

    def estimate(groups):
        arms = defaultdict(lambda: defaultdict(list))
        for rows in groups:
            for ep in rows:
                n = number(ep.get(numerator_key))
                d = number(ep.get(denominator_key))
                if n is not None and d is not None and not ep["issue"]:
                    arms[ep["arm"]]["n"].append(n)
                    arms[ep["arm"]]["d"].append(d)
        if not arms["treatment"]["n"] or not arms["deferred"]["n"]:
            return None
        dn = mean(arms["treatment"]["n"]) - mean(arms["deferred"]["n"])
        dd = mean(arms["treatment"]["d"]) - mean(arms["deferred"]["d"])
        return (dn / dd) if dd > 0 else None

    clusters = list(by_seed.values())
    point = estimate(clusters)
    result = {"estimate_gbp_per_added_aircraft": point, "ci95_seed_cluster": None,
              "bootstrap_replays": replays, "bootstrap_seed": seed,
              "note": "Ratio Wald descriptif; effet de ligne, pas rendement causal physique de l'appareil."}
    if len(clusters) < 2 or point is None:
        return result
    rng = random.Random(seed)
    vals = []
    for _ in range(replays):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        value = estimate(sample)
        if value is not None:
            vals.append(value)
    result["bootstrap_valid_replays"] = len(vals)
    if len(vals) < .9 * replays:
        return result
    vals.sort()
    result["ci95_seed_cluster"] = [vals[int(.025 * (len(vals) - 1))],
                                    vals[int(.975 * (len(vals) - 1))]]
    return result


def analyze_campaign(campaign, out_dir, *, followup_v2=False):
    path = out_dir / (campaign + ".json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    log_dir = out_dir / (campaign + "_engine")
    logs = sorted(log_dir.glob("airr1_itt_p50_seed*_r0.log"))
    if not logs:
        raise ValueError("Aucun log moteur p50 : campagne non analysable")
    telem = out_dir / (campaign + ".jsonl")
    # §8 endpoints use the per-episode NoAI monthly logs. Re-scanning the
    # ~1 GB C66 telemetry for the descriptive station proxy is unnecessary
    # and risks another out-of-memory failure during postprocessing.
    descriptive_telem = [] if followup_v2 else ([telem] if telem.is_file() else [])
    report = analyze(logs, descriptive_telem, replays=20000,
                     bootstrap_seed=0, include_episodes=True,
                     telemetry_policy_id="airr1_itt_p50", followup_v2=followup_v2)
    episodes = [ep for ep in report.pop("episodes") if ep["p"] == 50]
    months_seen = defaultdict(set)
    first_break = {}
    first_bad_second_year = {}
    for log in logs:
        for kind, row, _ in log_records(log):
            if kind != "AIRR1_ITT_MONTH":
                continue
            key = (str(row.get("seed")), str(row.get("id")))
            offset = integer(row.get("month_offset"))
            if offset is not None:
                months_seen[key].add(offset)
            if followup_v2 and offset is not None and 13 <= offset <= 24 \
                    and row.get("complete") == "0" and key not in first_bad_second_year:
                first_bad_second_year[key] = {
                    "reason": row.get("fail_reason"),
                    "days": integer(row.get("days")),
                }
            if row.get("complete") == "0" and key not in first_break:
                due, actual = integer(row.get("date_due")), integer(row.get("date_actual"))
                lag = actual - due if due is not None and actual is not None else None
                if followup_v2:
                    first_break[key] = (row.get("fail_reason") or "invalid_interval_other_or_unknown")
                else:
                    first_break[key] = ("checkpoint_lag_over_7_days" if lag is not None and lag > 7
                                        else "invalid_checkpoint_other_or_unknown")
    break_counts = Counter(first_break.values())
    comp = payload.get("policy_comparison") or {}
    pairs = comp.get("per_pair") or []
    all_seeds = sorted(set(payload.get("seeds", [])))
    paired = [p for p in pairs if p.get("complete") is True]
    complete_seeds = {p["seed"] for p in paired}
    primary = comp.get("aggregates", {}).get("profit_year", {})
    value = comp.get("aggregates", {}).get("company_value", {})
    counts = Counter(ep["arm"] for ep in episodes)
    additions = defaultdict(list)
    accounting = defaultdict(list)
    coverage = defaultdict(Counter)
    cohorts = defaultdict(lambda: defaultdict(lambda: Counter()))
    for ep in episodes:
        arm = ep["arm"]
        if ep["added"] is not None:
            additions[arm].append(ep["added"])
        if ep["transaction_accounting_cost"] is not None:
            accounting[arm].append(ep["transaction_accounting_cost"])
        coverage[arm]["assignments"] += 1
        coverage[arm]["24m_operating_valid"] += ep["line_vehicle_operating_profit_last_12m"] is not None
        coverage[arm]["24m_net_line_valid"] += ep["line_profit_last_12m"] is not None
        coverage[arm]["24m_vehs_proxy_valid"] += ep["line_fleet_profit_12m_proxy"] is not None
        coverage[arm]["missing_outcome"] += ep["added"] is None
        for key in ("fleet_class", "saturation", "kind", "v161_source", "v161_cohort"):
            group = ep.get(key) or "unknown"
            cohorts[key][group]["assigned_" + arm] += 1
            if ep["line_vehicle_operating_profit_last_12m"] is not None:
                cohorts[key][group]["24m_" + arm] += 1

    model_comparison = {}
    for source in sorted(set(ep.get("v161_source") or "unknown" for ep in episodes)):
        members = [ep for ep in episodes if (ep.get("v161_source") or "unknown") == source]
        model_comparison[source] = {
            "assignments": len(members),
            "modeled_per_aircraft_profit_gbp_per_year": summary([ep.get("v161_model") for ep in members]),
            "roi_selection_heuristic": summary([ep.get("roi_estimated") for ep in members]),
            "plane_quote_gbp": summary([ep.get("quote") for ep in members]),
            "observed_24m_treatment": sum(ep["line_vehicle_operating_profit_last_12m"] is not None
                                           and ep["arm"] == "treatment" for ep in members),
            "observed_24m_deferred": sum(ep["line_vehicle_operating_profit_last_12m"] is not None
                                          and ep["arm"] == "deferred" for ep in members),
        }

    snapshots = defaultdict(dict)
    for row in payload.get("summary", []):
        if row.get("arm") == "OpexAI":
            snapshots[row["seed"]][row.get("duel_policy_id")] = row
    structural_deltas = {}
    for category, key, kinds in (
        ("vehicles", "primary_vehicles_by_mode", ("rail", "road", "air", "water")),
        ("stations", "stations_by_facility", ("rail", "truck", "bus", "airport", "dock")),
    ):
        structural_deltas[category] = {}
        for kind in kinds:
            values = []
            for seed in all_seeds:
                if seed not in complete_seeds:
                    continue
                rows = snapshots[seed]
                if "airr1_itt_p0" not in rows or "airr1_itt_p50" not in rows:
                    continue
                left = rows["airr1_itt_p0"].get(key) or {}
                right = rows["airr1_itt_p50"].get(key) or {}
                if kind in left and kind in right:
                    values.append(right[kind] - left[kind])
            structural_deltas[category][kind] = {
                "paired_seed_deltas_p50_minus_p0": values,
                **summary(values),
                "ci95_seed_bootstrap": paired_ci(values),
            }
    first = cluster_itt(episodes, endpoint="added")
    operating = report["itt_line_vehicle_operating_profit_last_12m"]
    operating_ratio = descriptive_ratio(episodes, "line_vehicle_operating_profit_last_12m", "added")
    result = {
        "campaign": campaign,
        "recovery_provenance": payload.get("recovery_provenance"),
        "sha256_bundle": payload.get("source_bundle_sha256"),
        "sha256_manifest": payload.get("manifest_sha256"),
        "years": payload.get("years"),
        "seeds_requested": all_seeds,
        "games_completed": sum(g.get("game_ok") and g.get("game_status") == "complete"
                               for g in payload.get("games", [])),
        "games_total": len(payload.get("games", [])),
        "pairs_complete": len(paired),
        "pairs_total": len(pairs),
        "comparison_complete": comp.get("comparison_complete"),
        "metric_coverage_complete": comp.get("metric_coverage_complete"),
        "decision_rule": comp.get("decision_rule"),
        "verdict": comp.get("verdict"),
        "company_profit_year": primary,
        "company_value": value,
        "company_per_seed": [{
            "seed": p["seed"],
            "complete": p.get("complete"),
            "profit_year_delta": (p.get("metrics", {}).get("profit_year") or {}).get("policy_delta"),
            "company_value_delta": (p.get("metrics", {}).get("company_value") or {}).get("policy_delta"),
            "vehicles_delta": (p.get("metrics", {}).get("primary_vehicles") or {}).get("policy_delta"),
        } for p in pairs],
        "company_structural_differences_descriptive": structural_deltas,
        "assigned": dict(counts),
        "monthly_followup": {
            "episodes_with_24_month_rows": sum(len(months_seen[(ep["seed"], ep["episode_id"])]) == 24
                                               for ep in episodes),
            "episodes_with_less_than_24_month_rows": sum(len(months_seen[(ep["seed"], ep["episode_id"])]) < 24
                                                       for ep in episodes),
            "first_invalid_checkpoint_causes": dict(break_counts),
            "note": ("Les motifs d'intervalles sont locaux ; les fenetres 1-12 et 13-24 "
                     "sont independantes (amendement section 8)." if followup_v2
                     else "Le premier complete=0 devient irréversible; cause autre/inconnue si retard <=7 jours."),
        },
        "coverage_by_assignment": {a: dict(v) for a, v in coverage.items()},
        "first_stage_ITT_aircraft_added": first,
        "added_reported_by_arm": {a: summary(v) for a, v in additions.items()},
        "transaction_accounting_cost_by_arm": {a: summary(v) for a, v in accounting.items()},
        "descriptive_operating_ITT_per_aircraft_added": operating_ratio,
        "pre_registered_information_threshold": {
            "episodes_evaluable_24m": (operating["assigned_treatment_observed"]
                                      + operating["assigned_deferred_observed"]),
            "seeds_with_both_arms": operating["seeds_with_both_arms"],
            "required_episodes": 30,
            "required_seeds_with_both": 10,
            "met": (operating["assigned_treatment_observed"]
                    + operating["assigned_deferred_observed"] >= 30
                    and operating["seeds_with_both_arms"] >= 10),
        },
        "cohort_coverage": {k: {v: dict(count) for v, count in x.items()}
                            for k, x in cohorts.items()},
        "v161_model_versus_observation": model_comparison,
        "itt_auditor": report,
        "investments_displaced_verified": None,
        "physical_aircraft_roi_identifiable": False,
    }
    if followup_v2:
        result["amendment"] = "protocole_fourches_20261022_section_8_before_campaign2"
        result["telemetry_provenance"] = {
            "source": str(telem),
            "file_exists": telem.is_file(),
            "retained_original_jsonl": True,
            "descriptive_station_proxy_ingested": False,
            "reason": "V2 endpoints are direct monthly NoAI logs; omit unrelated bulky C66 station proxy",
        }
        result["itt_operating_12m"] = report["itt_line_vehicle_operating_profit_first_12m"]
        result["itt_operating_24m"] = report["itt_line_vehicle_operating_profit_last_12m"]
        end_date = date(1970 + int(payload["years"]), 1, 1)
        followup = {}
        per_seed = defaultdict(lambda: defaultdict(lambda: Counter()))
        for ep in episodes:
            per_seed[ep["seed"]][ep["arm"]]["assigned"] += 1
        for horizon in (12, 24):
            counts = defaultdict(Counter)
            status = Counter()
            for ep in episodes:
                arm = ep["arm"]
                assigned = game_date(ep["date"])
                eligible = assigned is not None and add_months(assigned, horizon) < end_date
                measured = ep.get("followup_" + str(horizon) + "m_status") == "valid"
                counts[arm]["assigned"] += 1
                if eligible:
                    counts[arm]["administratively_eligible"] += 1
                    per_seed[ep["seed"]][arm]["eligible_" + str(horizon)] += 1
                    if measured:
                        counts[arm]["valid"] += 1
                        per_seed[ep["seed"]][arm]["valid_" + str(horizon)] += 1
                    else:
                        reason = ep.get("followup_" + str(horizon) + "m_status") or "unknown"
                        counts[arm]["missing_" + reason] += 1
                        status[reason] += 1
                else:
                    counts[arm]["administratively_censored"] += 1
                    if measured:
                        counts[arm]["unexpected_observation_after_horizon"] += 1
            normalized = {arm: {**dict(v),
                      "retention_eligible": (v["valid"] / v["administratively_eligible"]
                                             if v["administratively_eligible"] else None),
                      "retention_all_assignments": (v["valid"] / v["assigned"] if v["assigned"] else None)}
                          for arm, v in counts.items()}
            t, d = (normalized.get(a, {}).get("retention_eligible") for a in ("treatment", "deferred"))
            epi = result["itt_operating_" + str(horizon) + "m"]
            threshold = (epi["assigned_treatment_observed"] + epi["assigned_deferred_observed"] >= 30
                         and epi["seeds_with_both_arms"] >= 10 and t is not None and d is not None
                         and min(t, d) >= .70 and abs(t-d) <= .10)
            followup[str(horizon)] = {"arms": normalized, "missing_reasons_among_eligible": dict(status),
                    "retention_gap_absolute": abs(t-d) if t is not None and d is not None else None,
                    "information_threshold_met": threshold}
        result["followup_windows"] = followup
        late_duration = Counter()
        for ep in episodes:
            assigned = game_date(ep["date"])
            if assigned is None or add_months(assigned, 24) >= end_date:
                continue
            if ep.get("followup_24m_status") != "interval_days_out_of_range":
                continue
            sample = first_bad_second_year.get((str(ep["seed"]), str(ep["episode_id"])))
            if sample is None or sample["reason"] != "interval_days_out_of_range" \
                    or sample["days"] is None:
                late_duration["unclassified"] += 1
            elif sample["days"] > 42:
                late_duration["greater_than_42_days"] += 1
            elif sample["days"] < 18:
                late_duration["less_than_18_days"] += 1
            else:
                late_duration["unexpected_in_range"] += 1
        result["failed_24m_interval_duration_by_first_bad_checkpoint"] = dict(late_duration)
        result["followup_by_seed"] = {k: {arm: dict(v) for arm, v in arms.items()}
                                      for k, arms in per_seed.items()}
        result["cohorts_12m_24m"] = {}
        for key in ("fleet_class", "saturation", "kind", "v161_source", "v161_cohort"):
            groups = {}
            for group in sorted({ep.get(key) or "unknown" for ep in episodes}):
                members = [ep for ep in episodes if (ep.get(key) or "unknown") == group]
                groups[group] = {"assigned": dict(Counter(ep["arm"] for ep in members)),
                    "12m": cluster_itt(members, endpoint="line_vehicle_operating_profit_first_12m"),
                    "24m": cluster_itt(members, endpoint="line_vehicle_operating_profit_last_12m")}
            result["cohorts_12m_24m"][key] = groups
        result["scientific_verdict"] = ("followup_information_met"
                                         if followup["24"]["information_threshold_met"]
                                         and result["games_completed"] == result["games_total"] == 40
                                         and result["pairs_complete"] == 20
                                         else "inconclusive")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    result = analyze_campaign(args.campaign, args.results_dir)
    path = args.results_dir / (args.campaign + "_itt_report.json")
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Rapport : {path}")
    print(f"Parties {result['games_completed']}/{result['games_total']}; paires "
          f"{result['pairs_complete']}/{result['pairs_total']}")
    print(f"ITT exploitation : {result['itt_auditor']['itt_line_vehicle_operating_profit_last_12m']}")
    print(f"ITT avions ajoutés : {result['first_stage_ITT_aircraft_added']}")


if __name__ == "__main__":
    main()
