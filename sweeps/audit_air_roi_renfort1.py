"""AIR-ROI-RENFORT-1 étape 1 : audit descriptif des logs existants.

Usage : python -X utf8 sweeps/audit_air_roi_renfort1.py \
    "results/air_flotte1_shadow_causes_5x6_20261022_engine/*.log" \
    --reference "results/rail_cal4_40x10_multimodal_pc_20261021_engine/reference_*.log"

Les données d'une autre partie ou campagne ne sont jamais jointes à un achat.
Une observation C121 à +2 est un delta de profit de ligne, sans témoin causal.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import glob
import json
from pathlib import Path
import re
from statistics import median


EVENT = re.compile(r"\bOPEX\s+(\d{4}-\d{1,2}-\d{1,2})\s+([A-Z0-9_]+)\s+(.*)$")
MARGINAL = re.compile(r"\bC121_FLEET_MARGINAL\s+(.*)$")
FIELD = re.compile(r"(\w+)=([^\s]+)")
SHADOW = {"AIRF1_BUY", "AIRF1_CLOCK", "AIRF1_READY", "AIRF1_OUTCOME",
          "AIRF1_LIST", "AIRF1_POOL", "AIRF1_RAIL",
          "AIRR1_PRE", "AIRR1_CONTEXT", "AIRR1_OUTCOME"}
SINGLE = SHADOW - {"AIRF1_RAIL"}
UNKNOWN_DIMENSIONS = ("planes_before_exact", "saturation", "capacity", "line_age_days",
                      "cycle_days", "competitor_pressure", "line_arm")
ROI_NUMERIC = {
    "baseVehicles", "vehCount", "want", "target", "physicalMax", "planeCapacity",
    "waitPaxA", "waitPaxB", "waitMailA", "waitMailB", "airportOccupancy",
    "pickupRate", "lastHistoricalCycleDays", "airportWaitDays", "buildDate",
    "lineAgeDays", "baseYear", "lastFleetDate", "marginalSamples", "coldStart",
    "economicWindowYears", "v161Neighbours", "v161Amort", "ownedRoutesA",
    "ownedRoutesB", "rivalCapacity", "cargo", "stationA", "stationB",
    "refleetEngine", "c77Tier", "c77Stamp", "kDec", "kDecTick", "fundScore",
    "unitPrice", "actualCost", "added", "replaced",
}
ROI_TEXT = {"c121Arm", "reason"}
ROI_FIELDS = ROI_NUMERIC | ROI_TEXT


def fields(payload):
    return dict(FIELD.findall(payload))


def numeric(row, key, default=None):
    try:
        value = float(row[key])
        if not (-float("inf") < value < float("inf")):
            return default
        return value
    except (KeyError, ValueError, TypeError):
        return default


def med(rows, key):
    vals = [row[key] for row in rows if row.get(key) is not None]
    return median(vals) if vals else None


def day_key(row):
    y, m, d = (int(part) for part in row["date"].split("-"))
    return date(y, m, d)


def when_key(row):
    """Tri des événements d'un jour par tick enregistré, sans tri lexical d'ID."""
    return (day_key(row), row["tick"] if row.get("tick") is not None else -1)


def percentile(rows, key, p):
    vals = sorted(row[key] for row in rows if row.get(key) is not None)
    if not vals:
        return None
    return vals[int((len(vals) - 1) * p)]


def grouped(rows, column):
    groups = defaultdict(list)
    for row in rows:
        groups[str(row.get(column, "unknown"))].append(row)
    return {key: {"n": len(group),
                  "cap_ratio_median": med(group, "cap_ratio"),
                  "model_roi_median_pm": med(group, "model_roi_pm"),
                  "published_roi_median_pm": med(group, "published_roi_pm"),
                  "calibrated_roi_median_pm": med(group, "calibrated_roi_pm"),
                  "c70_ratio_median": med(group, "calibration_ratio"),
                  "rank_median": med(group, "rank"),
                  "stable_built": sum(x["stable"] for x in group),
                  "built": sum(x["built"] for x in group)}
            for key, group in sorted(groups.items())}


def read_shadow(path):
    """Retourne des épisodes locaux au fichier; ID de partie jamais global."""
    records = {}
    observations = []
    for line in Path(path).open(encoding="utf-8", errors="replace"):
        match = EVENT.search(line)
        if match and match.group(2) in SHADOW:
            date, kind, payload = match.groups()
            row = fields(payload)
            event_id = row.get("id")
            if not event_id:
                continue
            rec = records.setdefault(event_id, {"id": event_id, "slots": {},
                                                "rails": [], "duplicates": set(), "date": date})
            if kind == "AIRF1_RAIL":
                rec["rails"].append(row)
            elif kind in rec["slots"]:
                rec["duplicates"].add(kind)
            else:
                rec["slots"][kind] = row
            if rec["date"] != date:
                rec["duplicates"].add("date")
        else:
            marginal = MARGINAL.search(line)
            if marginal:
                observations.append(fields(marginal.group(1)))
    return records, observations


def roi_probe_episode(rec, path):
    """Champs préachat seulement, avec origine propre ; jamais de repli post-achat."""
    slots = rec["slots"]
    pre = slots.get("AIRR1_PRE")
    context = slots.get("AIRR1_CONTEXT")
    outcome = slots.get("AIRR1_OUTCOME")
    if pre is None and context is None and outcome is None:
        return None
    sources = {"AIRR1_PRE": pre or {}, "AIRR1_CONTEXT": context or {},
               "AIRR1_OUTCOME": outcome or {}}
    values = {}
    provenance = {}
    conflicts = []
    for kind, event in sources.items():
        for key in ROI_FIELDS:
            if key not in event:
                continue
            if key in provenance:
                conflicts.append(key)
                continue
            raw = event[key]
            origin = event.get(key + "_src", "missing")
            if raw in ("na", "unknown", "null") or origin == "missing":
                value = None
                origin = "missing"
            else:
                value = numeric(event, key) if key in ROI_NUMERIC else raw
                if value is None:
                    origin = "invalid"
            values[key] = value
            provenance[key] = origin
    for key in ROI_FIELDS:
        values.setdefault(key, None)
        provenance.setdefault(key, "missing")
    pre_tick = numeric(pre or {}, "tick_pre")
    after_tick = numeric(outcome or {}, "tick_after")
    return {
        "file": str(path), "id": rec["id"], "date": rec["date"],
        "complete": all(sources.values()) and not conflicts and not rec["duplicates"],
        "duplicate": bool(rec["duplicates"]), "field_conflicts": conflicts,
        "tick_pre": pre_tick, "tick_after": after_tick,
        "same_tick": (pre_tick == after_tick if pre_tick is not None
                      and after_tick is not None else None),
        "values": values, "provenance": provenance,
        "actual_cost_kind": "net_AIAccounting_transaction_not_unit_invoice",
        "causal_incremental_profit": None,
    }


def episode(rec, path):
    slots = rec["slots"]
    buy = slots.get("AIRF1_BUY")
    if buy is None:
        return None
    outcome = slots.get("AIRF1_OUTCOME", {})
    clock = slots.get("AIRF1_CLOCK", {})
    ready = slots.get("AIRF1_READY", {})
    is_built = outcome.get("outcome") == "built"
    stable = (is_built and not rec["duplicates"] and clock.get("same_tick") == "1"
              and ready.get("same_tick") == "1" and ready.get("same_cash") == "1")
    channel = buy.get("channel", "unknown")
    price = numeric(buy, "unit_price")
    spend = numeric(buy, "spend")
    finance = numeric(buy, "finance")
    model = numeric(buy, "v161_model")
    raw = numeric(buy, "raw_profit")
    cal = numeric(buy, "calibrated_profit")
    tick = numeric(buy, "tick")
    kdec_tick = numeric(buy, "k_dec_selection_tick")
    kdec = numeric(buy, "k_dec_snapshot")
    units = round(spend / price) if (spend is not None and price and price > 0
                                     and spend / price >= 1
                                     and abs(spend / price - round(spend / price)) < .001) else None
    model_total = model * units if (model is not None and model >= 0 and units is not None) else None
    prior = model_total > 0 if model_total is not None else False
    cap_ratio = raw / model_total if prior and raw is not None and raw >= 0 else None
    denom = max(finance, kdec) if (finance is not None and finance > 0 and kdec is not None
                                   and kdec >= 0) else None
    reconstructed_score = (cal * 1000 / denom if channel == "reinforce" and cal is not None
                           and denom and denom > 0 else None)
    stored_score = numeric(buy, "fund_score")
    # Valeur publiée à l'achat = post-V161, avant application éventuelle de C70.
    # Le score stocké est celui de la sélection précédente, potentiellement périmée.
    return {
        "file": str(path), "id": rec["id"], "date": rec["date"],
        "tick": tick,
        "year": int(rec["date"][:4]), "line": buy.get("line"),
        "channel": channel, "built": is_built, "stable": stable,
        "outcome": outcome.get("outcome", "missing"),
        "duplicate": bool(rec["duplicates"]), "complete": all(key in slots for key in
          ("AIRF1_BUY", "AIRF1_OUTCOME", "AIRF1_READY", "AIRF1_CLOCK")),
        "raw_profit": raw if raw is not None and raw >= 0 else None,
        "calibrated_profit": cal if cal is not None and cal >= 0 else None,
        "v161_model_per_plane": model if model is not None and model >= 0 else None,
        "model_total_profit": model_total, "cap_ratio": cap_ratio,
        "calibration_ratio": cal / raw if raw and raw > 0 and cal is not None and cal >= 0 else None,
        "v161_source": buy.get("v161_src", "unknown"),
        "planned_units": units, "unit_price": price, "spend": spend,
        "finance": finance, "reserve": numeric(buy, "reserve"),
        "cash": numeric(buy, "cash"), "avail": numeric(buy, "avail"),
        "cash_after": numeric(outcome, "cash_after"),
        "cash_delta_post": ((numeric(buy, "cash") - numeric(outcome, "cash_after"))
                            if numeric(buy, "cash") is not None
                            and numeric(outcome, "cash_after") is not None else None),
        "rank": numeric(buy, "rank"), "fund_score_stored": stored_score,
        "raw_roi_stored_pm": numeric(buy, "raw_roi"),
        "published_roi_pm": raw * 1000 / spend if raw is not None and spend and spend > 0 else None,
        "model_roi_pm": model_total * 1000 / spend if model_total is not None and spend and spend > 0 else None,
        "calibrated_roi_pm": cal * 1000 / finance if cal is not None and finance and finance > 0 else None,
        "fund_roi_recomputed_pm": reconstructed_score,
        "fund_score_matches_c69": (abs(reconstructed_score - stored_score) <= max(.03, .0001 * abs(stored_score))
                    if reconstructed_score is not None and stored_score is not None else None),
        "k_dec": kdec, "k_dec_tick_lag": tick - kdec_tick if tick is not None
                                            and kdec_tick is not None and kdec_tick >= 0 else None,
        "added": numeric(outcome, "added"), "replaced": numeric(outcome, "replaced"),
        "rail_remaining": numeric(slots.get("AIRF1_LIST", {}), "rail_remaining"),
        "rail_pass_reason": slots.get("AIRF1_LIST", {}).get("rail_pass_reason", "unknown"),
        "rail_search_phase": buy.get("rail_search_phase", "unknown"),
        "rail_pool_truncated": slots.get("AIRF1_POOL", {}).get("truncated"),
        "actual_cost_observed": None, "actual_incremental_profit": None,
    }


def match_line_proxies(episodes, observations):
    """C121 +2 n'est qu'un delta de la ligne et peut inclure d'autres projets."""
    successful = [r for r in episodes if r["channel"] == "reinforce" and r["built"]
                  and r["added"] == 1 and r["line"] is not None]
    successful.sort(key=lambda r: (when_key(r), r["id"]))
    matched = []
    for obs in observations:
        lid = obs.get("line")
        obs_year = numeric(obs, "year")
        if lid is None or obs_year is None or numeric(obs, "added") != 1:
            continue
        eligible = [r for r in successful if r["line"] == lid
                    and r["year"] + 2 == obs_year]
        # Plusieurs achats cette année : impossible de donner à un seul avion le delta.
        if len(eligible) != 1:
            continue
        row = eligible[0]
        if any(r["line"] == lid and when_key(row) < when_key(r)
               and r["year"] < obs_year and r["built"] for r in episodes):
            continue
        profit = numeric(obs, "obs_profit")
        if profit is None:
            continue
        matched.append({"year": row["year"], "line": lid, "predicted": row["raw_profit"],
                        "model": row["model_total_profit"], "observed_line_delta": profit,
                        "error_line_proxy": row["raw_profit"] - profit if row["raw_profit"] is not None else None,
                        "v161_source": row["v161_source"], "stable": row["stable"]})
    return matched


