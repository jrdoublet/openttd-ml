"""Diagnostic / sonde C52 #7 : ET_STATION_FIRST_VEHICLE.

Mesure l'arrivee du premier vehicule sur chaque station pour etablir si les gares
fret sans note ont jamais ete desservies.
Parse les evenements :
  OPEX YYYY-MM-DD STATION_FIRST_VEHICLE station=X vehicle=Y mode=M kind=K cargo=C line=L rating=R tile=T
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    make_cfg,
    quarter_profit,
    write_json_atomically,
    year_profit,
)

ARM = "OpexAI[c52_station_first_vehicle_log=1]"
EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) STATION_FIRST_VEHICLE\s*(.*)$")


def parse_event_line(text):
    tokens = text.strip().split()
    fields = {}
    for tok in tokens:
        if "=" in tok:
            k, v = tok.split("=", 1)
            fields[k] = v
    return fields


def parse_station_first_vehicle_events(output):
    events = []
    for line in (output or "").splitlines():
        m = EVENT_RE.search(line)
        if m:
            date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            fields = parse_event_line(m.group(4))
            events.append({
                "date": date_str,
                "year": int(m.group(1)),
                "station": int(fields.get("station", -1)),
                "vehicle": int(fields.get("vehicle", -1)),
                "mode": fields.get("mode", "unknown"),
                "kind": fields.get("kind", "unknown"),
                "cargo": fields.get("cargo", "unknown"),
                "line": int(fields.get("line", -1)),
                "rating": int(fields.get("rating", -1)),
                "tile": int(fields.get("tile", -1)),
            })
    return events


def aggregate_events(events):
    by_mode = Counter()
    by_kind = Counter()
    by_cargo = Counter()
    distinct_stations = set()
    freight_stations = set()
    pax_stations = set()

    for ev in events:
        distinct_stations.add(ev["station"])
        by_mode[ev["mode"]] += 1
        by_kind[ev["kind"]] += 1
        by_cargo[ev["cargo"]] += 1
        if ev["kind"] == "freight":
            freight_stations.add(ev["station"])
        elif ev["kind"] == "pax":
            pax_stations.add(ev["station"])

    return {
        "total_first_arrivals": len(events),
        "distinct_stations_served": len(distinct_stations),
        "freight_stations_served": len(freight_stations),
        "pax_stations_served": len(pax_stations),
        "by_mode": dict(by_mode),
        "by_kind": dict(by_kind),
        "by_cargo": dict(by_cargo),
    }


def run_selftest():
    sample_log = """
OPEX 1970-3-15 STATION_FIRST_VEHICLE station=2 vehicle=10 mode=road kind=pax cargo=PASS line=1 rating=-1 tile=34470
OPEX 1970-3-22 STATION_FIRST_VEHICLE station=3 vehicle=11 mode=road kind=pax cargo=PASS line=1 rating=-1 tile=33448
OPEX 1970-5-10 STATION_FIRST_VEHICLE station=14 vehicle=21 mode=road kind=freight cargo=COAL line=4 rating=-1 tile=63104
OPEX 1970-5-28 STATION_FIRST_VEHICLE station=15 vehicle=22 mode=road kind=freight cargo=COAL line=4 rating=49 tile=62081
OPEX 1970-8-14 STATION_FIRST_VEHICLE station=20 vehicle=26 mode=rail kind=freight cargo=IRON line=5 rating=-1 tile=10868
"""
    events = parse_station_first_vehicle_events(sample_log)
    assert len(events) == 5
    assert events[0]["station"] == 2
    assert events[0]["vehicle"] == 10
    assert events[0]["mode"] == "road"
    assert events[0]["kind"] == "pax"
    assert events[0]["cargo"] == "PASS"
    assert events[0]["rating"] == -1

    assert events[3]["station"] == 15
    assert events[3]["rating"] == 49
    assert events[3]["kind"] == "freight"

    agg = aggregate_events(events)
    assert agg["total_first_arrivals"] == 5
    assert agg["distinct_stations_served"] == 5
    assert agg["freight_stations_served"] == 3
    assert agg["pax_stations_served"] == 2
    assert agg["by_mode"]["road"] == 4
    assert agg["by_mode"]["rail"] == 1
    assert agg["by_cargo"]["COAL"] == 2
    assert agg["by_cargo"]["PASS"] == 2
    assert agg["by_cargo"]["IRON"] == 1

    print("Selftest diag_c52_station_first_vehicle passed successfully!")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    print("Script de diagnostic C52 #7 pret. Utiliser --selftest pour verifier.")


if __name__ == "__main__":
    main()
