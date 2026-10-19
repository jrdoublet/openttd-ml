#!/usr/bin/env python3
"""V267 : variables de carte par graine, lues dans la sauvegarde initiale (docs/taches.md, V267).

La carte est fixee par la graine et la configuration du banc avant toute decision d'IA : une
partie d'un jour sans IA suffit. Sous-commandes :

  screen    (dans Docker, OpenTTDLab) joue chaque graine 1 jour sans IA, lit la sauvegarde du
            1er janvier 1970 et ecrit une ligne JSON de variables par graine ;
  features  (hors Docker) recalcule les variables depuis des .sav deja archives, pour les tests.

Variables (OpenTTD 15.3, version de sauvegarde 362 ; disposition des bits verifiee dans
tile_map.h, water_map.h, tunnelbridge_map.h, table/build_industry.h) :
  relief    altitude moyenne, ecart-type, maximum, rugosite (|dh| moyen entre voisines),
            part de tuiles en pente ;
  eau       parts de mer, de riviere (lacs compris), de cote, part d'eau "large" (lacs, baies) ;
  villes    nombre, taille (tuiles de maisons) : plus grande, mediane, part des 3 plus grandes,
            villes cotieres ;
  industries nombre, primaires, secondaires, centrales, plates-formes petrolieres, banques ;
  liaisons  paires de villes a 20..120 tuiles : part coupee par une riviere et longueur a
            franchir (ponts), part coupee par la mer (bateaux, avions), denivele le long du segment ;
            idem mines de charbon -> centrales.

Exemple PC :
  docker run --rm --network host --cpus=10 --memory=8g -v openttd-lab-home:/home/lab \\
    -v "$PWD":/work -w /work openttd-lab:latest \\
    python3 sweeps/v267_maps.py screen --count 3000 --out results/v267_maps_3000.jsonl --workers 10
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from station_source_map import raw_map_chunks  # noqa: E402

MP_CLEAR, MP_RAILWAY, MP_ROAD, MP_HOUSE, MP_TREES, MP_STATION, MP_WATER, MP_VOID, MP_INDUSTRY = range(9)
WATER_SEA, WATER_CANAL, WATER_RIVER = 0, 1, 2
WATER_TILE_COAST = 1
# table/build_industry.h (types d'origine, climat tempere)
PRIMARY = {0, 3, 5, 9, 11, 18}       # charbon, foret, plate-forme, ferme, puits, fer
SECONDARY = {2, 4, 6, 8}             # scierie, raffinerie, usine, acierie
POWER_STATION, OIL_RIG, BANK, COAL_MINE = 1, 5, 12, 0
PAIR_MIN, PAIR_MAX = 20, 120         # portee utile rail/route d'OpexAI
FEATURE_CHUNKS = ("MAPT", "MAPH", "MAPO", "MAP2", "MAP5")


def segment(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    """Tuiles d'un segment de Bresenham, extremites comprises."""
    out = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return out
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def crossing(points, width, water, height) -> tuple[int, int, int]:
    """(plus longue suite de riviere, plus longue suite de mer, denivele max-min) sur un segment.

    water[t] : 0 terre, WATER_RIVER + 1 riviere ou lac, WATER_SEA + 1 mer.
    """
    runs = {WATER_RIVER + 1: 0, WATER_SEA + 1: 0}
    best = dict(runs)
    hs = []
    for x, y in points:
        t = y * width + x
        hs.append(height[t])
        for kind in runs:
            runs[kind] = runs[kind] + 1 if water[t] == kind else 0
            best[kind] = max(best[kind], runs[kind])
    return best[WATER_RIVER + 1], best[WATER_SEA + 1], max(hs) - min(hs)


