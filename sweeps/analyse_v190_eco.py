#!/usr/bin/env python3
"""Autopsie REPRODUCTIBLE, lecture seule, du bundle V190-ECO 4x6.

Les coûts RAIL_BUILD sont les débits de chantier rapportés par OpexAI,
pas une ventilation comptable voie/gare/signal/depot/vehicule. Les profits
de ligne sont des profits de flotte (revenu brut indisponible). L'identification
des services s'appuie sur les vehicules de STATION_FIRST_VEHICLE; les cas
ambigus restent explicitement non attribues.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import re
from pathlib import Path

BASE = "v190_fix_independent_4x6_20261103"
RAIL = re.compile(r"\bOPEX (\d+)-(\d+)-(\d+) RAIL_BUILD line=(\d+) (.*)")
DOUBLE = re.compile(r"\bOPEX (\d+)-(\d+)-(\d+) V190 action=build_double line=(\d+) trains=(\d+)")
FIRST = re.compile(r"\bOPEX (\d+)-(\d+)-(\d+) STATION_FIRST_VEHICLE station=(\d+) vehicle=(\d+) mode=rail .*\bline=(\d+)")


def fields(s: str) -> dict:
    return dict(kv.split("=", 1) for kv in s.split() if "=" in kv)


def date(y: str, m: str, d: str) -> str:
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def parse_logs(folder: Path, policy: str, seed: int) -> tuple[dict, dict]:
    builds, first = {}, collections.defaultdict(list)
    doubles = set()
    path = folder / f"{policy}_seed{seed}_r0.log"
    for raw in path.open(encoding="utf-8", errors="replace"):
        if (m := RAIL.search(raw)) is not None:
            y, mo, day, lid, tail = m.groups()
            builds[int(lid)] = {"seed": seed, "policy": policy, "line_id": int(lid),
                                "date": date(y, mo, day), "year": int(y),
                                **fields(tail)}
        elif (m := DOUBLE.search(raw)) is not None:
            y, mo, day, lid, trains = m.groups()
            if int(trains) >= 2:
                doubles.add(int(lid))
        elif (m := FIRST.search(raw)) is not None:
            y, mo, day, station, vehicle, lid = m.groups()
            first[int(lid)].append({"station": int(station), "vehicle": int(vehicle),
                                    "date": date(y, mo, day)})
    for lid, b in builds.items():
        b["double"] = lid in doubles
        b["first_vehicles"] = first.get(lid, [])
        for k in ("dist", "cost", "wagons", "trains", "pred_profit", "reuse"):
            try:
                b[k] = int(b[k])
            except (KeyError, ValueError, TypeError):
                b[k] = None
    return builds, {"unmatched_double_ids": sorted(doubles.difference(builds))}


def index_snapshots(data: dict) -> dict:
    snaps = collections.defaultdict(list)
    for x in data["line_telemetry"]["snapshots"]:
        if x.get("arm") == "OpexAI" and x.get("ok"):
            snaps[(x["duel_policy_id"], x["seed"])].append(x)
    for v in snaps.values():
        v.sort(key=lambda x: x["date"])
    return snaps


def associate_service(build: dict, snapshots: list) -> dict:
    """Appariement conservateur à la première photo après mise en service."""
    candidates = []
    for s in snapshots:
        if s["date"][:7] <= build["date"][:7]:
            continue
        if s["date"] > (datetime.date.fromisoformat(build["date"]) +
                         datetime.timedelta(days=100)).isoformat():
            break
        for line in s["lines"]:
            if line["mode"] != "rail":
                continue
            # Le vehicule d'une station recemment ouverte et le quai
            # ensemble sont bien plus probants qu'un ID de station seul.
            ids = set(line["vehicle_ids"])
            stations = set(line["station_ids"])
            veh_hits = sum(v["vehicle"] in ids for v in build["first_vehicles"])
            station_hits = sum(v["station"] in stations for v in build["first_vehicles"])
            if veh_hits or station_hits:
                key = line["line_key_local"]
                score = veh_hits * 10 + station_hits * 2
                if build["trains"] == line["vehicles"]:
                    score += 1
                candidates.append((score, key, s["date"]))
        if candidates:
            break
    if not candidates:
        return {"service_key": None, "match": "unmatched", "match_date": None}
    candidates.sort(reverse=True)
    best = candidates[0]
    winners = {key for score, key, _ in candidates if score == best[0]}
    if len(winners) != 1:
        return {"service_key": None, "match": "ambiguous", "match_date": best[2]}
    return {"service_key": best[1], "match": "vehicle_and_station" if best[0] >= 10
            else "station_only", "match_date": best[2]}


def financial_by_year(snapshots: list, service_key: str, build_year: int) -> list:
    result = []
    for year in range(max(1970, build_year), 1976):
        # Les sauvegardes du 1er janvier precedent le basculement comptable
        # et portent encore l'ancien profit_this_year. Le 1er fevrier suivant
        # comporte le profit_last_year clos (verifie 1971-12 / 1972-02).
        closed = next((x for x in snapshots if x["date"] == f"{year + 1}-02-01"), None)
        december = next((x for x in snapshots if x["date"] == f"{year}-12-01"), None)
        s, key, complete = (closed, "profit_last_year_gbp", True) if closed else (
            december, "profit_this_year_gbp", False)
        if s is None:
            continue
        hits = [line for line in s["lines"] if line["line_key_local"] == service_key]
        if len(hits) != 1:
            continue
        line = hits[0]
        result.append({"year": year, "profit_gbp": round(line[key], 2),
                       "closed_year": complete, "vehicles": line["vehicles"],
                       "vehicle_financials": line["vehicle_financials"],
                       "capacity_by_cargo": line["capacity_by_cargo"],
                       "station_ids": line["station_ids"],
                       "service_key": line.get("service_key")})
    return result


def yearly_company(jsonl: Path) -> dict:
    grouped = collections.defaultdict(dict)
    for raw in jsonl.open(encoding="utf-8"):
        d = json.loads(raw)
        if d.get("run", [None])[0] != "OpexAI":
            continue
        policy = d.get("duel_policy_id")
        seed = d["run"][1]
        yr = int(d["date"][:4])
        grouped[(policy, seed, yr)][d["date"]] = {
            "money": d.get("money"), "loan": d.get("current_loan"),
            "n_vehicles": d.get("n_vehicles"),
            "n_stations": d.get("n_stations"), "profit_year": d.get("profit_year")}
    result = {}
    for (policy, seed, yr), dates in grouped.items():
        month_data = sorted(dates.items())
        end = dates.get(f"{yr}-12-01", month_data[-1][1])
        vals = [v["money"] for _, v in month_data if v["money"] is not None]
        loans = [v["loan"] for _, v in month_data if v["loan"] is not None]
        result[(policy, seed, yr)] = {
            "year": yr, "seed": seed, "policy": policy,
            "cash_end": end["money"], "loan_end": end["loan"],
            "cash_min": min(vals) if vals else None,
            "cash_max": max(vals) if vals else None,
            "loan_max": max(loans) if loans else None,
            "vehicles_end": end["n_vehicles"], "stations_end": end["n_stations"],
            "company_profit_year_end": end["profit_year"],
            "months_cash_below_50000": sum(v < 50000 for v in vals),
            "months_cash_below_100000": sum(v < 100000 for v in vals),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("results"))
    parser.add_argument("--campaign", default=BASE)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    source = json.loads((args.root / f"{args.campaign}.json").read_text(encoding="utf-8"))
    snaps = index_snapshots(source)
    financials = yearly_company(args.root / f"{args.campaign}.jsonl")
    log_dir = args.root / f"{args.campaign}_engine"
    policies = ("reference", "v190_fix_independent")
    all_lines, summaries, yearly_rows = [], {}, []
    for policy in policies:
        for seed in source["seeds"]:
            builds, diag = parse_logs(log_dir, policy, seed)
            series = snaps[(policy, seed)]
            for b in builds.values():
                b.update(associate_service(b, series))
                if b["service_key"] is not None:
                    b["profit_yearly"] = financial_by_year(series, b["service_key"], b["year"])
                    first_snapshot = next((x for x in series if x["date"] == b["match_date"]), None)
                    first_lines = [l for l in first_snapshot["lines"] if l["line_key_local"] == b["service_key"]] if first_snapshot else []
                    b["first_exposure"] = ({
                        "date": b["match_date"],
                        "vehicle_ids": first_lines[0]["vehicle_ids"],
                        "station_ids": first_lines[0]["station_ids"],
                        "vehicles": first_lines[0]["vehicles"],
                        "capacity_by_cargo": first_lines[0]["capacity_by_cargo"],
                    } if len(first_lines) == 1 else None)
                else:
                    b["profit_yearly"] = []
                    b["first_exposure"] = None
                all_lines.append(b)
            for year in range(1970, 1976):
                vals = [b for b in builds.values() if b["year"] == year]
                dec = next((s for s in series if s["date"] == f"{year}-12-01"), None)
                row = dict(financials.get((policy, seed, year), {}))
                row.update({"seed": seed, "year": year, "policy": policy,
                            "built_lines": len(vals),
                            "new_double_lines": sum(b["double"] for b in vals),
                            "build_cost_total_gbp": sum(b["cost"] or 0 for b in vals),
                            "double_build_cost_gbp": sum((b["cost"] or 0) for b in vals if b["double"]),
                            "rail_lines_observed_dec": len(dec["lines"]) if dec else None,
                            "rail_vehicles_observed_dec":
                            sum(line["vehicles"] for line in dec["lines"]) if dec else None})
                yearly_rows.append(row)
            summaries[f"{policy}:{seed}"] = {
                "build_count": len(builds),
                "double_count": sum(b["double"] for b in builds.values()),
                "build_cost_gbp": sum(b["cost"] or 0 for b in builds.values()),
                "double_cost_gbp": sum(b["cost"] or 0 for b in builds.values() if b["double"]),
                "double_match_status": collections.Counter(
                    b["match"] for b in builds.values() if b["double"]),
                **diag}
    result = {
        "campaign": args.campaign,
        "source_bundle_sha256": source["source_bundle_sha256"],
        "methodological_limits": [
            "RAIL_BUILD cost est le total chantier, pas le surcout marginal specifique au doublement",
            "Depenses voie/gare/signal/depot/wagons non detaillees dans RAIL_BUILD",
            "Revenu brut par ligne indisponible: seuls profits nets des vehicules sont observes",
            "Profits 1975 au 01/12 = YTD provisoire et non une annee close",
            "V190 construit des lignes doubles des l'ouverture: aucun avant/apres au sein d'une meme ligne",
            "Appariements station_only moins probants que vehicle_and_station",
        ],
        "yearly": yearly_rows, "summary": summaries, "builds": all_lines}
    out = args.out or args.root / f"{args.campaign}_eco.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=dict) + "\n", encoding="utf-8")
    print(f"saved: {out}; builds={len(all_lines)}, doubles={sum(b['double'] for b in all_lines)}")
    for name, s in summaries.items():
        print(name, "builds", s["build_count"], "double", s["double_count"],
              "cost", s["build_cost_gbp"], "double_cost", s["double_cost_gbp"],
              "matches", s["double_match_status"])


if __name__ == "__main__":
    main()
