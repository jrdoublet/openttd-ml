"""FRONT-PAX-1: bornes certaines de la frontiere rail/air sur EPOCH_BOUNDS.

Le journal n'enregistre que vRail texte, vAir.tointeger(), tFixe.tointeger(),
tpd.tointeger(), et les bornes finales. Nous traitons les valeurs tronquees
comme des INTERVALLES (et jamais comme des valeurs physiques exactes).
Le resultat classe les bornes rail/air prouvables; il ne retrouve PAS le motif
roadMax=roadMin ni les bornes physiques AIR/RAIL manquantes.

Usage: python -X utf8 sweeps/diag_front_pax_clamp_bounds.py
       --logs results/.../calib_duel_40x10_pc_20261021_engine
       --logs results/.../calib_solo_40x10_pc_20261021_engine
       --out results/front_pax_clamp_certain_20261025.json
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import re


EVENT = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) EPOCH_BOUNDS\s+(.*)$")
FIELDS = re.compile(r"(\w+)=([^\s]+)")
GAME = re.compile(r"^(.*?)_seed(\d+)_r(\d+)\.log(?:\.gz)?$")
EPS = 0.01  # marge sur l'affichage vRail texte (Squirrel, precision limitee)


def _days_per_tile(speed, ticks_per_day):
    return 4096.0 / (ticks_per_day * 1.6 * speed)


def classify(event):
    """Return interval and only deductions valid for every input in interval.

    Positive vAir and tFixe are truncated with .tointeger(): physical value
    in [printed, printed+1). The vRail string is allowed ±0.01 km/h; tpd=74
    is exact in OpexTicksPerDay, checked against current source by tests.
    """
    required = ("roadMin", "roadMax", "railAir", "railMax", "vRail", "vAir", "tFixe", "tpd")
    try:
        values = {k: float(event[k]) for k in required}
    except (KeyError, ValueError, TypeError, OverflowError):
        return {"reason": "missing_or_invalid"}
    if not all(math.isfinite(v) for v in values.values()):
        return {"reason": "missing_or_invalid"}
    road_min = values["roadMin"]
    road_max = values["roadMax"]
    rail_air = values["railAir"]
    rail_max = values["railMax"]
    vr = values["vRail"]
    va = values["vAir"]
    fixed = values["tFixe"]
    tpd = values["tpd"]
    if (tpd != 74 or min(road_min, road_max, rail_air, rail_max) < 0 or rail_max < road_max):
        return {"reason": "unexpected_bounds_or_tpd"}
    if (vr <= EPS or va <= 0 or fixed < 0):
        return {"reason": "no_complete_vehicle_profile"}
    # Largest difference is slowest possible train vs fastest possible plane:
    # gives smallest raw rail/air crossover if positive.
    largest_diff = _days_per_tile(vr - EPS, tpd) - _days_per_tile(va + 1.0, tpd)
    smallest_diff = _days_per_tile(vr + EPS, tpd) - _days_per_tile(va, tpd)
    if largest_diff <= 0:
        # Air never faster, so the code returns the map Manhattan span. The
        # present map span isn't in these EPOCH_BOUNDS observations; do not
        # assert it was necessarily the railMax clamp.
        return {"reason": "train_always_as_fast_or_faster"}
    raw_lower = fixed / largest_diff
    # Truncation floors a positive raw crossover to an integer before clamps.
    if math.floor(raw_lower) > rail_max:
        return {"reason": ("proven_upper_rail_clamp" if rail_air == rail_max else
                           "conflict_with_final_bound"),
                "raw_distance_lower": round(raw_lower, 2),
                "raw_distance_upper": (round((fixed + 1.0) / smallest_diff, 2)
                                       if smallest_diff > 0 else None),
                "road_max_equals_min": road_max == road_min}
    if smallest_diff > 0:
        raw_upper = (fixed + 1.0) / smallest_diff
        if math.floor(raw_upper) < road_max:
            return {"reason": ("proven_lower_road_clamp" if rail_air == road_max else
                               "conflict_with_final_bound"),
                    "raw_distance_lower": round(raw_lower, 2),
                    "raw_distance_upper": round(raw_upper, 2)}
        return {"reason": "physical_interval_overlaps_clamp_or_final",
                "raw_distance_lower": round(raw_lower, 2),
                "raw_distance_upper": round(raw_upper, 2)}
    return {"reason": "physical_interval_unbounded_above",
            "raw_distance_lower": round(raw_lower, 2), "raw_distance_upper": None}


def analyse(logdirs):
    observations = Counter()
    years = defaultdict(Counter)
    raw_observations = Counter()
    raw_years = defaultdict(Counter)
    repeated_observations = Counter()
    repeated_years = defaultdict(Counter)
    examples = {}
    games = set()
    seen_event_keys = set()
    copied_sources = {}
    canonical_names = {}
    for folder in logdirs:
        folder = Path(folder)
        if not folder.is_dir():
            raise ValueError(f"dossier de journaux absent: {folder}")
        for path in sorted(folder.iterdir()):
            game = GAME.match(path.name)
            if game is None:
                continue
            # A copied .log and .log.gz may coexist. In order not to mask
            # contradictions, compare their EPOCH_BOUNDS lines exactly.
            # Canonical numeric identities prevent seed01/seed1 and r00/r0
            # from being counted as different independent games. Different
            # arms and directories remain separate experiments.
            stream_id = (str(folder.resolve()), game.group(1),
                         int(game.group(2)), int(game.group(3)))
            basename = path.name[:-3] if path.suffix == ".gz" else path.name
            previous = canonical_names.setdefault(stream_id, basename)
            if previous != basename:
                raise ValueError(f"identite de partie FRONT-PAX ambigue : {previous} et {basename}")
            events = []
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    m = EVENT.search(line)
                    if m:
                        events.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)))
            if stream_id in copied_sources:
                if copied_sources[stream_id] != events:
                    raise ValueError(f"copies contradictoires de EPOCH_BOUNDS: {path}")
                continue
            copied_sources[stream_id] = events
            games.add(stream_id)
            for year, month, day, payload in events:
                fields = dict(FIELDS.findall(payload))
                result = classify(fields)
                reason = result["reason"]
                raw_observations[reason] += 1
                raw_years[year][reason] += 1
                # Keep multiple genuinely distinct events on the same day,
                # but count re-emissions of the same day/payload separately
                # from the historical unique-state metric.
                event_id = (stream_id, year, month, day, payload)
                if event_id in seen_event_keys:
                    repeated_observations[reason] += 1
                    repeated_years[year][reason] += 1
                    continue
                seen_event_keys.add(event_id)
                observations[reason] += 1
                years[year][reason] += 1
                examples.setdefault(reason, {"date": f"{year}-{month:02d}-{day:02d}",
                                             "seed": int(game.group(2)),
                                             "source": path.name,
                                             "values": fields, "interpretation": result})
    if not games or not observations:
        raise ValueError("aucun EPOCH_BOUNDS interpretable dans les journaux fournis")
    return {
        "games": len(games), "events": sum(observations.values()),
        "raw_emissions": sum(raw_observations.values()),
        "same_day_same_payload_reemissions": sum(repeated_observations.values()),
        "reasons": dict(sorted(observations.items())),
        "years": {str(y): dict(sorted(row.items())) for y, row in sorted(years.items())},
        "raw_reasons": dict(sorted(raw_observations.items())),
        "raw_years": {str(y): dict(sorted(row.items())) for y, row in sorted(raw_years.items())},
        "reemission_reasons": dict(sorted(repeated_observations.items())),
        "reemission_years": {str(y): dict(sorted(row.items()))
                             for y, row in sorted(repeated_years.items())},
        "examples": examples,
        "proven_scope": "rail-air physical crossover vs upper railMax clamp only",
        "unknown_scope": [
            "Reason for roadMax=roadMin (vehicle availability, deltaM, numerator, denominator, or sub-minimum raw distance)",
            "Exact unrounded tFixe/vAir, airport type and economic effect",
            "Counterfactual newly executable RAIL PASS and non-building projects",
            "Rail freight is not governed by the rail-air passenger frontier",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("ne pas ecraser une sortie existante")
    report = analyse(args.logs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "games", "events", "raw_emissions", "same_day_same_payload_reemissions", "reasons")},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