def pair_stats(prefix: str, a_points, b_points, width, water, height, same=False) -> dict:
    """Paires a PAIR_MIN..PAIR_MAX tuiles : rivieres a franchir (ponts), mer, denivele."""
    river, sea, climbs, n = [], 0, [], 0
    for i, (ax, ay) in enumerate(a_points):
        for j, (bx, by) in enumerate(b_points):
            if same and j <= i:
                continue
            d = abs(ax - bx) + abs(ay - by)
            if not PAIR_MIN <= d <= PAIR_MAX:
                continue
            n += 1
            r, m, climb = crossing(segment(ax, ay, bx, by), width, water, height)
            climbs.append(climb)
            if r:
                river.append(r)
            sea += bool(m)
    return {
        f"{prefix}_pairs": n,
        f"{prefix}_river_cross_share": len(river) / n if n else 0.0,
        f"{prefix}_river_run_mean": statistics.fmean(river) if river else 0.0,
        f"{prefix}_river_run_max": max(river) if river else 0,
        f"{prefix}_sea_cross_share": sea / n if n else 0.0,
        f"{prefix}_climb_mean": statistics.fmean(climbs) if climbs else 0.0,
        f"{prefix}_climb_p90": sorted(climbs)[int(0.9 * (len(climbs) - 1))] if climbs else 0,
    }


