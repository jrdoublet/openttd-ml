"""Captured new cargo, independent of loading/losses; OpenTTD 15.3 LGRP.

Supply is NOT a monotonically cumulative counter: compression and graph merges
rescale it. Only unchanged graph membership/compression/station identity permits
an exact difference. Cargo IDs are retained separately, never assumed to be PASS.
"""
from physical_counters import decode_stations


def _int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _first(value):
    return value[0] if isinstance(value, list) and value else value


def extract_town_month(chunks):
    """Only LAST_MONTH (1): precisely the information exposed by NoAI.

    Do not export the save's longer history as an AI feature. NoAI must build
    its own history from successive months; partial current month (0) is refused.
    """
    towns = chunks.get("CITY")
    if not isinstance(towns, dict):
        return {"ok": False, "reason": "missing_city", "towns": []}
    rows, errors = [], []
    for town_id, town in towns.items():
        if not isinstance(town, dict) or not _int(town.get("valid_history")):
            errors.append("invalid_town")
            continue
        if not town["valid_history"] & 2:
            continue
        supplied = town.get("supplied")
        if not isinstance(supplied, list):
            errors.append("invalid_supplied")
            continue
        for entry in supplied:
            history = entry.get("history") if isinstance(entry, dict) else None
            cargo = entry.get("cargo") if isinstance(entry, dict) else None
            if not _int(cargo) or not isinstance(history, list) or len(history) < 2 or not isinstance(history[1], dict):
                errors.append("invalid_cargo_history")
                continue
            production, captured = history[1].get("production"), history[1].get("transported")
            if not _int(production) or not _int(captured) or not 0 <= captured <= production:
                errors.append("invalid_month")
                continue
            rows.append({"town": int(town_id), "cargo": cargo,
                         "production": production, "supplied_all_companies": captured})
    return {"ok": not errors, "reason": ",".join(sorted(set(errors))) or None, "towns": rows}


def extract_station_supply(chunks, owner):
    decoded = decode_stations(chunks.get("STNN"), target_owner=owner)
    graphs = chunks.get("LGRP")
    dates = chunks.get("DATE")
    if not decoded.get("chunk_valid") or not isinstance(graphs, dict) or not isinstance(dates, dict):
        return {"ok": False, "reason": "missing_or_invalid_chunks", "nodes": []}
    date = next(iter(dates.values()), {}).get("economy_date")
    if not _int(date):
        return {"ok": False, "reason": "missing_economy_date", "nodes": []}
    stations = chunks["STNN"]
    owned = set(decoded["station_ids"])
    rows, errors, seen = [], [], set()
    for graph_id, graph in graphs.items():
        if not isinstance(graph, dict):
            errors.append("invalid_graph")
            continue
        cargo, compression, nodes = graph.get("cargo"), graph.get("last_compression"), graph.get("nodes")
        if not _int(cargo) or cargo < 0 or not _int(compression) or compression > date or not isinstance(nodes, list):
            errors.append("invalid_graph_header")
            continue
        if any(not isinstance(n, dict) or not _int(n.get("station")) or not _int(n.get("xy")) for n in nodes):
            errors.append("invalid_node_identity")
            continue
        membership = sorted([[n["station"], n["xy"]] for n in nodes])
        for node in nodes:
            station = node["station"]  # Direct StationID, NOT a +1 reference.
            if station not in owned:
                continue
            body = _first(stations.get(str(station), stations.get(station)))
            body = _first(body.get("normal", body))
            base = _first(body.get("base"))
            supply, update = node.get("supply"), node.get("last_update")
            if (not _int(supply) or not 0 <= supply <= 0xFFFFFFFF or not _int(update)
                    or update > date or not _int(base.get("build_date"))):
                errors.append("invalid_node_counter")
                continue
            key = (station, cargo)
            if key in seen:
                errors.append("duplicate_station_cargo")
                continue
            seen.add(key)
            rows.append({"station": station, "cargo": cargo, "graph": str(graph_id),
                         "town_ref": base.get("town"),
                         "compression": compression, "membership": membership,
                         "xy": node["xy"], "build_date": base["build_date"],
                         "supply": supply, "last_update": update,
                         "facilities": base.get("facilities")})
    return {"ok": not errors, "reason": ",".join(sorted(set(errors))) or None,
            "economy_date": date, "nodes": rows}


def supply_intervals(previous, current):
    """Unknowns remain None. Missing nodes are not evidence of zero arrivals."""
    if not previous.get("ok") or not current.get("ok"):
        return [{"exact": False, "reason": "invalid_snapshot", "arrivals": None}]
    days = current["economy_date"] - previous["economy_date"]
    if days <= 0 or days > 32:
        return [{"exact": False, "reason": "invalid_interval", "arrivals": None}]
    old = {(n["station"], n["cargo"]): n for n in previous["nodes"]}
    new = {(n["station"], n["cargo"]): n for n in current["nodes"]}
    result = []
    for key in sorted(old.keys() | new.keys()):
        a, b = old.get(key), new.get(key)
        reason = None
        if a is None or b is None:
            reason = "missing_boundary_node"
        elif any(a[field] != b[field] for field in ("graph", "compression", "membership", "xy", "build_date")):
            reason = "compression_merge_or_identity_change"
        elif b["supply"] < a["supply"] or b["last_update"] < a["last_update"]:
            reason = "counter_reset_or_wrap"
        elif b["supply"] > a["supply"] and b["last_update"] <= previous["economy_date"]:
            reason = "inconsistent_update_date"
        arrivals = b["supply"] - a["supply"] if reason is None else None
        result.append({"station": key[0], "cargo": key[1], "period_days": days,
                       "start_date": previous["economy_date"], "end_date": current["economy_date"],
                       "exact": reason is None, "reason": reason, "arrivals": arrivals,
                       "monthly_captured": arrivals * 30.4 / days if arrivals is not None else None})
    return result
