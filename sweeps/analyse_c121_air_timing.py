"""Diagnostic C121: decompose le timing AIR mesure sans calibrer l'IA.

Le runner C121 embarque les mesures ORDL issues de diag_airport_delay_engine:
travel_time (hors wait_time), wait_time, distance et vitesse API. Ce script
teste seulement la forme de l'erreur du modele physique:

    observed_travel_days ~= intercept + slope * flight_days_corrected

Les coefficients sont descriptifs et ne sont jamais utilises par OpexAI.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


def _stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
    values.sort()
    def q(frac):
        if len(values) == 1:
            return values[0]
        pos = frac * (len(values) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(values) - 1)
        part = pos - lo
        return values[lo] * (1.0 - part) + values[hi] * part
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p25": q(0.25),
        "p75": q(0.75),
    }


def _ols(rows):
    pairs = [
        (float(r["flight_days_corrected"]), float(r["observed_days"]))
        for r in rows
        if isinstance(r.get("flight_days_corrected"), (int, float))
        and isinstance(r.get("observed_days"), (int, float))
    ]
    if len(pairs) < 2:
        return {"n": len(pairs), "intercept_days": None, "slope": None}
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    xm = statistics.mean(xs)
    ym = statistics.mean(ys)
    denom = sum((x - xm) ** 2 for x in xs)
    slope = sum((x - xm) * (y - ym) for x, y in pairs) / denom if denom else None
    intercept = ym - slope * xm if slope is not None else None
    return {"n": len(pairs), "intercept_days": intercept, "slope": slope}


def _summary(rows):
    waits = [float(r.get("wait_ticks", 0)) / 74.0 for r in rows]
    delays = [
        float(r["observed_days"]) - float(r["flight_days_corrected"])
        for r in rows
        if isinstance(r.get("observed_days"), (int, float))
        and isinstance(r.get("flight_days_corrected"), (int, float))
    ]
    travel_ratio = [
        float(r["observed_days"]) / float(r["flight_days_corrected"])
        for r in rows
        if isinstance(r.get("observed_days"), (int, float))
        and isinstance(r.get("flight_days_corrected"), (int, float))
        and float(r["flight_days_corrected"]) > 0
    ]
    return {
        "n": len(rows),
        "distance": _stats([r.get("distance") for r in rows]),
        "flight_days": _stats([r.get("flight_days_corrected") for r in rows]),
        "travel_days": _stats([r.get("observed_days") for r in rows]),
        "wait_days": _stats(waits),
        "travel_minus_flight_days": _stats(delays),
        "travel_over_flight": _stats(travel_ratio),
        "ols_travel_vs_flight": _ols(rows),
    }


def analyse(payload):
    rows = []
    for checkpoint in payload.get("rows", []):
        seed = checkpoint.get("seed")
        for timing in checkpoint.get("timing_measurements", []):
            item = dict(timing)
            item["seed"] = seed
            rows.append(item)

    by_airport_pair = defaultdict(list)
    by_distance = defaultdict(list)
    by_load = defaultdict(list)
    for row in rows:
        a = row.get("src_airport_type")
        b = row.get("dst_airport_type")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            pair = tuple(sorted((int(a), int(b))))
            by_airport_pair[pair].append(row)
        d = row.get("distance")
        if isinstance(d, (int, float)):
            if d < 96:
                bucket = "<96"
            elif d < 160:
                bucket = "96-159"
            elif d < 224:
                bucket = "160-223"
            else:
                bucket = ">=224"
            by_distance[bucket].append(row)

        route_aircraft = int(row.get("route_aircraft") or 0)
        max_station_aircraft = max(
            int(row.get("src_station_aircraft") or 0),
            int(row.get("dst_station_aircraft") or 0),
        )
        max_station_routes = max(
            int(row.get("src_station_routes") or 0),
            int(row.get("dst_station_routes") or 0),
        )
        if route_aircraft <= 1 and max_station_aircraft <= 1 and max_station_routes <= 1:
            by_load["strict_uncontended"].append(row)
        if route_aircraft <= 1 and max_station_aircraft <= 2 and max_station_routes <= 2:
            by_load["light"].append(row)
        if max_station_aircraft >= 6 or max_station_routes >= 4:
            by_load["busy"].append(row)

    return {
        "source_campaign": payload.get("campaign_id"),
        "note": (
            "Diagnostic uniquement: OLS et medians servent a identifier si l'erreur "
            "est fixe (FTA/aeroport) ou proportionnelle au vol; aucun coefficient n'est "
            "injecte dans OpexAI."
        ),
        "overall": _summary(rows),
        "by_airport_pair": {
            f"{a}-{b}": _summary(group)
            for (a, b), group in sorted(by_airport_pair.items())
        },
        "by_distance": {
            key: _summary(by_distance[key])
            for key in ("<96", "96-159", "160-223", ">=224")
            if key in by_distance
        },
        "by_load": {
            key: _summary(by_load[key])
            for key in ("strict_uncontended", "light", "busy")
            if key in by_load
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyse(payload)
    out = args.out or args.input.with_name(args.input.stem + "_timing.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Sortie: {out}")


if __name__ == "__main__":
    main()
