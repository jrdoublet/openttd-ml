"""AIR-ROI-LIGNE-1: auditer les jointures des nouvelles lignes, hors moteur.

Le capital AIR_BUILD est journalise apres construction et peut inclure les
depenses AIAccounting reconciliees ; il n'isole pas le CAPEX net du site.
PROJECT_CHOSEN est lui aussi emis apres le chantier. Ces donnees et
LINE_REVENUE ne mesurent pas un ROI marginal ; l'outil distingue la flotte
initiale de la flotte observee.

Usage: python -X utf8 sweeps/diag_air_roi_ligne_coverage.py
           --logs results/.../calib_duel_40x10_pc_20261021_engine
           --out results/air_roi_ligne_coverage_20261025.json
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

try:
    from sweeps.analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, num, open_text
except ModuleNotFoundError:
    from analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, num, open_text


LINE_ID_RE = re.compile(r"(?:0|[1-9][0-9]*)\Z")


def analyse_log(lines, with_arms=False):
    """Return exact-day choices, builds, mature reports, and join limitations."""
    choices = {}
    builds = {}
    counts = Counter()
    mature_per_line_year = {}
    for raw in lines:
        found = LINE_RE.search(raw)
        if not found:
            continue
        date = (int(found.group(1)), int(found.group(2)), int(found.group(3)))
        tag = found.group(4)
        if tag not in ("PROJECT_CHOSEN", "AIR_BUILD", "LINE_REVENUE"):
            continue
        kv = dict(KV_RE.findall(found.group(5)))
        if tag == "PROJECT_CHOSEN" and kv.get("mode") == "air":
            choices[(kv.get("src"), kv.get("dst"))] = (date, kv)
        elif tag == "AIR_BUILD":
            counts["air_build_events"] += 1
            line_id = kv.get("line")
            if line_id is None or LINE_ID_RE.fullmatch(line_id) is None or line_id in builds:
                counts["invalid_or_reused_line_id"] += 1
                continue
            postbuild_capital = num(kv.get("cost"))
            init_fleet = num(kv.get("planes"))
            key = (kv.get("src"), kv.get("dst"))
            chosen = choices.get(key)
            same_day = bool(chosen and chosen[0] == date)
            if same_day:
                counts["matched_choice_same_day"] += 1
                choices.pop(key)
            else:
                counts["no_exact_day_choice"] += 1
            builds[line_id] = {
                "date": date, "arm": kv.get("arm", "unknown"),
                "postbuild_capital": postbuild_capital, "initial_planes": init_fleet,
                "choice_profit": num(chosen[1].get("profit")) if same_day else None,
                "choice_cost": num(chosen[1].get("cost")) if same_day else None,
                "choice_matched": same_day,
                "mature_years": set(), "fleet_drift_years": set(),
                "fleet_unknown_years": set(),
            }
        elif tag == "LINE_REVENUE" and kv.get("mode") == "air":
            counts["air_revenue_events"] += 1
            age = num(kv.get("age"))
            if age is None:
                counts["invalid_age_revenue_events"] += 1
                continue
            if age < 2:
                counts["censored_immature_events"] += 1
                continue
            counts["mature_revenue_events"] += 1
            line_id = kv.get("line")
            if line_id is None or LINE_ID_RE.fullmatch(line_id) is None:
                counts["mature_invalid_line_id"] += 1
                continue
            if line_id not in builds:
                counts["mature_without_build"] += 1
                continue
            year = num(kv.get("year"))
            if year is None or not year.is_integer():
                counts["mature_invalid_year"] += 1
                continue
            year = int(year)
            key = (line_id, year)
            if key in mature_per_line_year:
                counts["duplicate_line_year"] += 1
                continue
            mature_per_line_year[key] = True
            b = builds[line_id]
            b["mature_years"].add(year)
            observed_fleet = num(kv.get("vehs"))
            if observed_fleet is None or b["initial_planes"] is None:
                b["fleet_unknown_years"].add(year)
            elif observed_fleet != b["initial_planes"]:
                b["fleet_drift_years"].add(year)
            if num(kv.get("real_prof")) is None or num(kv.get("pred_prof")) is None:
                counts["mature_missing_profit"] += 1
    counts["air_builds_distinct"] = len(builds)
    counts["builds_with_mature_report"] = sum(bool(b["mature_years"]) for b in builds.values())
    counts["builds_without_mature_report"] = sum(not b["mature_years"] for b in builds.values())
    counts["builds_with_fleet_drift"] = sum(bool(b["fleet_drift_years"]) for b in builds.values())
    counts["mature_line_years_joined"] = len(mature_per_line_year)
    counts["mature_line_years_fleet_drift"] = sum(len(b["fleet_drift_years"]) for b in builds.values())
    counts["mature_line_years_fleet_unknown"] = sum(len(b["fleet_unknown_years"]) for b in builds.values())
    counts["builds_postbuild_capital_present"] = sum(
        b["postbuild_capital"] is not None for b in builds.values()
    )
    counts["observed_net_infrastructure_capex"] = 0  # not separable from AIR_BUILD.cost
    counts["observed_marginal_counterfactual"] = 0  # not emitted by LINE_REVENUE
    if not with_arms:
        return dict(counts)
    arms = defaultdict(Counter)
    for build in builds.values():
        arm = arms[build["arm"]]
        mature = build["mature_years"]
        drift = build["fleet_drift_years"]
        unknown = build["fleet_unknown_years"]
        arm["builds"] += 1
        arm["builds_with_mature_report"] += bool(mature)
        arm["builds_without_mature_report"] += not bool(mature)
        arm["builds_with_fleet_count_drift"] += bool(drift)
        arm["mature_line_years"] += len(mature)
        arm["mature_line_years_fleet_count_drift"] += len(drift)
        arm["mature_line_years_fleet_count_unknown"] += len(unknown)
        arm["mature_line_years_same_fleet_count"] += len(mature - drift - unknown)
        arm["postbuild_capital_present"] += build["postbuild_capital"] is not None
    return dict(counts), {key: dict(value) for key, value in sorted(arms.items())}


def analyse_directory(path: Path):
    files = sorted(p for p in path.iterdir() if p.is_file() and (p.name.endswith(".log") or p.name.endswith(".log.gz")))
    if not files:
        raise ValueError(f"aucun log moteur : {path}")
    games = {}
    source_hashes = {}
    for file in files:
        base = file.name[:-3] if file.name.endswith(".gz") else file.name
        m = SEED_RE.search(base)
        if not m:
            continue
        key = (base.split("_seed")[0], int(m.group(1)), int(m.group(2)))
        with open_text(str(file)) as handle:
            raw_text = handle.read()
        digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        if key in source_hashes:
            if source_hashes[key] != digest:
                raise ValueError(f"copies de partie contradictoires : {key}")
            continue
        source_hashes[key] = digest
        audit, arms = analyse_log(raw_text.splitlines(keepends=True), with_arms=True)
        games[key] = (audit, arms)
    if not games:
        raise ValueError(f"aucun fichier seed lisible : {path}")
    totals = Counter()
    by_arm = defaultdict(Counter)
    for audit, arms in games.values():
        totals.update(audit)
        for arm, row in arms.items():
            by_arm[arm].update(row)
    if sum(row["builds"] for row in by_arm.values()) != totals["air_builds_distinct"]:
        raise ValueError("AIR-ROI-LIGNE: ventilation des constructions incoherente")
    if sum(row["mature_line_years"] for row in by_arm.values()) != totals["mature_line_years_joined"]:
        raise ValueError("AIR-ROI-LIGNE: ventilation des releves matures incoherente")
    return {
        "n_games": len(games),
        "seeds": sorted({key[1] for key in games}),
        "counts": dict(sorted(totals.items())),
        "by_build_arm": {arm: dict(sorted(row.items())) for arm, row in sorted(by_arm.items())},
        "limitations": [
            "AIR_BUILD.cost is post-construction capital, potentially reconciled with "
            "AIAccounting; no isolated net infrastructure CAPEX is observed",
            "LINE_REVENUE.real_prof is whole-line profit, not an incremental counterfactual",
            "No construction-free controls or opportunity cost observations",
            "Fleet expansion/replacement confounds gross line-profit comparisons",
            "Fleet equality refers only to aircraft counts at yearly snapshots, not "
            "aircraft identity or model; missing counts are not treated as drift",
            "Build-arm categories describe already constructed lines, not profitability "
            "or physical incremental airport construction cost",
            "Same-day source/destination association is diagnostic, not a causal identity",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("refuse d'ecraser un resultat existant")
    result = analyse_directory(args.logs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
