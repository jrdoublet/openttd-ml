"""Sonde de catalogue 1950-2000 (taches.md S4 item 6).

CatalogProbe ne joue pas : un rafraichissement annuel, panneaux CA/CB/CO/CP/CE.
La mesure 1970-1989 est results/catalogue_churn.json ; celle-ci allonge jusqu'a 2000
pour l'electrification, INTERNATIONAL (1990) et le debut du parc (1950).
"""
import argparse
import json
import re
from pathlib import Path

from openttdlab import local_folder, run_experiments

ROOT = Path("/work")

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1950
map_x = 8
map_y = 8
"""

AIRPORT_NAMES = [
    "SMALL", "LARGE", "METROPOLITAN", "INTERNATIONAL", "COMMUTER",
    "INTERCON", "HELIPORT", "HELISTATION", "HELIDEPOT",
]
# Ordre vanilla OpenGFX 7.1 / OpenTTD 15.3 (AIRailTypeList) : 0 RAIL, 1 ELECTRIC, 2 MONO, 3 MAGLEV.
RAIL_TYPE_NAMES = ["RAIL", "ELECTRIC", "MONO", "MAGLEV"]

RE_CA = re.compile(r"^CA\|(\d+)\|(\d+)\|(\d+)$")
RE_CB = re.compile(r"^CB\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_CO = re.compile(r"^CO\|(\d+)\|(\d+)\|(\d+)$")
RE_CP = re.compile(r"^CP\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_CE = re.compile(r"^CE\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")


def decode_mask(mask, names):
    return [name for i, name in enumerate(names) if mask & (1 << i)]


def keep(row):
    chunks = row["chunks"]
    signs = [s["name"] for s in chunks.get("SIGN", {}).values()]
    return ({
        "seed": row["experiment"]["opex_seed"],
        "date": str(row["date"]),
        "signs": signs,
        "openttd_output": row.get("output"),
    },)


def parse_years(signs):
    by_year = {}
    for sign in signs:
        if m := RE_CA.match(sign):
            y = int(m.group(1))
            d = by_year.setdefault(y, {"year": y})
            d["towns"] = int(m.group(2))
            d["industries"] = int(m.group(3))
        elif m := RE_CB.match(sign):
            y = int(m.group(1))
            d = by_year.setdefault(y, {"year": y})
            d["rail"] = int(m.group(2))
            d["road"] = int(m.group(3))
            d["water"] = int(m.group(4))
            d["air"] = int(m.group(5))
            d["airports"] = decode_mask(int(m.group(6)), AIRPORT_NAMES)
        elif m := RE_CO.match(sign):
            y = int(m.group(1))
            d = by_year.setdefault(y, {"year": y})
            d["ops_towns"] = int(m.group(2))
            d["ops_industries"] = int(m.group(3))
        elif m := RE_CP.match(sign):
            y = int(m.group(1))
            d = by_year.setdefault(y, {"year": y})
            d["ops_pairs"] = int(m.group(2))
            d["ops_engines"] = int(m.group(3))
            d["ops_airports"] = int(m.group(4))
        elif m := RE_CE.match(sign):
            y = int(m.group(1))
            d = by_year.setdefault(y, {"year": y})
            n_types = int(m.group(2))
            counts = [int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))]
            d["n_rail_types"] = n_types
            d["rail_types_available"] = RAIL_TYPE_NAMES[:n_types]
            d["locos_rail"] = counts[0] if n_types >= 1 else 0
            d["locos_electric"] = counts[1] if n_types >= 2 else 0
            d["locos_mono"] = counts[2] if n_types >= 3 else 0
            d["locos_maglev"] = counts[3] if n_types >= 4 else 0
    return [by_year[y] for y in sorted(by_year)]


def first_year(rows, pred):
    for row in rows:
        if pred(row):
            return row["year"]
    return None


def summarise(rows):
    def series(key):
        return [row.get(key) for row in rows if key in row]

    intro = {
        "electric_rail_available": first_year(
            rows, lambda r: "ELECTRIC" in (r.get("rail_types_available") or [])),
        "electric_loco": first_year(rows, lambda r: (r.get("locos_electric") or 0) > 0),
        "monorail_available": first_year(
            rows, lambda r: "MONO" in (r.get("rail_types_available") or [])),
        "monorail_loco": first_year(rows, lambda r: (r.get("locos_mono") or 0) > 0),
        "maglev_available": first_year(
            rows, lambda r: "MAGLEV" in (r.get("rail_types_available") or [])),
        "maglev_loco": first_year(rows, lambda r: (r.get("locos_maglev") or 0) > 0),
    }
    for name in AIRPORT_NAMES:
        intro["airport_" + name.lower()] = first_year(
            rows, lambda r, n=name: n in (r.get("airports") or []))
    start, end = rows[0], rows[-1]
    return {
        "years": [start["year"], end["year"]],
        "intro": intro,
        "engines_start": {k: start.get(k) for k in ("rail", "road", "water", "air")},
        "engines_end": {k: end.get(k) for k in ("rail", "road", "water", "air")},
        "ops_engines_median": sorted(series("ops_engines"))[len(series("ops_engines")) // 2]
        if series("ops_engines") else None,
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("years", type=int, nargs="?", default=51)
    parser.add_argument("seeds", type=int, nargs="*", default=[42])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.years <= 0:
        parser.error("years doit etre positif")
    if not args.seeds:
        parser.error("au moins une graine")
    return args


def main():
    args = parse_args()
    result_path = args.output if args.output is not None else (
        ROOT / "results" / f"catalogue_churn_1950_{1949 + args.years}.json")
    if not result_path.is_absolute():
        result_path = ROOT / result_path
    experiments = [{
        "seed": seed, "days": 365 * args.years, "openttd_config": CFG,
        "ais": (local_folder(str(ROOT / "ai" / "CatalogProbe"), "CatalogProbe"),),
        "opex_seed": seed,
    } for seed in args.seeds]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=min(args.workers, len(args.seeds)), result_processor=keep,
        experiments=experiments,
    ))
    rows_by_seed = {seed: [] for seed in args.seeds}
    for row in rows:
        rows_by_seed[row["seed"]].append(row)
    missing = [seed for seed, series in rows_by_seed.items() if not series]
    if missing:
        raise RuntimeError(f"aucune sauvegarde pour les graines: {missing}")

    runs = []
    for seed in args.seeds:
        series = sorted(rows_by_seed[seed], key=lambda row: row["date"])
        per_year = parse_years(series[-1]["signs"])
        runs.append({
            "seed": seed,
            "n_savegames": len(series),
            "final_date": series[-1]["date"],
            "per_year": per_year,
            "summary": summarise(per_year) if per_year else {},
        })
        print(f"=== {args.years} ans, graine {seed}, {series[-1]['date']} ===")
        summary = runs[-1]["summary"]
        print(f"annees {summary.get('years')}  intro {summary.get('intro')}")
        print(f"moteurs debut {summary.get('engines_start')}  fin {summary.get('engines_end')}")

    payload = {
        "openttd_version": OPENTTD_VERSION, "opengfx_version": OPENGFX_VERSION,
        "starting_year": 1950, "years": args.years, "seeds": args.seeds,
        "openttd_config": CFG,
        "note": "CatalogProbe, starting_year=1950, config gelee sinon. "
                "CE = locos par type de rail (pas wagons). "
                "La sonde 1970-1989 reste results/catalogue_churn.json.",
        "runs": runs,
    }
    result_path.write_text(json.dumps(payload, indent=2))
    print(f"ecrit {result_path}")


if __name__ == "__main__":
    main()
