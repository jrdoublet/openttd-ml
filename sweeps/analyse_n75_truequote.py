"""Causal-exposure diagnostic for the opt-in AIR 1->2 fleet true quote.

Counts each fleet action once by (seed, arm, route), not recurring plan lines.
Does NOT interpret changes in average profit as profit caused by N75.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

EVENT = re.compile(r"\bOPEX (?P<date>\d{4}-\d+-\d+) (?P<event>N75_QUOTE|AIR_BUILD|FLEET_PROJECT|V252_ENGINE|RAIL_BUILD) (?P<body>.*)")
KV = re.compile(r"([a-zA-Z_]+)=([^\s]+)")


def read_events(path):
    events = []
    with path.open(encoding="utf-8", errors="replace") as fp:
        for line in fp:
            match = EVENT.search(line)
            if match:
                events.append({"date": match.group("date"),
                               "event": match.group("event"),
                               **dict(KV.findall(match.group("body")))})
    return events


def project(events):
    line_routes = {}
    for event in events:
        if event["event"] == "AIR_BUILD" and all(k in event for k in ("line", "src", "dst")):
            line_routes[event["line"]] = "|".join(sorted((event["src"], event["dst"]), key=int))
    fleet = Counter()
    fleet_dates = defaultdict(list)
    direct = []
    quote = Counter()
    prices = []
    v252 = []
    missing_routes = []
    for e in events:
        if e["event"] == "FLEET_PROJECT" and e.get("action") == "grow":
            route = line_routes.get(e.get("line"))
            if not route:
                missing_routes.append(e)
                continue
            n = int(e.get("added", "0"))
            fleet[route] += n
            fleet_dates[route].append((e["date"], n))
        elif e["event"] == "V252_ENGINE" and e.get("action") == "reinforce":
            v252.append(e)
        elif e["event"] == "N75_QUOTE":
            quote[e.get("phase", "unknown")] += 1
            if e.get("phase") == "built":
                direct.append(e)
                old = int(e.get("old_quote", 0))
                planned = int(e.get("plan_quote", 0))
                actual = int(e.get("engine_price", 0))
                prices.append((old, planned, actual))
    # Only completed construction events are counted as line construction.
    air_builds = sum(e["event"] == "AIR_BUILD" for e in events)
    rail_builds = sum(e["event"] == "RAIL_BUILD" for e in events)
    return {"events": events, "fleet": fleet, "fleet_dates": fleet_dates,
            "quote": quote, "direct": direct, "prices": prices,
            "air_builds": air_builds, "rail_builds": rail_builds,
            "v252": v252, "missing_routes": missing_routes,
            "line_routes": line_routes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("engine_dir", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    groups = defaultdict(dict)
    for path in sorted(args.engine_dir.glob("*.log")):
        match = re.fullmatch(r"(reference|n75_truequote)_seed(\d+)_r0\.log", path.name)
        if match:
            arm, seed = match.groups()
            groups[int(seed)][arm] = project(read_events(path))
    if not groups:
        raise SystemExit("no paired logs found")

    rows = []
    for seed, arms in sorted(groups.items()):
        if len(arms) != 2:
            raise SystemExit(f"seed={seed} incomplete arms")
        r, v = arms["reference"], arms["n75_truequote"]
        common_routes = set(r["fleet"]) | set(v["fleet"])
        physical_delta = {route: v["fleet"][route] - r["fleet"][route]
                          for route in sorted(common_routes) if v["fleet"][route] != r["fleet"][route]}
        mismatches = [e for e in v["direct"] if int(e.get("plan_quote", -1)) != int(e.get("engine_price", -2))]
        missing = len(r["missing_routes"]) + len(v["missing_routes"])
        row = {
            "seed": seed,
            "off_fleet_added": sum(r["fleet"].values()),
            "on_fleet_added": sum(v["fleet"].values()),
            "delta_fleet_added": sum(v["fleet"].values()) - sum(r["fleet"].values()),
            "fleet_routes_changed": len(physical_delta),
            "fleet_routes_more": sum(delta > 0 for delta in physical_delta.values()),
            "fleet_routes_less": sum(delta < 0 for delta in physical_delta.values()),
            "fleet_delta_by_route": physical_delta,
            "off_air_builds": r["air_builds"],
            "on_air_builds": v["air_builds"],
            "off_rail_builds": r["rail_builds"],
            "on_rail_builds": v["rail_builds"],
            "on_v252_reinforce": len(v["v252"]),
            "on_quote_phases": dict(v["quote"]),
            "on_quote_direct_built": len(v["direct"]),
            "on_quote_built_new_more_expensive": sum(new > old for old, new, _ in v["prices"]),
            "on_quote_built_new_cheaper": sum(new < old for old, new, _ in v["prices"]),
            "on_quote_engine_price_mismatch": len(mismatches),
            "unmapped_fleet_events": missing,
        }
        rows.append(row)
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    print("AGGREGATE", json.dumps({
        "seeds": len(rows),
        "on_quote_builds": sum(x["on_quote_direct_built"] for x in rows),
        "on_quote_plan_events": sum(x["on_quote_phases"].get("plan", 0) for x in rows),
        "on_quote_stale": sum(x["on_quote_phases"].get("stale", 0) for x in rows),
        "engine_quote_mismatches": sum(x["on_quote_engine_price_mismatch"] for x in rows),
        "net_fleet_purchases": sum(x["delta_fleet_added"] for x in rows),
        "positive_fleet_seeds": sum(x["delta_fleet_added"] > 0 for x in rows),
        "negative_fleet_seeds": sum(x["delta_fleet_added"] < 0 for x in rows),
        "unmapped_fleet_events": sum(x["unmapped_fleet_events"] for x in rows),
    }, ensure_ascii=False))
    if args.json:
        args.json.write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
