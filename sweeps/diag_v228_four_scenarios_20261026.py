#!/usr/bin/env python3
"""V228: strictly descriptive four independent 20x10 C66.3 reference scenarios.

Three 256x256 worlds starting in 1950, 1970, 1990, and a 1024x1024
world starting in 1970. Shared seeds and frozen settings do NOT make
different worlds or dates paired counterfactuals. No causal/V102 verdict.

Usage:
  python sweeps/diag_v228_four_scenarios_20261026.py \
    --y1950 1950_256.json --y1970 1970_256.json \
    --y1990 1990_256.json --map1024 1970_1024.json --out report.json

This script never runs the engine. Each input must already exist and pass
the complete health, provenance, and final-checkpoint gate.
"""

import argparse
import json
from pathlib import Path
from statistics import median

try:
    from sweeps.diag_v228_map_coverage_20261025 import read_reference, summarize_map
except ModuleNotFoundError:
    # Direct script invocation from the sweeps directory.
    from diag_v228_map_coverage_20261025 import read_reference, summarize_map


SCENARIOS = (
    ("y1950", 1950, 8),
    ("y1970", 1970, 8),
    ("y1990", 1990, 8),
    ("map1024", 1970, 10),
)
SHARED_FIELDS = (
    "source_bundle_sha256", "policy_id", "policies", "arms", "design",
    "aaahogex_settings", "openttd_version", "opengfx_version",
)


def summarize_scenario(data, games):
    """Same V228 profit/ratio contract, with additional descriptive medians."""
    opex = [games[(seed, "OpexAI")] for seed in data["seeds"]]
    aaa = [games[(seed, "AAAHogEx")] for seed in data["seeds"]]
    result = summarize_map(data, games)
    result.update({
        "start_year": data["start_year"],
        "last_year": data["expected_last_year"],
        "last_checkpoint": data["expected_last_checkpoint"],
        "profit_year_median_opex": round(median(p["profit_year"] for p in opex), 2),
        "profit_year_median_aaahogex": round(median(p["profit_year"] for p in aaa), 2),
        "median_opex_vehicles": round(median(p["n_vehicles"] for p in opex), 2),
        "median_aaa_vehicles": round(median(p["n_vehicles"] for p in aaa), 2),
    })
    return result


def compare_four(y1950, y1970, y1990, map1024):
    """Compare only healthy, independently generated reference summaries."""
    locations = dict(zip(
        (entry[0] for entry in SCENARIOS),
        (y1950, y1970, y1990, map1024),
    ))
    sources = {}
    summaries = {}
    baseline = None
    seen_campaigns = set()
    for key, start_year, exponent in SCENARIOS:
        path = Path(locations[key])
        data, games = read_reference(path, expected_start_year=start_year)
        if data.get("map_size") != exponent:
            raise ValueError(f"{key} map_size doit valoir {exponent}")
        if any(field not in data or data[field] is None for field in SHARED_FIELDS):
            raise ValueError(f"provenance bundle/reglage/runtime incomplete : {key}")
        if data["campaign_id"] in seen_campaigns:
            raise ValueError(f"campaign_id reutilise entre scenarios : {key}")
        seen_campaigns.add(data["campaign_id"])
        if baseline is None:
            baseline = data
        else:
            for field in SHARED_FIELDS:
                if baseline.get(field) != data.get(field):
                    raise ValueError(f"bundle ou reglage divergent : {field} ({key})")
            if sorted(baseline["seeds"]) != sorted(data["seeds"]):
                raise ValueError(f"graines canoniques divergentes : {key}")
        sources[key] = {
            "json": str(path),
            "campaign_id": data["campaign_id"],
            "manifest_sha256": data["manifest_sha256"],
        }
        summaries[key] = summarize_scenario(data, games)
    return {
        "interpretation": (
            "Quatre references 20 graines x 10 ans independantes, descriptives "
            "uniquement; memes graines, bundle, politiques, reglages AAA et runtime. "
            "Un changement d'annee ou de carte modifie le monde genere. "
            "Aucun appariement contrefactuel, verdict V102 ni rendement causal."
        ),
        "source_bundle_sha256": baseline["source_bundle_sha256"],
        "openttd_version": baseline["openttd_version"],
        "opengfx_version": baseline["opengfx_version"],
        "seeds": sorted(baseline["seeds"]),
        "sources": sources,
        "scenarios": summaries,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--y1950", type=Path, required=True)
    parser.add_argument("--y1970", type=Path, required=True)
    parser.add_argument("--y1990", type=Path, required=True)
    parser.add_argument("--map1024", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error("ne pas ecraser un diagnostic existant")
    try:
        result = compare_four(args.y1950, args.y1970, args.y1990, args.map1024)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # x = atomic exclusive creation; guards against an output-file race.
    with args.out.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps(result["scenarios"], ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
