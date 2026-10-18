"""Diagnostic V242 : flotte routière, proxy de rabattement, attente en gare.

Lit des extraits déjà produits par les harnais (JSONL de duel, ou
``line_telemetry`` d'un JSON de campagne). Ne lance aucune partie.

Le proxy de rabattement n'est pas le drapeau d'ordre ``OF_TRANSFER`` : la
télémétrie de ligne ne conserve que les StationID. Une ligne routière est
comptée comme rabattement si l'un de ses StationID est aussi celui d'une
ligne aérienne ou ferroviaire de la même compagnie, dans le même instantané.
C'est le signe d'un arrêt joint, pas une preuve d'ordre de transfert.

``max_waiting_cargo`` est le pic depuis le dernier recalcul de note, pas le
stock instantané ni le taux de remplissage des sièges.
"""

from __future__ import annotations

import argparse
import gzip
import json
import statistics
from pathlib import Path


PASSENGER_CARGO = "0"
MODES = ("rail", "road", "air", "water")


def _open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def iter_jsonl(path):
    with _open_text(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _seed_of(row):
    run = row.get("run") or []
    if len(run) > 1:
        return run[1]
    return row.get("seed")


def _repeat_of(row):
    run = row.get("run") or []
    if len(run) > 2:
        return run[2]
    return row.get("repeat", 0)


def _arm_of(row):
    run = row.get("run") or []
    if run:
        return run[0]
    return row.get("arm")


def _duel_policy(row):
    """Politique du duel, pas l'étiquette de compagnie.

    Le harnais écrit ``policy_id="AAAHogEx"`` sur chaque ligne adverse et
    ``duel_policy_id`` pour distinguer les deux parties appariées. Sans ce
    second champ, les deux AAA d'une même graine se confondent.
    """
    duel = row.get("duel_policy_id")
    if duel is not None:
        return duel
    return row.get("policy_id")


def latest_company_rows(rows):
    """Dernier instantané valide par duel, compagnie, graine et répétition."""
    chosen = {}
    for row in rows:
        if row.get("vehs_chunk_valid") is False:
            continue
        date = str(row.get("date") or "")
        key = (
            _duel_policy(row),
            row.get("company_slot"),
            _arm_of(row),
            _seed_of(row),
            _repeat_of(row),
        )
        previous = chosen.get(key)
        if previous is None or date >= previous[0]:
            chosen[key] = (date, row)
    return [item[1] for item in chosen.values()]


def _numbers(values):
    clean = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    if not clean:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(clean),
        "mean": statistics.fmean(clean),
        "median": statistics.median(clean),
        "min": min(clean),
        "max": max(clean),
    }


def _mode_count(row, mode):
    by_mode = row.get("primary_vehicles_by_mode") or {}
    value = by_mode.get(mode)
    if value is None:
        return None
    return value


def _facility_count(row, name):
    facilities = row.get("stations_by_facility") or {}
    value = facilities.get(name)
    if value is None:
        return None
    return value


def summarize_company_rows(rows):
    """Agrège les derniers instantanés par politique et par compagnie."""
    groups = {}
    for row in latest_company_rows(rows):
        key = (_duel_policy(row), row.get("company_slot"), _arm_of(row))
        groups.setdefault(key, []).append(row)
    reports = []
    for (policy_id, slot, arm), group in sorted(groups.items(), key=lambda item: (str(item[0][0]), str(item[0][2]))):
        dates = [str(row.get("date") or "") for row in group]
        reports.append({
            "policy_id": policy_id,
            "company_policy_id": group[0].get("policy_id"),
            "company_slot": slot,
            "arm": arm,
            "games": len(group),
            "dates": _numbers([]),
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
            "profit_year": _numbers([row.get("profit_year") for row in group]),
            "company_value": _numbers([row.get("company_value") for row in group]),
            "median_station_rating": _numbers([row.get("median_station_rating") for row in group]),
            "vehicles": {mode: _numbers([_mode_count(row, mode) for row in group]) for mode in MODES},
            "primary_vehicles": _numbers([row.get("primary_vehicles") for row in group]),
            "stations": {
                name: _numbers([_facility_count(row, name) for row in group])
                for name in ("rail", "truck", "bus", "airport", "dock")
            },
            "air_passenger_capacity": _numbers([row.get("air_passenger_capacity") for row in group]),
            "road_share_of_fleet": _numbers([
                (row.get("primary_vehicles_by_mode") or {}).get("road") / row.get("primary_vehicles")
                if row.get("primary_vehicles")
                else None
                for row in group
            ]),
        })
    return reports


