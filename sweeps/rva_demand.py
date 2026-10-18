"""RVA-08, offline endpoint contract; no town-total -> tile-volume conversion.

Inputs must describe actual station tiles/radii and producer identities. This
module cannot reconstruct those from town centres or an API aggregate count.
Station::RecomputeCatchment, OpenTTD 15.3 station.cpp:494-506, unions squares
around individual station tiles. A station's enclosing rectangle is not its
catchment. Neutral industry stations require their separate engine contract.
"""
from rva_dry_cycle import known


def station_allocation(production, stations):
    """Expected monthly allocation, before packet rounding (15.3 station_cmd.cpp:4599).

    Ratings are raw 0..255, not NoAI percentages. Eligibility (visited cargo,
    exclusivity, selective servicing) must already have been resolved by caller.
    Group by COMPANY, then divide its allocation among ALL eligible stations.
    Unknown competitor ratings must be supplied as scenarios, never defaulted.
    """
    if not known(production) or production < 0:
        return None
    best, totals, ids = {}, {}, set()
    for s in stations:
        if s['station'] in ids:
            raise ValueError('A joined station receives one allocation')
        ids.add(s['station'])
        r = s.get('rating_raw')
        if not known(r) or not 0 <= r <= 255:
            return None
        if r == 0:
            continue
        owner = s['owner']
        best[owner] = max(best.get(owner, 0), r)
        totals[owner] = totals.get(owner, 0) + r
    if not best:
        return {s['station']: 0.0 for s in stations}
    # UpdateStationWaiting consumes 1/256 units: station_cmd.cpp (amount_fract).
    captured = production * (max(best.values()) + 1) / 256
    return {s['station']: captured * best[s['owner']] / sum(best.values())
            * s['rating_raw'] / totals[s['owner']] if s['rating_raw'] else 0.0
            for s in stations}


def local_demand(town_monthly, tile_weights, covered_tiles, stations_by_tile,
                 candidate, *, inventory_complete=True):
    """Town production distributed over its *entire* producer inventory.

    Weight = API producer count, not cargo units. Uniform output per producer
    is an explicit initial estimator, including NewGRF uncertainty, not a game
    rule. Each tile belongs to one town; candidate coverage is its real union.
    Both stations_by_tile and weights are one cargo/date only. Missing coverage
    or volume is unknown. No supplied/production subtraction: that would charge
    station ratings twice. Supplied is a validation observable instead.
    """
    if (inventory_complete is not True or not known(town_monthly) or town_monthly < 0
            or any(not known(w) or w < 0 for w in tile_weights.values())):
        return {'status': 'not_covered', 'line_month': None, 'own_delta_month': None}
    total = sum(tile_weights.values())
    if total <= 0:
        return {'status': 'not_covered', 'line_month': None, 'own_delta_month': None}
    demand, own_delta, effects = 0.0, 0.0, {}
    for tile in set(covered_tiles).intersection(tile_weights):
        production = town_monthly * tile_weights[tile] / total
        old = stations_by_tile.get(tile)
        if old is None:
            return {'status': 'not_covered', 'line_month': None, 'own_delta_month': None}
        before = station_allocation(production, old)
        after = station_allocation(production, [*old, candidate])
        if before is None or after is None:
            return {'status': 'not_covered', 'line_month': None, 'own_delta_month': None}
        demand += after[candidate['station']]
        old_own = [s for s in old if s['owner'] == candidate['owner']]
        own_delta += after[candidate['station']] + sum(
            after[s['station']] - before[s['station']] for s in old_own)
        for s in old_own:
            sid = s['station']
            effects[sid] = effects.get(sid, 0) + after[sid] - before[sid]
    return {'status': 'estimated_uniform_producer_output', 'line_month': demand,
            'own_delta_month': own_delta, 'station_delta_month': effects,
            'unit': 'cargo_units_per_observed_month',
            'rounding': 'expectation_before_packet_rounding',
            'uncertainty': 'producer_heterogeneity_and_future_rating'}


