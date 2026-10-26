"""Fail-closed DIST-BORNES-1 V276 physical exposure from paired engine logs.

This identifies constructed freight pairs OUTSIDE the historic V276 band,
requiring the same exact pair in prior PROJECT_CHOSEN and successful
RAIL_ATTEMPT records. Differences *inside* the historical band do not qualify.
Run only on an already completed, frozen C66.4 campaign.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path


EVENT = re.compile(r"\bOPEX\s+(\d{4})-(\d{1,2})-(\d{1,2})\s+([A-Z][A-Z0-9_]+)\s+(.*)")
FIELD = re.compile(r"([A-Za-z_]+)=([^\s]+)")


def events(path):
    with Path(path).open(encoding="utf-8", errors="replace") as stream:
        for row in stream:
            match = EVENT.search(row)
            if match is None:
                continue
            date = tuple(int(match.group(i)) for i in (1, 2, 3))
            yield date, match.group(4), dict(FIELD.findall(match.group(5)))


def pair_key(fields):
    if not all(key in fields for key in ("src", "dst")):
        return None
    try:
        return int(fields["src"]), int(fields["dst"])
    except ValueError:
        return None


def read_log(path):
    bounds = []
    choices = {}
    attempts = {}
    constructed = []
    raw_builds = []
    counts = Counter()
    for date, event, fields in events(path):
        counts[event] += 1
        if event == "EPOCH_BOUNDS":
            try:
                bounds.append((date, int(fields["railMin"]), int(fields["railMax"])))
            except (KeyError, ValueError):
                pass
        if event == "PROJECT_CHOSEN" and fields.get("mode") == "rail" and fields.get("kind") == "freight":
            key = pair_key(fields)
            if key is not None:
                choices.setdefault((key, fields.get("cargo")), []).append(date)
        if event == "RAIL_ATTEMPT" and fields.get("kind") == "freight" and fields.get("ok") == "1":
            key = pair_key(fields)
            if key is not None:
                try:
                    attempts[(date, key)] = int(fields["manh"])
                except (KeyError, ValueError):
                    pass
        if event == "RAIL_BUILD":
            key = pair_key(fields)
            current_bounds = [(minimum, maximum) for bdate, minimum, maximum in bounds if bdate <= date]
            try:
                distance = int(fields["dist"])
            except (KeyError, ValueError):
                distance = None
            if current_bounds and distance is not None:
                minimum, maximum = current_bounds[-1]
                raw_builds.append({"date": "-".join(str(x) for x in date),
                                   "src": key[0] if key else None,
                                   "dst": key[1] if key else None,
                                   "cargo": fields.get("cargo"),
                                   "distance": distance,
                                   "outside_historical_v276": distance < minimum or distance > maximum})
            else:
                raw_builds.append({"date": "-".join(str(x) for x in date),
                                   "outside_historical_v276": None})
            if key is None:
                continue
            candidate = attempts.get((date, key))
            choice = choices.get((key, fields.get("cargo")), [])
            if candidate is None or not any(t <= date for t in choice):
                continue
            current_bounds = [(minimum, maximum) for bdate, minimum, maximum in bounds if bdate <= date]
            if not current_bounds:
                continue
            minimum, maximum = current_bounds[-1]
            constructed.append({"date": "-".join(str(x) for x in date), "src": key[0], "dst": key[1],
                                "cargo": fields.get("cargo"), "manhattan": candidate,
                                "rail_min": minimum, "rail_max": maximum,
                                "outside_historical_v276": candidate < minimum or candidate > maximum})
    return {"bounds_count": len(bounds), "v276_publishes": counts["V276_PUBLISH"],
            "v269_events": counts["V269"], "rail_attempts": counts["RAIL_ATTEMPT"],
            "rail_builds": counts["RAIL_BUILD"], "freight_joined": constructed,
            "raw_builds": raw_builds}


def assess(directory, seeds):
    summary = {}
    exposed = []
    incomplete = []
    unlinked_potential = []
    unknown_distance = []
    for seed in seeds:
        arms = {}
        for arm in ("reference", "dist_bornes_unified"):
            path = Path(directory) / f"{arm}_seed{seed}_r0.log"
            if not path.is_file():
                incomplete.append(str(path))
                continue
            arms[arm] = read_log(path)
        if len(arms) < 2:
            continue
        ref_pairs = {(r["src"], r["dst"], r["cargo"]) for r in arms["reference"]["freight_joined"]}
        new_candidates = [line for line in arms["dist_bornes_unified"]["freight_joined"]
                          if line["outside_historical_v276"]
                          and (line["src"], line["dst"], line["cargo"]) not in ref_pairs]
        all_builds = arms["dist_bornes_unified"]["raw_builds"]
        if any(line["outside_historical_v276"] is None for line in all_builds):
            unknown_distance.append(seed)
        if any(line["outside_historical_v276"] for line in all_builds):
            # Even without a join, an outside-band construction might be the
            # target. It remains unproven until linked with the V276 source.
            unlinked_potential.append(seed)
        # V276_PUBLISH only establishes a live V276 pipeline, and still does not
        # record the admission of a specific pair. Conservatively label an
        # outside-band build "potential", never proven, in absence of the
        # producer-path identity linking a V276 enumeration to that pair.
        # No pair-specific V276 admission event exists in these engine logs.
        # A positive candidate is therefore undecidable, and a total absence
        # of potential outside-band builds proves the exposure gate failed.
        proven = []
        summary[str(seed)] = {"arms": {arm: {k: v for k, v in row.items() if k != "freight_joined"}
                                       for arm, row in arms.items()},
                              "newly_built_outside_historical_band_potential": new_candidates,
                              "physically_proven_v276_admissions": proven}
    return {"schema": "dist_bornes_unified_exposure_v1", "seeds_requested": seeds,
            "missing_logs": incomplete, "per_seed": summary,
            "verified_exposure_seeds": exposed,
            "unlinked_potential_seeds": sorted(set(unlinked_potential)),
            "unknown_build_distance_seeds": unknown_distance,
            "verdict": ("INCONCLUSIVE" if incomplete or unlinked_potential or unknown_distance else
                        "EXPOSED" if len(exposed) >= 2 else "NO_GO_NON_EXPOSE"),
            "limitation": ("V276_PUBLISH has no per-pair identity. A build outside the old band "
                           "alone cannot prove V276-origin admission; unlinked cases are only potential.")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 100, 7, 999, 2026])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Rapport existant, ne pas écraser")
    result = assess(args.engine_dir, args.seeds)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exposition vérifiée : {len(result['verified_exposure_seeds'])}/{len(args.seeds)} — {result['verdict']}")
    for seed, data in result["per_seed"].items():
        print(f"seed={seed}: hors-bande construit potentiels="
              f"{len(data['newly_built_outside_historical_band_potential'])}, "
              f"confirmés={len(data['physically_proven_v276_admissions'])}")
    if result["missing_logs"]:
        print(f"Journaux manquants: {len(result['missing_logs'])}")


if __name__ == "__main__":
    main()