def _station_ids(line):
    raw = line.get("station_ids") or line.get("ordered_station_ids") or []
    result = []
    for value in raw:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result


def classify_road_lines(lines):
    """Sépare les lignes routières qui partagent un StationID avec l'air ou le rail."""
    air_stations = set()
    rail_stations = set()
    for line in lines:
        mode = line.get("mode")
        if mode == "air":
            air_stations.update(_station_ids(line))
        elif mode == "rail":
            rail_stations.update(_station_ids(line))
    feeder = []
    other = []
    for line in lines:
        if line.get("mode") != "road":
            continue
        stations = set(_station_ids(line))
        touches_air = bool(stations & air_stations)
        touches_rail = bool(stations & rail_stations)
        annotated = dict(line)
        annotated["touches_air"] = touches_air
        annotated["touches_rail"] = touches_rail
        if touches_air or touches_rail:
            feeder.append(annotated)
        else:
            other.append(annotated)
    return {
        "feeder": feeder,
        "other_road": other,
        "air_station_ids": air_stations,
        "rail_station_ids": rail_stations,
    }


def _vehicle_count(line):
    value = line.get("vehicles")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return 0


def _profit(line, field):
    value = line.get(field)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return 0.0


def _line_profit_sum(lines, field):
    return sum(_profit(line, field) for line in lines)


def _vehicle_sum(lines):
    return sum(_vehicle_count(line) for line in lines)


def mode_passenger_endpoints(lines, mode, passenger_cargo=PASSENGER_CARGO, require_airport=False):
    """Un point par gare d'un mode : pic d'attente, note, sièges d'un véhicule.

    Le champ ``one_plane_seats`` porte la capacité passagers de la ligne
    divisée par le nombre de véhicules, quel que soit le mode. Plusieurs
    lignes sur la même gare : on garde la plus petite capacité par véhicule.
    """
    by_station = {}
    for line in lines:
        if line.get("mode") != mode:
            continue
        vehicles = _vehicle_count(line)
        capacity = (line.get("capacity_by_cargo") or {}).get(passenger_cargo)
        per_vehicle = None
        if isinstance(capacity, (int, float)) and not isinstance(capacity, bool) and vehicles > 0:
            per_vehicle = capacity / vehicles
        for endpoint in line.get("endpoint_cargo_stats") or []:
            if require_airport and not endpoint.get("airport"):
                continue
            station_id = endpoint.get("station_id")
            cargo = (endpoint.get("cargo") or {}).get(str(passenger_cargo)) or {}
            waiting = cargo.get("max_waiting_cargo")
            rating = cargo.get("rating")
            current = by_station.get(station_id)
            if current is None:
                current = {
                    "station_id": station_id,
                    "town_id": endpoint.get("town_id"),
                    "max_waiting_cargo": waiting if isinstance(waiting, (int, float)) and not isinstance(waiting, bool) else None,
                    "rating": rating if isinstance(rating, (int, float)) and not isinstance(rating, bool) else None,
                    "one_plane_seats": per_vehicle,
                    "rated": bool(cargo.get("rated")),
                }
                by_station[station_id] = current
                continue
            if isinstance(waiting, (int, float)) and not isinstance(waiting, bool):
                previous = current["max_waiting_cargo"]
                current["max_waiting_cargo"] = waiting if previous is None else max(previous, waiting)
            if isinstance(rating, (int, float)) and not isinstance(rating, bool):
                previous = current["rating"]
                current["rating"] = rating if previous is None else min(previous, rating)
            if per_vehicle is not None:
                previous = current["one_plane_seats"]
                current["one_plane_seats"] = per_vehicle if previous is None else min(previous, per_vehicle)
            current["rated"] = current["rated"] or bool(cargo.get("rated"))
    return list(by_station.values())


