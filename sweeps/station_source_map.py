"""Supplement OpenTTDLab tables with raw map RIFF chunks, save version 362 only.

Read-only diagnostic; never a NoAI feature. OpenTTD 15.3 map_sl.cpp/town_map.h
define the layout. Unsupported versions, NewGRFs and malformed maps fail closed.
"""
import lzma
import math
import re
import struct
import zlib

# Original airports only, table/airport_defaults.h at OpenTTD 15.3.
AIRPORT_CATCHMENTS = (4, 5, 4, 6, 8, 4, 4, 10, 4, 4)


def raw_map_chunks(data):
    if len(data) < 8:
        raise ValueError("truncated header")
    version = int.from_bytes(data[4:6], "big")
    if version != 362:
        raise ValueError("only savegame version 362 is qualified")
    compression = data[:4]
    if compression == b"OTTN":
        payload = data[8:]
    elif compression == b"OTTZ":
        payload = zlib.decompress(data[8:])
    elif compression == b"OTTX":
        payload = lzma.decompress(data[8:])
    else:
        raise ValueError("unsupported compression")
    offset = 0

    def read(n):
        nonlocal offset
        if n < 0 or offset + n > len(payload):
            raise ValueError("truncated chunk")
        result = payload[offset:offset+n]
        offset += n
        return result

    def gamma():
        b = read(1)[0]
        for count, mask, prefix in ((0, 0x7f, 0), (1, 0x3f, 0x80),
                                    (2, 0x1f, 0xc0), (3, 0x0f, 0xe0), (4, 7, 0xf0)):
            if b >> (7-count) == prefix >> (7-count):
                return ((b & mask) << (8*count)) | int.from_bytes(read(count), "big")
        raise ValueError("invalid gamma")

    chunks, seen = {}, set()
    while True:
        tag = read(4)
        if tag == b"\0\0\0\0":
            break
        if tag in seen:
            raise ValueError("duplicate chunk")
        seen.add(tag)
        m = read(1)[0]
        kind = m & 15
        if kind == 0:
            size = (m >> 4) << 24 | int.from_bytes(read(3), "big")
            block = read(size)
            if tag in (b"MAPT", b"MAP2", b"MAPE", b"M3LO", b"MAP8"):
                chunks[tag.decode()] = block
        elif kind in (1, 2, 3, 4) and m == kind:
            while (size := gamma()) != 0:
                read(size - 1)  # Includes sparse index/header in the encoded block.
        else:
            raise ValueError("unsupported chunk framing")
    if offset != len(payload):
        raise ValueError("trailing bytes")
    if set(chunks) != {"MAPT", "MAP2", "MAPE", "M3LO", "MAP8"}:
        raise ValueError("missing map chunk")
    return chunks


def original_house_populations(source):
    body = source.split("extern const HouseSpec _original_house_specs[] = {", 1)[1].split("};", 1)[0]
    entries = re.findall(r"\bMS\(\s*[^,]+,\s*[^,]+,\s*(\d+),", body)
    if len(entries) != 110:
        raise ValueError("original house table identity/count unsupported")
    return list(map(int, entries))


def decode_map(data, game, populations):
    chunks = {k: v["records"] for k, v in game["chunks"].items()}
    if game["savegame_version"] != 362 or chunks.get("NGRF") or chunks.get("HIDS"):
        raise ValueError("only unmodified original houses in version 362 are qualified")
    dims = chunks["MAPS"]["0"]
    width, height = dims["dim_x"], dims["dim_y"]
    n = width * height
    raw = raw_map_chunks(data)
    if any(len(raw[k]) != n * (2 if k in ("MAP2", "MAP8") else 1) for k in raw):
        raise ValueError("map chunk length/dimensions mismatch")
    ids = list(struct.unpack(f">{n}H", raw["MAP2"]))
    types = list(struct.unpack(f">{n}H", raw["MAP8"]))
    houses, facilities = [], []
    sums = {}
    for tile, value in enumerate(raw["MAPT"]):
        kind = value >> 4
        if kind == 3:  # MP_HOUSE, map_type.h in 15.3
            house_type = types[tile] & 0xfff
            if house_type >= len(populations) or str(ids[tile]) not in chunks["CITY"]:
                raise ValueError("invalid original house/town identity")
            population = populations[house_type]
            completed = bool(raw["M3LO"][tile] & 128)
            houses.append({"tile": tile, "town": ids[tile], "house_type": house_type,
                           "population": population, "completed": completed})
            if completed:
                sums[ids[tile]] = sums.get(ids[tile], 0) + population
        elif kind == 5:  # MP_STATION
            facilities.append({"tile": tile, "station": ids[tile], "type": (raw["MAPE"][tile] >> 3) & 15})
    # CITY normally omits reconstructible population. Never invent a cache checksum.
    verified = 0
    for town, record in chunks["CITY"].items():
        if "population" not in record:
            continue
        if sums.get(int(town), 0) != record["population"]:
            raise ValueError(f"decoded house population differs from CITY town {town}")
        verified += 1
    return {"width": width, "height": height, "houses": houses, "facility_tiles": facilities,
            "town_population_reconstructed": sums, "town_population_cache_verified": verified}