def catchment(station_tiles, map_width, map_height):
    """station_tiles = iterable of (x, y, effective_radius); no default radius."""
    if any(type(v) is not int or v <= 0 for v in (map_width, map_height)):
        raise ValueError("Map dimensions must be explicit positive integers")
    covered = set()
    for x, y, radius in station_tiles:
        if (any(type(v) is not int for v in (x, y, radius)) or radius < 0
                or not 0 <= x < map_width or not 0 <= y < map_height):
            raise ValueError("Invalid station tile/radius")
        # Inclusive tile interval, clipped at map boundaries, per engine source.
        covered.update((px, py)
            for px in range(max(0, x - radius), min(map_width, x + radius + 1))
            for py in range(max(0, y - radius), min(map_height, y + radius + 1)))
    return covered


def endpoint(coverage_tiles, producers, cargo, *, inventory_complete, services):
    """One cargo/direction, explicit coverage; missing local volume stays unknown.

    producers: unique producer_id, tiles, cargos:{id: {monthly, source}}.
    monthly is production before station rating, never a planned/delivered flow.
    services: own service_id, cargo, coverage_tiles, capacity_month, carried_month.
    Spare capacity is descriptive; it is not lost demand or a gain coefficient.
    Inputs must share context, date and month convention before calling.
    """
    if cargo is None:
        raise ValueError("Resolve cargo identity before endpoint evaluation")
    covered = set(coverage_tiles)
    seen, selected = set(), []
    for producer in producers:
        identity = producer["producer_id"]
        if identity in seen:
            raise ValueError("Duplicate producer identity: aggregate its tiles first")
        seen.add(identity)
        if covered.intersection(producer["tiles"]) and cargo in producer["cargos"]:
            selected.append(producer)
    known_volume = 0
    missing = []
    for producer in selected:
        record = producer["cargos"][cargo]
        volume = record.get("monthly")
        if not known(volume) or volume < 0 or not record.get("source"):
            missing.append(producer["producer_id"])
        else:
            known_volume += volume
    complete = inventory_complete is True and not missing
    overlaps, seen_services = [], set()
    for service in services:
        if service["cargo"] != cargo:
            continue
        if service["service_id"] in seen_services:
            raise ValueError("Duplicate service identity")
        seen_services.add(service["service_id"])
        tiles = covered.intersection(service["coverage_tiles"])
        affected = [p["producer_id"] for p in selected if tiles.intersection(p["tiles"])]
        capacity, carried = service.get("capacity_month"), service.get("carried_month")
        spare = (max(0, capacity - carried) if known(capacity) and capacity >= 0
                 and known(carried) and 0 <= carried <= capacity else None)
        overlaps.append({"service_id": service["service_id"], "producer_ids": affected,
                         "covered_tiles": len(tiles), "spare_capacity_month": spare,
                         "displaced_month": None})
    return {"cargo": cargo, "producer_ids": [p["producer_id"] for p in selected],
            "producer_count": len(selected) if inventory_complete is True else None,
            "observed_producer_count": len(selected), "missing_volume_ids": missing,
            "production_month": known_volume if complete else None,
            "known_production_subtotal_month": known_volume,
            "volume_coverage": "covered_inputs" if complete else "not_covered",
            "unit": "cargo_units_per_explicit_input_month", "own_services": overlaps,
            "line_demand_month": None, "company_increment_month": None}


def endpoints(endpoint_a, endpoint_b):
    """Keep both directions; shared producers cannot be summed without allocation."""
    if endpoint_a["cargo"] != endpoint_b["cargo"]:
        raise ValueError("Distinct cargos must remain in distinct endpoint pairs")
    shared = set(endpoint_a["producer_ids"]).intersection(endpoint_b["producer_ids"])
    a, b = endpoint_a["production_month"], endpoint_b["production_month"]
    return {"cargo": endpoint_a["cargo"], "a": endpoint_a, "b": endpoint_b,
            "shared_producer_ids": sorted(shared),
            "production_total_month": a + b if not shared and a is not None and b is not None else None,
            "line_demand_month": None, "allocation_coverage": "requires_distribution_model"}