def summarize_shadow(paths, include_episodes=False):
    counts = Counter()
    rows = []
    proxies = []
    by_file = {}
    roi_rows = []
    for path in paths:
        records, observations = read_shadow(path)
        roi_rows.extend(filter(None, (roi_probe_episode(rec, path) for rec in records.values())))
        one = [episode(rec, path) for rec in records.values()]
        one = [r for r in one if r is not None]
        one.sort(key=lambda r: (when_key(r), r["id"]))
        # Episodes de croissance antérieures de cette même ligne, pas nb d'avions.
        prev = Counter()
        for row in one:
            row["prior_successful_growth_episodes"] = prev[row["line"]]
            row["growth_history_bucket"] = str(min(prev[row["line"]], 3)) + ("+" if prev[row["line"]] >= 3 else "")
            if row["channel"] == "reinforce" and row["built"] and row["added"] and row["added"] > 0:
                prev[row["line"]] += 1
        one_proxy = match_line_proxies(one, observations)
        counts["c121_post_line_observations"] += len(observations)
        proxies.extend(one_proxy)
        by_file[Path(path).name] = {"events": len(one), "built": sum(r["built"] for r in one),
                                    "stable_built": sum(r["stable"] for r in one),
                                    "line_proxy_matched": len(one_proxy)}
        rows.extend(one)
    reinforced = [r for r in rows if r["channel"] == "reinforce"]
    built = [r for r in reinforced if r["built"]]
    stable = [r for r in built if r["stable"]]
    for row in rows:
        counts["attempts"] += 1
        counts["channel_" + row["channel"]] += 1
        counts["outcome_" + row["outcome"]] += 1
        if row["built"]:
            counts["built"] += 1
        if row["stable"]:
            counts["stable_built"] += 1
        if row["duplicate"]:
            counts["duplicates"] += 1
        if row["complete"]:
            counts["complete_four_core_events"] += 1
    for r in reinforced:
        counts["reinforce_planned_units_known"] += r["planned_units"] is not None
        counts["reinforce_v161_model_known"] += r["model_total_profit"] is not None
        counts["reinforce_calibrated_profit_known"] += r["calibrated_profit"] is not None
        counts["reinforce_decision_fund_score_known"] += r["fund_score_stored"] is not None
        counts["reinforce_kdec_stale_tick"] += r["k_dec_tick_lag"] is not None and r["k_dec_tick_lag"] > 0
        counts["reinforce_fund_score_c69_exact"] += r["fund_score_matches_c69"] is True
    counts["reinforce_built"] = len(built)
    counts["reinforce_built_added_one_or_more"] = sum(r["added"] is not None and r["added"] > 0 for r in built)
    counts["reinforce_built_replaced_only"] = sum(r["added"] == 0 and r["replaced"] is not None
                                                and r["replaced"] > 0 for r in built)
    counts["reinforce_stable_built"] = len(stable)
    counts["reinforce_built_unstable"] = len(built) - len(stable)
    counts["line_proxy_matched"] = len(proxies)
    result = {
        "scope": "descriptive_existing_shadow_only", "files": len(paths),
        "counts": dict(counts), "by_file": by_file,
        "reinforce_all": {"n": len(reinforced), "model_roi_median_pm": med(reinforced, "model_roi_pm"),
                          "published_roi_median_pm": med(reinforced, "published_roi_pm"),
                          "calibrated_roi_median_pm": med(reinforced, "calibrated_roi_pm"),
                          "cap_ratio_median": med(reinforced, "cap_ratio"),
                          "cap_ratio_p10": percentile(reinforced, "cap_ratio", .1),
                          "cap_ratio_p90": percentile(reinforced, "cap_ratio", .9),
                          "calibration_ratio_median": med(reinforced, "calibration_ratio"),
                          "model_vs_cap_profit_median": med([
                              {"gap": r["model_total_profit"] - r["raw_profit"]}
                              for r in reinforced if r["model_total_profit"] is not None
                              and r["raw_profit"] is not None], "gap"),
                          "rank_median": med(reinforced, "rank"),
                          "k_dec_tick_lag_median": med(reinforced, "k_dec_tick_lag"),
                          "stored_minus_recomputed_score_median": med([
                              {"error": r["fund_score_stored"] - r["fund_roi_recomputed_pm"]}
                              for r in reinforced if r["fund_score_stored"] is not None
                              and r["fund_roi_recomputed_pm"] is not None], "error"),
                          "cash_delta_post_median_built": med(built, "cash_delta_post"),
                          "spend_median_built": med(built, "spend")},
        "reinforce_built": {"n": len(built), "cap_ratio_median": med(built, "cap_ratio"),
                            "published_roi_median_pm": med(built, "published_roi_pm"),
                            "model_roi_median_pm": med(built, "model_roi_pm"),
                            "calibrated_roi_median_pm": med(built, "calibrated_roi_pm")},
        "reinforce_stable_built": {"n": len(stable), "cap_ratio_median": med(stable, "cap_ratio"),
                                   "published_roi_median_pm": med(stable, "published_roi_pm")},
        "by_v161_source": grouped(reinforced, "v161_source"),
        "by_planned_units": grouped(reinforced, "planned_units"),
        "by_growth_history_proxy": grouped(reinforced, "growth_history_bucket"),
        "by_year": grouped(reinforced, "year"),
        "by_rank": grouped(reinforced, "rank"),
        "post_purchase_line_proxy": {"matched": len(proxies),
             "observed_line_delta_median": med(proxies, "observed_line_delta"),
             "prediction_minus_line_delta_median": med(proxies, "error_line_proxy"),
             "with_negative_line_delta": sum(r["observed_line_delta"] < 0 for r in proxies),
             "stable_matches": sum(r["stable"] for r in proxies),
             "economic_attribution": None},
        "decision_dimension_coverage": {
            "planes_before_exact": sum(r["values"]["vehCount"] is not None for r in roi_rows),
            "saturation": sum(r["values"]["waitPaxA"] is not None for r in roi_rows),
            "capacity": sum(r["values"]["planeCapacity"] is not None for r in roi_rows),
            "line_age_days": sum(r["values"]["lineAgeDays"] is not None for r in roi_rows),
            "cycle_days": sum(r["values"]["lastHistoricalCycleDays"] is not None for r in roi_rows),
            "competitor_pressure": sum(r["values"]["rivalCapacity"] is not None for r in roi_rows),
            "line_arm": sum(r["values"]["c121Arm"] is not None for r in roi_rows),
        },
        "air_roi_renfort1": {
            "episodes": len(roi_rows),
            "complete": sum(bool(r["complete"]) for r in roi_rows),
            "same_tick": sum(r["same_tick"] is True for r in roi_rows),
            "successful_additions": sum((r["values"]["added"] or 0) > 0 for r in roi_rows),
            "field_coverage": {
                key: sum(r["values"][key] is not None for r in roi_rows)
                for key in sorted(ROI_FIELDS)
            },
            "actual_cost_observed": sum(r["values"]["actualCost"] is not None for r in roi_rows),
            "actual_cost_on_successful_addition": sum(
                (r["values"]["added"] or 0) > 0 and r["values"]["actualCost"] is not None
                for r in roi_rows),
            "causal_incremental_profit": None,
        },
        "unobservable": {"true_aircraft_count_at_buy": None, "capacity_saturation_at_buy": None,
                         "age_rotation_competition_line_type_at_buy": None,
                         "actual_invoice_per_plane": None, "marginal_profit_with_same_save_control": None},
    }
    if include_episodes:
        # Inclut les tentatives refusées et les clichés instables; les manquants
        # restent null, sans remplissage depuis une autre graine ou année.
        result["episodes"] = rows
        result["air_roi_renfort1"]["details"] = roi_rows
    return result


