"""Read existing C66 annual telemetry; never starts games or changes inputs.

The exact accounting identity is P/N = (P/A) * (A/N). Route/model
characteristics are descriptive ratios, NOT independent causal multipliers.
Unobserved factors stay null. December profit is year-to-date, not a full year.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


YEARS = (1973, 1976, 1979)
ARMS = ("OpexAI", "AAAHogEx")


def read_json(path):
    path = Path(path)
    if path.suffix == ".gz":
        return json.loads(subprocess.check_output(["zcat", str(path)], text=True))
    return json.loads(path.read_text(encoding="utf-8"))


def ratio(a, b):
    return a / b if a is not None and b is not None and b != 0 else None


def mean(values):
    return sum(values) / len(values) if values else None


def engine_table(source):
    """Resolve engine IDs from MA comments, then join AVI rows by model name.

    No hard-coded cargo IDs or engine offsets; source values are nominal,
    not measured speeds, running bills or post-refit capacities.
    """
    ids = {}
    aircraft = {}
    for number, line in enumerate(source.splitlines(), 1):
        match = re.search(r"\bMA\(.*//\s*(\d+)\s+(.+?)\s*$", line)
        if match:
            ids[match[2]] = int(match[1])
        match = re.search(r"\bAVI\((.*?)\).*//\s*\d+\s+(.+?)\s*$", line)
        if match:
            fields = [v.strip() for v in match[1].split(",")]
            aircraft[match[2]] = {
                "nominal_kmh": int(fields[6]) * 128 // 10,
                "running_cost_factor": int(fields[2]),
                "nominal_pax": int(fields[8]),
                "nominal_mail": int(fields[7]),
                "source_line": number,
            }
    return {str(ids[name]): dict(data, name=name) for name, data in aircraft.items() if name in ids}


def describe(lines, map_width, sources):
    n = sum(line["vehicles"] for line in lines)
    profit_values = [line.get("profit_this_year_gbp") for line in lines]
    profit = sum(profit_values) if all(v is not None for v in profit_values) else None
    capacities = Counter()
    distances = []
    stations = {}
    markets = set()
    cargo_services = {}
    for line in lines:
        capacities.update(line["capacity_by_cargo"])
        markets.add(line["market_key"])
        service = ",".join(sorted(line["capacity_by_cargo"]))
        group = cargo_services.setdefault(service, {"planes": 0, "profit_ytd_gbp": 0})
        group["planes"] += line["vehicles"]
        if group["profit_ytd_gbp"] is not None:
            group["profit_ytd_gbp"] = (group["profit_ytd_gbp"] + line["profit_this_year_gbp"]
                                       if line.get("profit_this_year_gbp") is not None else None)
        tiles = line.get("ordered_station_tiles", [])
        if len(tiles) != 2:
            raise ValueError("Expected two endpoints on every air route")
        a, b = tiles
        dx, dy = abs(a % map_width - b % map_width), abs(a // map_width - b // map_width)
        distances.append((line["vehicles"], math.hypot(dx, dy), dx + dy))
        for endpoint in line["endpoint_cargo_stats"]:
            stations[endpoint["station_id"]] = endpoint
    ratings = defaultdict(list)
    pickup = defaultdict(list)
    waiting = defaultdict(list)
    for endpoint in stations.values():
        for cargo, stats in endpoint["cargo"].items():
            if stats.get("rated") and stats.get("rating") is not None:
                ratings[cargo].append(stats["rating"])
            if stats.get("time_since_pickup") is not None:
                pickup[cargo].append(stats["time_since_pickup"])
            if stats.get("max_waiting_cargo") is not None:
                waiting[cargo].append(stats["max_waiting_cargo"])
    return {
        "planes": n, "airports": len(stations), "pairs": len(markets), "lines": len(lines),
        "profit_ytd_gbp": profit, "profit_per_plane": ratio(profit, n),
        "profit_per_airport": ratio(profit, len(stations)),
        "planes_per_airport": ratio(n, len(stations)),
        "planes_per_pair": ratio(n, len(markets)),
        "routes_per_airport": ratio(2 * len(lines), len(stations)),
        "distance_euclidean_plane_weighted": ratio(sum(w * d for w, d, _ in distances), n),
        "distance_manhattan_plane_weighted": ratio(sum(w * d for w, _, d in distances), n),
        "capacity_by_cargo_per_plane": {c: ratio(v, n) for c, v in capacities.items()},
        "rating_by_cargo": {c: mean(v) for c, v in ratings.items()},
        "rating_count_by_cargo": {c: len(v) for c, v in ratings.items()},
        "pickup_periods_by_cargo": {c: mean(v) for c, v in pickup.items()},
        "max_waiting_rating_stat_by_cargo": {c: mean(v) for c, v in waiting.items()},
        "cargo_services": cargo_services,
        "sources": sources,
    }


def log_evidence(log_dir, seeds, years):
    records = []
    for seed in seeds:
        path = Path(log_dir) / f"reference_seed{seed}_r0.log"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # C121_FLEET_MARGINAL is intentionally not an OpexDecide event.
            marginal = re.search(r"C121_FLEET_MARGINAL (.*)", line)
            event = re.search(r"OPEX (\d+)-\d+-\d+ (LINE_REVENUE|C121_HUB_DELAY|AIR_FLEET) (.*)", line)
            if marginal:
                fields = dict(re.findall(r"(\w+)=([^\s]+)", marginal[1]))
                year = int(fields["year"])
                kind = "C121_FLEET_MARGINAL"
            elif event:
                year, kind = int(event[1]), event[2]
                fields = dict(re.findall(r"(\w+)=([^\s]+)", event[3]))
            else:
                continue
            if year in years:
                records.append({"seed": seed, "year": year, "kind": kind,
                                "fields": fields, "source": f"{path}:{number}"})
    return records


def decompose(data, rows, models, log_records):
    if data.get("openttd_version") != "15.3":
        raise ValueError("This analysis requires the OpenTTD 15.3 schema")
    seeds = data["seeds"]
    if data.get("repeats") != 1 or len(seeds) != len(set(seeds)):
        raise ValueError("Expected distinct seeds and one repeat")
    games = [g for g in data["games"] if g["policy_id"] == "reference"]
    if len(games) != len(seeds) or {g["seed"] for g in games} != set(seeds) or not all(g["game_ok"] for g in games):
        raise ValueError("Reference games must all be present and healthy")
    output = {"schema": 1, "campaign": data["campaign_id"], "bundle_sha256": data["source_bundle_sha256"],
              "scope": "reference only; December 1 YTD vehicle operating profit; pooled ratios across seeds",
              "identifiable_identity": "profit_per_plane = profit_per_airport / planes_per_airport",
              "causal_factorization_identified": False, "years": {},
              "unavailable": {
                  "departure_load_A_to_B": "No departure cargo/capacity series for both companies",
                  "departure_load_B_to_A": "No departure cargo/capacity series for both companies",
                  "town_population": "No town population in annual line telemetry; town IDs are not populations",
                  "dock_days": "C121_HUB_DELAY is an Opex-only inferred residual, not measured dock time",
                  "running_cost_actual": "line_telemetry.unavailable_fields includes running_cost",
                  "depreciation_charge_in_vehicle_profit": "Not charged in profit_this_year_gbp; book value is a stock",
                  "maintenance_airports": "No separate bill per airport in this telemetry",
                  "instant_waiting": "max_waiting_cargo is a rating statistic, not GetCargoWaiting",
                  "rating_qualification": "Historical collector may use Acceptance instead of Rating; inspect frozen harness",
              }}
    for year in YEARS:
        arms = {}
        for arm in ARMS:
            selected = [(i, s) for i, s in enumerate(data["line_telemetry"]["snapshots"])
                        if s["duel_policy_id"] == "reference" and s["year"] == year and s["arm"] == arm]
            if len(selected) != len(seeds) or {s["seed"] for _, s in selected} != set(seeds):
                raise ValueError(f"Incomplete/duplicate annual snapshots: {year} {arm}")
            by_seed = []
            for i, snapshot in selected:
                if not snapshot["ok"] or snapshot["unresolved_vehicles"] or snapshot["date"] != f"{year}-12-01":
                    raise ValueError("Invalid December telemetry")
                air = [line for line in snapshot["lines"] if line["mode"] == "air"]
                metric = describe(air, 1 << data["map_size"], [f"$.line_telemetry.snapshots[{i}].lines[mode=air]"])
                metric["seed"] = snapshot["seed"]
                by_seed.append(metric)
            # Airport and market IDs are local to each game; never merge them across seeds.
            n = sum(m["planes"] for m in by_seed)
            a = sum(m["airports"] for m in by_seed)
            p = sum(m["pairs"] for m in by_seed)
            profit = sum(m["profit_ytd_gbp"] for m in by_seed) if all(m["profit_ytd_gbp"] is not None for m in by_seed) else None
            result = {"planes": n, "airports": a, "pairs": p,
                      "profit_ytd_gbp": profit, "profit_per_plane": ratio(profit, n),
                      "profit_per_airport": ratio(profit, a), "planes_per_airport": ratio(n, a),
                      "planes_per_pair": ratio(n, p),
                      "pairs_per_airport": ratio(p, a),
                      "by_seed": by_seed}
            for field in ("distance_euclidean_plane_weighted", "distance_manhattan_plane_weighted"):
                result[field] = ratio(sum(m[field] * m["planes"] for m in by_seed), n)
            rating_cargos = {c for m in by_seed for c in m["rating_by_cargo"]}
            result["rating_by_cargo"] = {c: ratio(
                sum(m["rating_by_cargo"].get(c, 0) * m["rating_count_by_cargo"].get(c, 0) for m in by_seed),
                sum(m["rating_count_by_cargo"].get(c, 0) for m in by_seed)) for c in rating_cargos}
            services = {c for m in by_seed for c in m["cargo_services"]}
            result["cargo_services"] = {}
            for service in sorted(services):
                groups = [m["cargo_services"][service] for m in by_seed if service in m["cargo_services"]]
                count = sum(g["planes"] for g in groups)
                service_profit = sum(g["profit_ytd_gbp"] for g in groups) if all(g["profit_ytd_gbp"] is not None for g in groups) else None
                result["cargo_services"][service] = {"planes": count, "profit_ytd_gbp": service_profit,
                                                      "profit_per_plane": ratio(service_profit, count)}
            capacities = Counter()
            engines = Counter()
            row_sources = []
            for line_number, row in rows:
                if (row.get("duel_policy_id") == "reference" and row["run"][0] == arm
                        and row["date"] == f"{year}-12-01"):
                    engines.update(row["air_engine_counts"])
                    capacities.update(row["air_capacities_by_cargo"])
                    row_sources.append(f"JSONL:{line_number}:air_engine_counts,air_capacities_by_cargo")
            if len(row_sources) != len(seeds) or sum(engines.values()) != n:
                raise ValueError("Fleet census and decoded air lines disagree")
            result["engines"] = dict(engines)
            result["capacity_by_cargo_per_plane"] = {c: ratio(v, n) for c, v in capacities.items()}
            result["engine_sources"] = row_sources
            if models:
                if not all(engine in models for engine in engines):
                    raise ValueError("Unknown engine in supplied source table")
                for field in ("nominal_kmh", "running_cost_factor", "nominal_pax"):
                    result[field] = sum(models[e][field] * count for e, count in engines.items()) / n
            arms[arm] = result
        ours, theirs = (arms[a] for a in ARMS)
        identity = {
            "profit_per_plane_ratio": ratio(ours["profit_per_plane"], theirs["profit_per_plane"]),
            "airport_yield_factor": ratio(ours["profit_per_airport"], theirs["profit_per_airport"]),
            "inverse_density_factor": ratio(theirs["planes_per_airport"], ours["planes_per_airport"]),
            "inverse_pairs_per_airport_factor": ratio(theirs["pairs_per_airport"], ours["pairs_per_airport"]),
            "inverse_planes_per_pair_factor": ratio(theirs["planes_per_pair"], ours["planes_per_pair"]),
        }
        identity["product"] = identity["airport_yield_factor"] * identity["inverse_density_factor"]
        identity["three_factor_product"] = (identity["airport_yield_factor"]
            * identity["inverse_pairs_per_airport_factor"] * identity["inverse_planes_per_pair_factor"])
        output["years"][str(year)] = {"arms": arms, "accounting_factors": identity,
            "descriptive_ratios_not_causal_factors": {
                field: ratio(ours.get(field), theirs.get(field)) for field in
                ("distance_euclidean_plane_weighted", "distance_manhattan_plane_weighted", "nominal_kmh", "nominal_pax", "running_cost_factor", "planes_per_pair")},
            "log_evidence": [r for r in log_records if r["year"] == year]}
        last_delay = {}
        for event in output["years"][str(year)]["log_evidence"]:
            if event["kind"] == "C121_HUB_DELAY":
                last_delay[(event["seed"], event["fields"]["station"])] = event
        output["years"][str(year)]["opex_hub_residual_last_per_station"] = {
            "mean_days": mean([float(e["fields"]["days"]) for e in last_delay.values()]),
            "stations": len(last_delay),
            "qualification": "Opex-only inferred residual, not dock time; correlated with density",
            "sources": [e["source"] for e in last_delay.values()],
        }
    output["engine_table"] = models
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--openttd-src", type=Path, help="OpenTTD 15.3 src directory, for nominal engine descriptors")
    args = parser.parse_args()
    path = args.campaign
    data = read_json(path)
    stem = path.name.removesuffix(".gz").removesuffix(".json")
    jsonl = path.parent / (stem + ".jsonl" + (".gz" if path.suffix == ".gz" else ""))
    row_text = (subprocess.check_output(["zcat", str(jsonl)], text=True) if jsonl.suffix == ".gz"
                else jsonl.read_text(encoding="utf-8"))
    rows = [(i, json.loads(line)) for i, line in enumerate(row_text.splitlines(), 1) if line.strip()]
    table_path = args.openttd_src / "table/engines.h" if args.openttd_src else None
    models = engine_table(table_path.read_text(encoding="utf-8")) if table_path else {}
    log_dir = path.parent / (stem + "_engine")
    records = log_evidence(log_dir, data["seeds"], YEARS)
    result = decompose(data, rows, models, records)
    result["inputs"] = [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in (path, jsonl)]
    if table_path:
        result["inputs"].append({"path": str(table_path), "sha256": hashlib.sha256(table_path.read_bytes()).hexdigest()})
    for seed in data["seeds"]:
        log_path = log_dir / f"reference_seed{seed}_r0.log"
        result["inputs"].append({"path": str(log_path), "sha256": hashlib.sha256(log_path.read_bytes()).hexdigest()})
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