def airport_endpoints(lines, passenger_cargo=PASSENGER_CARGO):
    """Un point par aéroport. Voir ``mode_passenger_endpoints``."""
    return mode_passenger_endpoints(lines, "air", passenger_cargo, require_airport=True)


def catchment_summary(endpoints):
    """Part des aéroports dont le pic d'attente est sous la capacité d'un avion."""
    comparable = []
    below = 0
    for endpoint in endpoints:
        waiting = endpoint.get("max_waiting_cargo")
        seats = endpoint.get("one_plane_seats")
        if waiting is None or seats is None or seats <= 0:
            continue
        comparable.append(endpoint)
        if waiting < seats:
            below += 1
    return {
        "airports": len(endpoints),
        "comparable": len(comparable),
        "peak_waiting_below_one_plane": below,
        "share_below_one_plane": (below / len(comparable)) if comparable else None,
        "max_waiting_cargo": _numbers([item.get("max_waiting_cargo") for item in endpoints]),
        "rating": _numbers([item.get("rating") for item in endpoints]),
        "one_plane_seats": _numbers([item.get("one_plane_seats") for item in endpoints]),
        "waiting_per_seat": _numbers([
            item["max_waiting_cargo"] / item["one_plane_seats"]
            for item in comparable
        ]),
    }


def _road_station_ids(lines):
    stations = set()
    for line in lines:
        if line.get("mode") == "road":
            stations.update(_station_ids(line))
    return stations


def catchment_by_road_join(lines, passenger_cargo=PASSENGER_CARGO):
    """Compare le pic d'attente des aéroports joints à une ligne routière et des autres.

    Le joint est un StationID partagé, pas un ordre ``OF_TRANSFER``. Ce n'est
    pas un taux de remplissage des sièges.
    """
    endpoints = airport_endpoints(lines, passenger_cargo)
    road_stations = _road_station_ids(lines)
    fed = [item for item in endpoints if item.get("station_id") in road_stations]
    unfed = [item for item in endpoints if item.get("station_id") not in road_stations]
    return {"fed": catchment_summary(fed), "unfed": catchment_summary(unfed)}


def summarize_snapshot(snapshot, passenger_cargo=PASSENGER_CARGO):
    lines = snapshot.get("lines") or []
    if snapshot.get("ok") is False:
        return None
    split = classify_road_lines(lines)
    air_lines = [line for line in lines if line.get("mode") == "air"]
    rail_lines = [line for line in lines if line.get("mode") == "rail"]
    feeder = split["feeder"]
    other = split["other_road"]
    road_vehicles = _vehicle_sum(feeder) + _vehicle_sum(other)
    feeder_vehicles = _vehicle_sum(feeder)
    return {
        "road_vehicles": road_vehicles,
        "feeder_vehicles": feeder_vehicles,
        "feeder_share": (feeder_vehicles / road_vehicles) if road_vehicles else None,
        "feeder_touch_air_vehicles": _vehicle_sum([line for line in feeder if line["touches_air"]]),
        "feeder_touch_rail_vehicles": _vehicle_sum([line for line in feeder if line["touches_rail"]]),
        "other_road_vehicles": _vehicle_sum(other),
        "air_vehicles": _vehicle_sum(air_lines),
        "rail_vehicles": _vehicle_sum(rail_lines),
        "road_profit_last_year": _line_profit_sum(feeder, "profit_last_year_gbp") + _line_profit_sum(other, "profit_last_year_gbp"),
        "feeder_profit_last_year": _line_profit_sum(feeder, "profit_last_year_gbp"),
        "other_road_profit_last_year": _line_profit_sum(other, "profit_last_year_gbp"),
        "air_profit_last_year": _line_profit_sum(air_lines, "profit_last_year_gbp"),
        "rail_profit_last_year": _line_profit_sum(rail_lines, "profit_last_year_gbp"),
        "road_profit_this_year": _line_profit_sum(feeder, "profit_this_year_gbp") + _line_profit_sum(other, "profit_this_year_gbp"),
        "feeder_profit_this_year": _line_profit_sum(feeder, "profit_this_year_gbp"),
        "air_profit_this_year": _line_profit_sum(air_lines, "profit_this_year_gbp"),
        "catchment": catchment_summary(airport_endpoints(lines, passenger_cargo)),
        "catchment_by_road_join": catchment_by_road_join(lines, passenger_cargo),
        "unresolved_vehicles": len(snapshot.get("unresolved_vehicles") or []),
    }


