"""AIR-FLOTTE-1: retrospective, non-causal AIR/RAIL opportunity audit.

Usage (no OpenTTD run):
    python -B sweeps/analyze_air_flotte1.py "results/.../reference_seed*_r0.log"

Only contemporaneous *calendar dates* are joined. PORTFOLIO_RANK is top-five,
not an atomic list of projects displaced by an AIR purchase. C121's observed
delta is a whole-line before/after proxy, not an identified marginal effect.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import glob
import json
from pathlib import Path
import re
from statistics import median


EVENT = re.compile(r"OPEX (\d{4}-\d{1,2}-\d{1,2}) ([A-Z0-9_]+) (.*)")
FIELDS = re.compile(r"(\w+)=([^ ]+)")
SEED = re.compile(r"(?:reference|rail_cal_1)_seed([^_]+)_r\d+\.log$")


def parse_fields(message: str) -> dict[str, str]:
    return dict(FIELDS.findall(message))


def number(row: dict[str, str], key: str) -> int | None:
    try:
        return int(row[key])
    except (KeyError, TypeError, ValueError):
        return None


def median_or_none(values):
    return median(values) if values else None


def analyze_log(path: Path) -> dict:
    match = SEED.search(path.name)
    seed = match.group(1) if match else path.name
    counts = Counter()
    rail_by_day = defaultdict(list)
    last_growth = {}
    renewal_serial = Counter()
    fleet = []
    renewals = []
    rail_builds = set()
    matched_marginals = []
    marginal_links_after_renewal = 0
    previous_rank_date = None
    previous_rank_block = []
    prior_rank_at_fleet = []
    prior_rank_at_renewal = []

    with path.open("r", encoding="utf-8", errors="replace") as source:
        for line in source:
            match = EVENT.search(line)
            if match:
                date, kind, payload = match.groups()
                fields = parse_fields(payload)
                if kind == "PORTFOLIO_RANK":
                    counts["portfolio_top5_rows"] += 1
                    if fields.get("rank") == "0" or previous_rank_date != date:
                        previous_rank_block = []
                    previous_rank_date = date
                    previous_rank_block.append(fields)
                    if fields.get("mode") == "rail":
                        rail_by_day[date].append(fields)
                elif kind == "FLEET_PROJECT" and fields.get("action") == "grow":
                    added = number(fields, "added")
                    if added is not None and added > 0:
                        counts["air_reinforcements"] += 1
                        event = {"date": date, "year": int(date[:4]),
                                 "line": fields.get("line"),
                                 "roi": number(fields, "roi"),
                                 "profit": number(fields, "profit"),
                                 "capital": number(fields, "price"),
                                 "raw_model": number(fields, "v161_model")}
                        fleet.append(event)
                        last_growth[event["line"]] = (event, renewal_serial[event["line"]])
                        prior_rank_at_fleet.append(
                            list(previous_rank_block) if previous_rank_date == date else [])
                elif kind == "V252_REPLACE":
                    counts["air_renewals"] += 1
                    renewals.append(date)
                    renewal_serial[fields.get("line")] += 1
                    prior_rank_at_renewal.append(
                        list(previous_rank_block) if previous_rank_date == date else [])
                elif kind == "RAIL_BUILD":
                    counts["rail_builds"] += 1
                    rail_builds.add((date, fields.get("src"), fields.get("dst")))
            if "C121_FLEET_MARGINAL " in line:
                counts["marginal_observations"] += 1
                observation = parse_fields(line.split("C121_FLEET_MARGINAL ", 1)[1])
                lid = observation.get("line")
                observed_year = number(observation, "year")
                observed_profit = number(observation, "obs_profit")
                # The current marginal baseline is overwritten on each growth.
                # Use only the latest growth BEFORE this report line, not a
                # later purchase in that same calendar year.
                if lid in last_growth and observed_year is not None and observed_profit is not None:
                    purchase, old_serial = last_growth[lid]
                    if (purchase["year"] + 2 == observed_year
                            and number(observation, "added") == 1
                            and purchase["capital"] is not None and purchase["capital"] > 0):
                        if renewal_serial[lid] != old_serial:
                            marginal_links_after_renewal += 1
                        else:
                            matched_marginals.append({"predicted_roi": purchase["roi"],
                                                      "observed_profit_proxy": observed_profit,
                                                      "observed_roi_proxy": 1000 * observed_profit / purchase["capital"]})

    comparisons = []
    for event in fleet:
        rail = rail_by_day.get(event["date"], [])
        if not rail:
            continue
        # The best *ranking* candidate is not necessarily the highest raw ROI,
        # because the global rank already includes C77 priority tiers.
        ranked = [r for r in rail if number(r, "rank") is not None
                  and number(r, "roi") is not None]
        if not ranked or event["roi"] is None:
            continue
        best = min(ranked, key=lambda r: int(r["rank"]))
        comparisons.append({
            "air_roi": event["roi"], "best_rail_roi": int(best["roi"]),
            "any_rail_roi_higher": any(int(r["roi"]) > event["roi"] for r in ranked),
            "best_rail_built_same_day": (event["date"], best.get("src"),
                                          best.get("dst")) in rail_builds,
        })

    raw_roi = [1000 * e["raw_model"] / e["capital"] for e in fleet
               if e["raw_model"] is not None and e["capital"] is not None and e["capital"] > 0]
    fleet_rois = [e["roi"] for e in fleet if e["roi"] is not None]
    return {"seed": seed, "counts": dict(counts),
            "raw_roi": raw_roi, "fleet_rois": fleet_rois,
            "same_day": comparisons,
            "fleet_with_prior_rank_same_day": sum(bool(block) for block in prior_rank_at_fleet),
            "fleet_with_prior_rail_same_day": sum(any(r.get("mode") == "rail" for r in block)
                                                   for block in prior_rank_at_fleet),
            "renewals_with_rail_rank_same_day": sum(bool(rail_by_day.get(d)) for d in renewals),
            "renewals_with_prior_rail_same_day": sum(any(r.get("mode") == "rail" for r in block)
                                                      for block in prior_rank_at_renewal),
            "marginal_after_intervening_renewal_excluded": marginal_links_after_renewal,
            "marginal_matched": matched_marginals}


def summarize(logs: list[dict]) -> dict:
    totals = Counter()
    for log in logs:
        totals.update(log["counts"])
    fleet_rois = [v for log in logs for v in log["fleet_rois"]]
    raw_rois = [v for log in logs for v in log["raw_roi"]]
    compares = [v for log in logs for v in log["same_day"]]
    observed = [v for log in logs for v in log["marginal_matched"]]
    obs_roi = [o["observed_roi_proxy"] for o in observed]
    seed_medians = [median_or_none([o["observed_roi_proxy"] for o in log["marginal_matched"]])
                    for log in logs]
    return {
        "scope": "descriptive_only_no_counterfactual",
        "files": len(logs), "seeds": sorted(log["seed"] for log in logs),
        "events": dict(totals),
        "fleet_roi_v161_median_permille": median_or_none(fleet_rois),
        "fleet_roi_model_before_v161_median_permille": median_or_none(raw_rois),
        "fleet_buys_roi_lt_100_permille": sum(v < 100 for v in fleet_rois),
        "same_day_air_buy_and_top5_rail": len(compares),
        "same_day_best_ranked_rail_roi_gt_fleet": sum(v["best_rail_roi"] > v["air_roi"] for v in compares),
        "same_day_any_top5_rail_roi_gt_fleet": sum(v["any_rail_roi_higher"] for v in compares),
        "same_day_best_ranked_rail_built": sum(v["best_rail_built_same_day"] for v in compares),
        "fleet_with_preceding_portfolio_rank_same_day": sum(log["fleet_with_prior_rank_same_day"] for log in logs),
        "fleet_with_preceding_rail_rank_same_day": sum(log["fleet_with_prior_rail_same_day"] for log in logs),
        "same_day_renewal_and_top5_rail": sum(log["renewals_with_rail_rank_same_day"] for log in logs),
        "renewal_with_preceding_rail_rank_same_day": sum(log["renewals_with_prior_rail_same_day"] for log in logs),
        "two_year_air_c121_marginal_proxy_matched": len(observed),
        "two_year_air_c121_marginal_intervening_renewal_excluded": sum(log["marginal_after_intervening_renewal_excluded"] for log in logs),
        "two_year_air_c121_proxy_negative": sum(v["observed_profit_proxy"] < 0 for v in observed),
        "two_year_air_c121_proxy_profit_median": median_or_none([v["observed_profit_proxy"] for v in observed]),
        "two_year_air_c121_proxy_roi_median_permille": median_or_none(obs_roi),
        "two_year_air_c121_proxy_seed_medians_median_permille": median_or_none([v for v in seed_medians if v is not None]),
        "rail_unbuilt_two_year_realized_roi": None,
        "v252_predicted_incremental_roi": None,
        "contemporaneous_displacement_identified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patterns", nargs="+", help="Filename or glob; reference arm only for baseline")
    args = parser.parse_args()
    paths = sorted({Path(path) for pattern in args.patterns for path in glob.glob(pattern)})
    if not paths:
        parser.error("no log matches the input pattern")
    print(json.dumps(summarize([analyze_log(path) for path in paths]), indent=2,
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
