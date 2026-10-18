"""RVA-08, offline endpoint contract; no town-total -> tile-volume conversion.

Inputs must describe actual station tiles/radii and producer identities. This
module cannot reconstruct those from town centres or an API aggregate count.
Station::RecomputeCatchment, OpenTTD 15.3 station.cpp:494-506, unions squares
around individual station tiles. A station's enclosing rectangle is not its
catchment. Neutral industry stations require their separate engine contract.
"""
from rva_dry_cycle import known


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