def reference_panel(paths):
    """Autre cohorte; aucune jointure entre un achat shadow et une référence."""
    buys = []
    exact_before = []
    for path in paths:
        for line in Path(path).open(encoding="utf-8", errors="replace"):
            m = EVENT.search(line)
            if not m:
                continue
            date, kind, payload = m.groups()
            f = fields(payload)
            if kind == "FLEET_PROJECT" and f.get("action") == "grow":
                buys.append({"date": date, "roi": numeric(f, "roi"),
                             "model": numeric(f, "v161_model"), "price": numeric(f, "price"),
                             "v161_source": f.get("v161_src", "unknown")})
            elif kind == "AIR_FLEET" and f.get("action") == "grow":
                n = numeric(f, "planes_before")
                if n is not None:
                    exact_before.append(n)
    return {"scope": "independent_reference_no_shadow_join", "files": len(paths),
            "fleet_projects_built": len(buys), "fleet_roi_stored_median_pm": med(buys, "roi"),
            "fleet_model_roi_median_pm": med([
                {"roi": r["model"] * 1000 / r["price"]} for r in buys
                if r["model"] is not None and r["price"] and r["price"] > 0], "roi"),
            "fleet_by_v161_source": dict(Counter(r["v161_source"] for r in buys)),
            "legacy_air_fleet_growth_with_planes_before": len(exact_before),
            "legacy_planes_before_histogram": dict(sorted(Counter(int(n) for n in exact_before).items())),
            "caution": "AIR_FLEET legacy growth is a distinct channel; counts do not label portfolio purchases."}


def expand(patterns):
    return sorted({Path(p) for pat in patterns for p in glob.glob(pat) if Path(p).is_file()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patterns", nargs="+", help="AIRF1 shadow log files/globs")
    parser.add_argument("--reference", action="append", default=[],
                        help="Optional independent reference panel (glob, repeatable)")
    parser.add_argument("--details", action="store_true",
                        help="Include every individual attempt with provenance and missing fields")
    args = parser.parse_args()
    paths = expand(args.patterns)
    if not paths:
        parser.error("no matching shadow logs")
    out = summarize_shadow(paths, include_episodes=args.details)
    refs = expand(args.reference)
    if refs:
        out["separate_reference_panel"] = reference_panel(refs)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
