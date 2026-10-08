"""Compare NoAI-accessible town-production history to external station arrivals.

Frozen coverage/rating proxies, NOT the full current C121 fleet evaluator.
Town Supplied counts all companies and is not assigned to an Opex station.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path

from analyse_c121_pax_flux import numeric_fields
from analyse_station_supply import analyse, metrics


def qualified_town_rows(snapshot):
    """A malformed other town/cargo cannot invalidate a qualified row.

    The collector validates each emitted row independently and omits invalid
    rows. Its global status reports completeness, not validity of emitted rows.
    Revalidate here so malformed checkpoint data cannot become an AI feature.
    """
    for town in snapshot.get("towns", []):
        if not isinstance(town, dict):
            continue
        fields = ("town", "cargo", "production", "supplied_all_companies")
        if not all(isinstance(town.get(k), int) and not isinstance(town[k], bool)
                   and town[k] >= 0 for k in fields):
            continue
        if town["supplied_all_companies"] <= town["production"]:
            yield town


def production_features(history, anchor):
    """Only observations already available before the forecast date.

    Deduplicate by real closed economy month, not calendar checkpoint month.
    Require 12 consecutive valid months; never expose the save's hidden history.
    """
    available = {h["closed_month"]: h for h in history if h["available_month"] < anchor}
    if not available:
        return None
    last = max(available)
    past = [available.get(m) for m in range(last - 11, last + 1)]
    if any(h is None for h in past):
        return None
    return {"production_last": past[-1]["production"],
            "production_mean12": sum(h["production"] for h in past) / 12,
            "latest_closed_month": last,
            "supplied_all_companies_mean12": sum(h["supplied_all_companies"] for h in past) / 12}


def town_analysis(path):
    base = analyse(path)
    bench = json.loads(path.read_text(encoding="utf8"))
    history = defaultdict(list)
    versions, snapshot_status = set(), Counter()
    with path.with_suffix(".jsonl").open(encoding="utf8") as handle:
        for text in handle:
            row = json.loads(text)
            if row["company_slot"] != 0:
                continue
            versions.add(row.get("savegame_version"))
            snapshot = row.get("town_month", {})
            snapshot_status[str(snapshot.get("ok"))] += 1
            calendar = date.fromisoformat(row["date"])
            economy = date.fromordinal(row["station_supply"]["economy_date"] - 365)
            available_month = calendar.year * 12 + calendar.month
            closed_month = economy.year * 12 + economy.month - 1
            for town in qualified_town_rows(snapshot):
                history[(row["game_id"], town["town"], town["cargo"])].append({
                    **town, "available_month": available_month, "closed_month": closed_month})
    builds, cargo_ids = {}, {}
    import re
    for game in bench["games"]:
        log = path.parent / "bench_engine" / Path(game["engine_log_path"]).name
        text = log.read_text(encoding="utf8")
        ids = {int(m) for m in re.findall(r"\[1\] \[I\].*?\bid:(\d+) .*?label:PASS\b", text)}
        if len(ids) != 1:
            raise ValueError("PASS identity unknown")
        cargo_ids[game["game_id"]] = ids.pop()
        for line in text.splitlines():
            if "[0] [I] C121_BUILD " not in line:
                continue
            f = numeric_fields(line.split("C121_BUILD ", 1)[1])
            if f.get("new_airports") != 2:
                continue
            for end in ("a", "b"):
                required = ("station_id_", "town_", "pax_produced_", "pax_town_tiles_", "pax_union_tiles_", "rating_pax_", "pax_raw_")
                if not all(isinstance(f.get(k + end), (int, float)) for k in required):
                    continue
                builds.setdefault((game["game_id"], int(f["station_id_" + end])), {
                    "town": int(f["town_" + end]), "produced": f["pax_produced_" + end],
                    "town_tiles": f["pax_town_tiles_" + end], "union_tiles": f["pax_union_tiles_" + end],
                    "rating": f["rating_pax_" + end], "raw": f["pax_raw_" + end]})
    cases, excluded = [], Counter()
    for case in base["cases"]:
        key = (case["game_id"], case["station"])
        build = builds.get(key)
        if not build or build["town_tiles"] <= 0:
            excluded["missing_build_geometry"] += 1
            continue
        fraction = min(1, build["union_tiles"] / build["town_tiles"])
        if abs(fraction * build["produced"] - build["raw"]) > 1.00001:
            excluded["build_raw_geometry_mismatch"] += 1
            continue
        h = history[(case["game_id"], build["town"], cargo_ids[case["game_id"]])]
        features = production_features(h, case["anchor_year"] * 12 + 1)
        if features is None:
            excluded["missing_12_consecutive_past_town_months"] += 1
            continue
        scale = fraction * (build["rating"] + 1) / 256
        cases.append({**case, **features, "town": build["town"], "coverage_fraction_initial": fraction,
                      "town_production_latest": scale * features["production_last"],
                      "town_production_mean12": scale * features["production_mean12"]})
    reserved = [c for c in cases if c["seed"] in (73, 314, 512)]
    development = [c for c in cases if c["seed"] not in (73, 314, 512)]
    predictors = ("initial_offered_proxy", "town_production_latest", "town_production_mean12", "past_supply_oracle")
    return {"campaign": base["campaign"], "bundle_sha256": base["bundle_sha256"],
            "manifest_sha256": base["manifest_sha256"], "checkpoint_sha256": base["checkpoint_sha256"],
            "log_hashes": base["log_hashes"], "healthy_complete": base["healthy_complete"],
            "savegame_versions": sorted(v for v in versions if v is not None),
            "town_snapshot_status": dict(snapshot_status), "base_cases": len(base["cases"]),
            "case_exclusions": dict(excluded), "status": "exploratory_partial_year_fixed_geometry",
            "development": {p: metrics(development, p) for p in predictors},
            "reserved": {p: metrics(reserved, p) for p in predictors},
            "cases": cases, "economic_verdict": "not_evaluated"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bench", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = town_analysis(args.bench)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k not in ("cases", "log_hashes")}, indent=2))


if __name__ == "__main__":
    main()