def latest_snapshots(snapshots):
    chosen = {}
    for snapshot in snapshots:
        if snapshot.get("ok") is False:
            continue
        date = str(snapshot.get("date") or "")
        key = (
            snapshot.get("duel_policy_id"),
            snapshot.get("arm"),
            snapshot.get("seed"),
            snapshot.get("repeat", 0),
        )
        previous = chosen.get(key)
        if previous is None or date >= previous[0]:
            chosen[key] = (date, snapshot)
    return [item[1] for item in chosen.values()]


def _mean_field(items, field):
    return _numbers([item.get(field) for item in items])


def summarize_line_telemetry(payload, passenger_cargo=PASSENGER_CARGO):
    telemetry = payload.get("line_telemetry") if isinstance(payload, dict) and "line_telemetry" in payload else payload
    if not isinstance(telemetry, dict):
        raise ValueError("line_telemetry absent")
    snapshots = latest_snapshots(telemetry.get("snapshots") or [])
    groups = {}
    for snapshot in snapshots:
        summary = summarize_snapshot(snapshot, passenger_cargo)
        if summary is None:
            continue
        key = (snapshot.get("duel_policy_id"), snapshot.get("arm"))
        groups.setdefault(key, []).append((snapshot, summary))
    reports = []
    for (policy_id, arm), pairs in sorted(groups.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
        summaries = [pair[1] for pair in pairs]
        dates = [str(pair[0].get("date") or "") for pair in pairs]
        reports.append({
            "policy_id": policy_id,
            "arm": arm,
            "games": len(summaries),
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
            "road_vehicles": _mean_field(summaries, "road_vehicles"),
            "feeder_vehicles": _mean_field(summaries, "feeder_vehicles"),
            "feeder_share": _mean_field(summaries, "feeder_share"),
            "feeder_touch_air_vehicles": _mean_field(summaries, "feeder_touch_air_vehicles"),
            "feeder_touch_rail_vehicles": _mean_field(summaries, "feeder_touch_rail_vehicles"),
            "other_road_vehicles": _mean_field(summaries, "other_road_vehicles"),
            "air_vehicles": _mean_field(summaries, "air_vehicles"),
            "rail_vehicles": _mean_field(summaries, "rail_vehicles"),
            "road_profit_last_year": _mean_field(summaries, "road_profit_last_year"),
            "feeder_profit_last_year": _mean_field(summaries, "feeder_profit_last_year"),
            "other_road_profit_last_year": _mean_field(summaries, "other_road_profit_last_year"),
            "air_profit_last_year": _mean_field(summaries, "air_profit_last_year"),
            "rail_profit_last_year": _mean_field(summaries, "rail_profit_last_year"),
            "road_profit_this_year": _mean_field(summaries, "road_profit_this_year"),
            "feeder_profit_this_year": _mean_field(summaries, "feeder_profit_this_year"),
            "air_profit_this_year": _mean_field(summaries, "air_profit_this_year"),
            "unresolved_vehicles": _mean_field(summaries, "unresolved_vehicles"),
            "airports_per_game": _numbers([item["catchment"]["airports"] for item in summaries]),
            "share_below_one_plane": _numbers([
                item["catchment"]["share_below_one_plane"] for item in summaries
            ]),
        })
        reports[-1]["catchment_mean_of_game_means"] = {
            "share_below_one_plane": reports[-1]["share_below_one_plane"],
            "max_waiting_cargo": _numbers([
                item["catchment"]["max_waiting_cargo"]["mean"] for item in summaries
            ]),
            "rating": _numbers([
                item["catchment"]["rating"]["mean"] for item in summaries
            ]),
            "one_plane_seats": _numbers([
                item["catchment"]["one_plane_seats"]["mean"] for item in summaries
            ]),
            "waiting_per_seat": _numbers([
                item["catchment"]["waiting_per_seat"]["mean"] for item in summaries
            ]),
            "comparable_airports": _numbers([
                item["catchment"]["comparable"] for item in summaries
            ]),
        }
        comparable = sum(item["catchment"]["comparable"] for item in summaries)
        below = sum(item["catchment"]["peak_waiting_below_one_plane"] for item in summaries)
        reports[-1]["pooled_airports"] = sum(item["catchment"]["airports"] for item in summaries)
        reports[-1]["pooled_comparable"] = comparable
        reports[-1]["pooled_below_one_plane"] = below
        reports[-1]["pooled_share_below_one_plane"] = (below / comparable) if comparable else None
        for label in ("fed", "unfed"):
            joined = [item["catchment_by_road_join"][label] for item in summaries]
            joined_comparable = sum(item["comparable"] for item in joined)
            joined_below = sum(item["peak_waiting_below_one_plane"] for item in joined)
            reports[-1]["catchment_mean_of_game_means"][label] = {
                "airports": _numbers([item["airports"] for item in joined]),
                "comparable": _numbers([item["comparable"] for item in joined]),
                "share_below_one_plane": _numbers([item["share_below_one_plane"] for item in joined]),
                "waiting_per_seat": _numbers([item["waiting_per_seat"]["mean"] for item in joined]),
                "max_waiting_cargo": _numbers([item["max_waiting_cargo"]["mean"] for item in joined]),
                "rating": _numbers([item["rating"]["mean"] for item in joined]),
                "pooled_comparable": joined_comparable,
                "pooled_below_one_plane": joined_below,
                "pooled_share_below_one_plane": (
                    joined_below / joined_comparable if joined_comparable else None
                ),
            }
    return {
        "scope": telemetry.get("scope"),
        "unavailable_fields": telemetry.get("unavailable_fields"),
        "groups": reports,
    }


def load_json(path):
    with _open_text(path) as handle:
        return json.load(handle)


def company_report_from_jsonl(path):
    return summarize_company_rows(iter_jsonl(path))


def line_report_from_json(path, passenger_cargo=PASSENGER_CARGO):
    return summarize_line_telemetry(load_json(path), passenger_cargo)


def _fmt_stat(stat, digits=1):
    if not stat or stat.get("mean") is None:
        return "n=0"
    return (
        f"n={stat['n']} moy={stat['mean']:.{digits}f} méd={stat['median']:.{digits}f} "
        f"[{stat['min']:.{digits}f} ; {stat['max']:.{digits}f}]"
    )


def format_company_report(reports):
    lines = []
    for report in reports:
        lines.append(
            f"{report['arm']} policy={report['policy_id']} slot={report['company_slot']} "
            f"parties={report['games']} dates={report['date_min']}..{report['date_max']}"
        )
        for mode in MODES:
            lines.append(f"  {mode}: {_fmt_stat(report['vehicles'][mode], 2)}")
        lines.append(f"  profit_year £: {_fmt_stat(report['profit_year'], 0)}")
        lines.append(f"  airports: {_fmt_stat(report['stations']['airport'], 2)}")
        lines.append(f"  bus stops: {_fmt_stat(report['stations']['bus'], 2)}")
        lines.append(f"  rail st: {_fmt_stat(report['stations']['rail'], 2)}")
        lines.append(f"  air pax cap: {_fmt_stat(report['air_passenger_capacity'], 0)}")
        lines.append(f"  rating médiane gares: {_fmt_stat(report['median_station_rating'], 1)}")
    return "\n".join(lines)


def format_line_report(report):
    lines = [f"scope={report.get('scope')} indisponible={report.get('unavailable_fields')}"]
    for group in report["groups"]:
        lines.append(
            f"{group['arm']} policy={group['policy_id']} parties={group['games']} "
            f"dates={group['date_min']}..{group['date_max']}"
        )
        lines.append(f"  road veh: {_fmt_stat(group['road_vehicles'], 2)}")
        lines.append(f"  feeder proxy veh: {_fmt_stat(group['feeder_vehicles'], 2)}")
        lines.append(f"  feeder share: {_fmt_stat(group['feeder_share'], 3)}")
        lines.append(f"  touch air: {_fmt_stat(group['feeder_touch_air_vehicles'], 2)}")
        lines.append(f"  touch rail: {_fmt_stat(group['feeder_touch_rail_vehicles'], 2)}")
        lines.append(f"  other road: {_fmt_stat(group['other_road_vehicles'], 2)}")
        lines.append(f"  air veh: {_fmt_stat(group['air_vehicles'], 2)}")
        lines.append(f"  rail veh: {_fmt_stat(group['rail_vehicles'], 2)}")
        lines.append(f"  road profit last £: {_fmt_stat(group['road_profit_last_year'], 0)}")
        lines.append(f"  feeder profit last £: {_fmt_stat(group['feeder_profit_last_year'], 0)}")
        lines.append(f"  other road profit last £: {_fmt_stat(group['other_road_profit_last_year'], 0)}")
        lines.append(f"  air profit last £: {_fmt_stat(group['air_profit_last_year'], 0)}")
        lines.append(f"  rail profit last £: {_fmt_stat(group['rail_profit_last_year'], 0)}")
        lines.append(f"  road profit this £: {_fmt_stat(group['road_profit_this_year'], 0)}")
        lines.append(f"  feeder profit this £: {_fmt_stat(group['feeder_profit_this_year'], 0)}")
        lines.append(f"  air profit this £: {_fmt_stat(group['air_profit_this_year'], 0)}")
        catch = group["catchment_mean_of_game_means"]
        lines.append(f"  aéroports/partie: {_fmt_stat(group['airports_per_game'], 2)}")
        pooled = group.get("pooled_share_below_one_plane")
        pooled_text = "n=0" if pooled is None else (
            f"{group['pooled_below_one_plane']}/{group['pooled_comparable']} = {pooled:.3f} "
            f"(aéroports listés {group['pooled_airports']})"
        )
        lines.append(f"  part pic < 1 avion (moyenne des parties): {_fmt_stat(catch['share_below_one_plane'], 3)}")
        lines.append(f"  part pic < 1 avion (pool): {pooled_text}")
        lines.append(f"  attente pic moy/partie: {_fmt_stat(catch['max_waiting_cargo'], 1)}")
        lines.append(f"  note moy/partie: {_fmt_stat(catch['rating'], 1)}")
        lines.append(f"  sièges/avion moy/partie: {_fmt_stat(catch['one_plane_seats'], 1)}")
        lines.append(f"  attente/siège moy/partie: {_fmt_stat(catch['waiting_per_seat'], 3)}")
        for label, title in (("fed", "aéroports joints route"), ("unfed", "aéroports sans route")):
            block = catch[label]
            share = block["pooled_share_below_one_plane"]
            share_text = "n=0" if share is None else (
                f"{block['pooled_below_one_plane']}/{block['pooled_comparable']} = {share:.3f}"
            )
            lines.append(
                f"  {title}: {share_text} ; attente/siège {_fmt_stat(block['waiting_per_seat'], 3)} "
                f"; note {_fmt_stat(block['rating'], 1)}"
            )
        lines.append(f"  non résolus: {_fmt_stat(group['unresolved_vehicles'], 2)}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnostic V242 sur extraits existants")
    sub = parser.add_subparsers(dest="command", required=True)
    company = sub.add_parser("company-jsonl")
    company.add_argument("path")
    lines = sub.add_parser("line-telemetry")
    lines.add_argument("path")
    lines.add_argument("--passenger-cargo", default=PASSENGER_CARGO)
    args = parser.parse_args(argv)
    if args.command == "company-jsonl":
        print(format_company_report(company_report_from_jsonl(args.path)))
    else:
        print(format_line_report(line_report_from_json(args.path, args.passenger_cargo)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