def station_catchments(decoded, stations, modified=True):
    """Union of actual facility tile expansions, not station bounding boxes."""
    width, height = decoded["width"], decoded["height"]
    result = {}
    for facility in decoded["facility_tiles"]:
        sid, kind, tile = facility["station"], facility["type"], facility["tile"]
        if kind in (6, 7, 8):  # Waypoints/buoys have no catchment.
            continue
        if sid not in stations:
            raise ValueError("facility without normal station identity")
        if kind not in range(6):
            raise ValueError("unknown facility type")
        radius = 4
        if modified:
            if kind == 1:
                airport = stations[sid]["airport.type"]
                if not 0 <= airport < len(AIRPORT_CATCHMENTS):
                    raise ValueError("custom airport unsupported")
                radius = AIRPORT_CATCHMENTS[airport]
            else:
                radius = {0: 4, 2: 3, 3: 3, 4: 4, 5: 5}[kind]
        covered = result.setdefault(sid, set())
        x, y = tile % width, tile // width
        for yy in range(max(0, y-radius), min(height, y+radius+1)):
            covered.update(range(yy*width + max(0, x-radius),
                                 yy*width + min(width, x+radius+1)))
    return result


def audit_sources(decoded, game, cargo):
    """Snapshot mechanism audit. Weights/ratings are NOT a yearly forecast.

    Qualified for original binomial town generation, scale 100 only. Cargo must
    be resolved as PASS externally. Continuous allocations omit integer rounding.
    """
    chunks = {k: v["records"] for k, v in game["chunks"].items()}
    settings = chunks["PATS"]["0"]
    if (settings["economy.town_cargogen_mode"] != 1 or
            settings["economy.town_cargo_scale"] != 100 or
            settings["station.serve_neutral_industries"] != 1):
        raise ValueError("unsupported production or neutral-station setting")
    towns = chunks["CITY"]
    stations, eligible = {}, {}
    for sid, entry in chunks.get("STNN", {}).items():
        normal = entry.get("normal", [])
        if not normal:
            continue
        st = normal[0]
        base = st["base"][0]
        stations[int(sid)] = st
        good = st["goods"][cargo]
        # Engine does not require HasRating here: eligibility is last_speed != 0.
        if (good["rating"] == 0 or
                (settings["order.selectgoods"] and good["last_speed"] == 0) or
                base["facilities"] == 4):  # truck-stop-only cannot receive PASS
            continue
        town = towns[str(base["town"] - 1)]  # serialized TownRef, not TownID
        owner = base["owner"]
        if owner != 16 and town["exclusive_counter"] > 0 and town["exclusivity"] != owner:
            continue
        eligible[int(sid)] = {"owner": owner, "rating": good["rating"],
                              "airport": bool(base["facilities"] & 8)}
    catchments = station_catchments(decoded, stations, bool(settings["station.modified_catchment"]))
    # NoAI-visible rival airport tiles/owners only. Unknown foreign type/rating
    # are NOT read: original small-airport radius and equal company ratings prior.
    visible = {}
    for facility in decoded["facility_tiles"]:
        if facility["type"] != 1 or facility["station"] not in stations:
            continue
        owner = stations[facility["station"]]["base"][0]["owner"]
        if not 0 <= owner < 15:
            continue
        coverage = station_catchments({**decoded, "facility_tiles": [facility]},
                                      {facility["station"]: {"airport.type": 0}},
                                      bool(settings["station.modified_catchment"]))
        for tile in coverage.get(facility["station"], ()):
            visible.setdefault(tile, set()).add(owner)
    totals = {sid: {**st, "source_weight": 0, "shared_rival_weight": 0,
                   "own_only_weight": 0.0, "all_companies_weight": 0.0,
                   "own_only_monthly": 0.0, "all_companies_monthly": 0.0,
                   "visible_airports_monthly": 0.0,
                   "missing_source_towns": set(),
                   "producer_count": 0} for sid, st in eligible.items()}
    source_towns = {}
    production = {}
    for tid, town in towns.items():
        if not town.get("valid_history", 0) & 2:
            continue
        for good in town["supplied"]:
            if good["cargo"] == cargo and len(good["history"]) > 1:
                value = good["history"][1]["production"]
                if isinstance(value, int) and value >= 0:
                    production[int(tid)] = value
    for house in decoded["houses"]:
        if house["completed"] and house["population"] > 0:
            source_towns[house["town"]] = source_towns.get(house["town"], 0) + (house["population"]+7)//8
    for house in decoded["houses"]:
        if not house["completed"] or house["population"] == 0:
            continue
        weight = (house["population"] + 7) // 8
        town = towns[str(house["town"])]
        covering = {sid: st for sid, st in eligible.items()
                    if house["tile"] in catchments.get(sid, ()) and
                    (town["exclusive_counter"] == 0 or town["exclusivity"] == st["owner"])}
        if not covering:
            continue
        best, sums = {}, {}
        for st in covering.values():
            owner, rating = st["owner"], st["rating"]
            best[owner] = max(best.get(owner, 0), rating)
            sums[owner] = sums.get(owner, 0) + rating
        for sid, st in covering.items():
            owner, rating = st["owner"], st["rating"]
            row = totals[sid]
            row["source_weight"] += weight
            row["producer_count"] += 1
            row["shared_rival_weight"] += weight if len(best) > 1 else 0
            own_fraction = (best[owner]+1)/256 * rating/sums[owner]
            all_fraction = ((max(best.values())+1)/256 * best[owner]/sum(best.values()) * rating/sums[owner])
            row["own_only_weight"] += weight * own_fraction
            row["all_companies_weight"] += weight * all_fraction
            if house["town"] not in production:
                row["missing_source_towns"].add(house["town"])
            else:
                generated = weight * production[house["town"]] / source_towns[house["town"]]
                row["own_only_monthly"] += generated * own_fraction
                row["all_companies_monthly"] += generated * all_fraction
                rivals = visible.get(house["tile"], set()) - {owner}
                row["visible_airports_monthly"] += generated * own_fraction / (1 + len(rivals))
    for row in totals.values():
        row["missing_source_towns"] = sorted(row["missing_source_towns"])
        if row["missing_source_towns"]:
            row["own_only_monthly"] = row["all_companies_monthly"] = None
            row["visible_airports_monthly"] = None
        row["competition_ratio"] = (row["all_companies_weight"]/row["own_only_weight"]
                                    if row["own_only_weight"] else None)
    # Reproduce B9's denominator separately from density and competition.
    # GetCargoProduction counts population-bearing original house tiles,
    # including construction; actual generation requires completion.
    for sid, row in totals.items():
        town_id = stations[sid]["base"][0]["town"] - 1
        town = towns[str(town_id)]
        population = decoded["town_population_reconstructed"].get(town_id, 0)
        radius = min(20, 4 + int(math.sqrt(population)/8))
        tx, ty = town["xy"] % decoded["width"], town["xy"] // decoded["width"]
        producers = [h for h in decoded["houses"] if h["population"] > 0]
        whole = [h for h in producers if h["town"] == town_id]
        covered = [h for h in whole if h["tile"] in catchments.get(sid, ())]
        window = [h for h in producers if
                  abs(h["tile"] % decoded["width"] - tx) <= radius and
                  abs(h["tile"] // decoded["width"] - ty) <= radius]
        weight = sum((h["population"]+7)//8 for h in covered if h["completed"])
        total_weight = source_towns.get(town_id, 0)
        row.update(town=town_id, b9_radius=radius, b9_window_producers=len(window),
                   whole_town_producers=len(whole), covered_town_producers=len(covered),
                   b9_coverage_fraction=min(len(covered), len(window))/len(window) if window else None,
                   whole_town_count_fraction=len(covered)/len(whole) if whole else None,
                   whole_town_weight_fraction=weight/total_weight if total_weight else None)
        b9_own, b9_visible = 0.0, 0.0
        if town_id in production and window:
            per_house = production[town_id] / len(window)
            clamp = min(len(covered), len(window))/len(covered) if covered else 1.0
            for house in covered:
                ratings = [st["rating"] for other, st in eligible.items() if
                           st["owner"] == row["owner"] and house["tile"] in catchments.get(other, ())]
                fraction = (max(ratings)+1)/256 * row["rating"]/sum(ratings)
                amount = per_house * clamp * fraction
                b9_own += amount
                b9_visible += amount / (1 + len(visible.get(house["tile"], set()) - {row["owner"]}))
            row["b9_own_monthly"], row["b9_visible_monthly"] = b9_own, b9_visible
        else:
            row["b9_own_monthly"] = row["b9_visible_monthly"] = None
    return {"station_sources": totals, "town_source_weights": source_towns,
            "eligible_stations": len(eligible), "qualified_yearly_forecast": False}