def map_features(data: bytes, chunks: dict) -> dict:
    """Variables de carte depuis les octets d'une sauvegarde 362 et ses chunks OpenTTDLab."""
    records = {k: v.get("records", v) for k, v in chunks.items()}
    dims = records["MAPS"]["0"]
    width, height_dim = dims["dim_x"], dims["dim_y"]
    n = width * height_dim
    raw = raw_map_chunks(data, FEATURE_CHUNKS)
    kinds = [v >> 4 for v in raw["MAPT"]]
    height = list(raw["MAPH"])
    m1, m5 = raw["MAPO"], raw["MAP5"]
    m2 = [int.from_bytes(raw["MAP2"][2 * i:2 * i + 2], "big") for i in range(n)]
    if len(kinds) != n or len(height) != n or len(m1) != n or len(m5) != n:
        raise ValueError("map chunk length/dimensions mismatch")

    land = [t for t in range(n) if kinds[t] != MP_VOID]
    is_water = [False] * n
    water = [0] * n
    sea = river = coast = 0
    for t in land:
        if kinds[t] != MP_WATER:
            continue
        if (m5[t] >> 4) == WATER_TILE_COAST:
            coast += 1
            continue
        wclass = (m1[t] >> 5) & 3
        if wclass == WATER_SEA:
            sea += 1
        elif wclass == WATER_RIVER:
            river += 1
        is_water[t] = True
        water[t] = wclass + 1
    wide = 0
    diffs, sloped = [], 0
    for t in land:
        x, y = t % width, t // width
        nb = [u for u in (t + 1 if x + 1 < width else None, t + width if y + 1 < height_dim else None)
              if u is not None and kinds[u] != MP_VOID]
        local = [abs(height[t] - height[u]) for u in nb]
        diffs.extend(local)
        if any(local):
            sloped += 1
        if is_water[t] and 0 < x < width - 1 and 0 < y < height_dim - 1:
            if all(is_water[u] for u in (t - 1, t + 1, t - width, t + width)):
                wide += 1
    hl = [height[t] for t in land]
    total = len(land)

    town_tiles: dict[int, int] = {}
    for t in land:
        if kinds[t] == MP_HOUSE:
            town_tiles[m2[t]] = town_tiles.get(m2[t], 0) + 1
    towns = records.get("CITY", {})
    sizes = sorted((town_tiles.get(int(k), 0) for k in towns), reverse=True)
    town_xy = [(v["xy"] % width, v["xy"] // width) for v in towns.values()]
    coastal = 0
    for tx, ty in town_xy:
        r = 8
        if any(is_water[y * width + x] and (m1[y * width + x] >> 5) & 3 == WATER_SEA
               for y in range(max(0, ty - r), min(height_dim, ty + r + 1))
               for x in range(max(0, tx - r), min(width, tx + r + 1))):
            coastal += 1

    inds = list(records.get("INDY", {}).values())
    itypes = [v["type"] for v in inds]
    ind_xy = lambda wanted: [((v["location.tile"] % width) + 1, (v["location.tile"] // width) + 1)
                             for v in inds if v["type"] == wanted]

    out = {
        "tiles": total,
        "height_mean": statistics.fmean(hl), "height_std": statistics.pstdev(hl), "height_max": max(hl),
        "roughness": statistics.fmean(diffs) if diffs else 0.0, "slope_share": sloped / total,
        "sea_share": sea / total, "river_share": river / total, "coast_share": coast / total,
        "wide_water_share": wide / total,
        "towns": len(sizes), "town_tiles_max": sizes[0] if sizes else 0,
        "town_tiles_median": statistics.median(sizes) if sizes else 0,
        "town_top3_share": sum(sizes[:3]) / sum(sizes) if sum(sizes) else 0.0,
        "coastal_towns": coastal,
        "industries": len(inds),
        "industries_primary": sum(t in PRIMARY for t in itypes),
        "industries_secondary": sum(t in SECONDARY for t in itypes),
        "power_stations": itypes.count(POWER_STATION), "oil_rigs": itypes.count(OIL_RIG),
        "banks": itypes.count(BANK),
    }
    out.update(pair_stats("town", town_xy, town_xy, width, water, height, same=True))
    out.update(pair_stats("coal", ind_xy(COAL_MINE), ind_xy(POWER_STATION), width, water, height))
    return out


def features_from_file(path: Path) -> dict:
    import openttdlab
    data = path.read_bytes()
    game = openttdlab.parse_savegame(iter([data]))
    if game["savegame_version"] != 362:
        raise ValueError("only savegame version 362 is qualified")
    return map_features(data, game["chunks"])


def read_seeds(args) -> list[int]:
    if args.seeds_file:
        return [int(x) for x in Path(args.seeds_file).read_text().split()]
    from v267_seeds import EXCLUDED, SEEDS_40, lcg_seeds
    historic = [s for s in SEEDS_40 if s not in EXCLUDED]
    return historic + lcg_seeds(args.count - len(historic), args.init, EXCLUDED)


def cmd_screen(args) -> None:
    import openttdlab
    import bench_v2
    seeds = read_seeds(args)
    out = Path(args.out)
    done = set()
    if out.exists():
        done = {json.loads(line)["seed"] for line in out.read_text().splitlines() if line.strip()}
    todo = [s for s in seeds if s not in done]
    cfg = bench_v2.make_cfg(1970, 8)
    print(f"{len(todo)} graines a lire ({len(done)} deja faites) -> {out}", flush=True)
    for start in range(0, len(todo), args.batch):
        batch = todo[start:start + args.batch]
        archive = Path(tempfile.mkdtemp(prefix="v267maps_", dir=args.tmp))
        try:
            bench_v2.enable_savegame_cleanup(archive)
            list(openttdlab.run_experiments(
                openttd_version=bench_v2.OPENTTD_VERSION, opengfx_version=bench_v2.OPENGFX_VERSION,
                max_workers=args.workers, result_processor=lambda row: [],
                experiments=[{"seed": s, "days": 1, "openttd_config": cfg, "ais": ()} for s in batch]))
            with out.open("a") as fh:
                for i, seed in enumerate(batch):
                    feats = features_from_file(archive / str(i) / "save" / "0.sav")
                    fh.write(json.dumps({"seed": seed, **feats}) + "\n")
        finally:
            shutil.rmtree(archive, ignore_errors=True)
        print(f"  {min(start + args.batch, len(todo))}/{len(todo)}", flush=True)


def cmd_features(args) -> None:
    for path in args.sav:
        print(json.dumps({"path": path, **features_from_file(Path(path))}))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen")
    s.add_argument("--seeds-file")
    s.add_argument("--count", type=int, default=3000, help="sans --seeds-file : historiques + LCG V267")
    s.add_argument("--init", type=int, default=20261019)
    s.add_argument("--out", required=True)
    s.add_argument("--workers", type=int, default=10)
    s.add_argument("--batch", type=int, default=100)
    s.add_argument("--tmp", default="results")
    s.set_defaults(func=cmd_screen)
    f = sub.add_parser("features")
    f.add_argument("sav", nargs="+")
    f.set_defaults(func=cmd_features)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
