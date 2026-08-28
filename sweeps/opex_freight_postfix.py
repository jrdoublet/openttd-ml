"""Verification post-correctif (2026-08-28) : meme protocole exact que
docs/opex_predict_vs_actual_postfix_freight.json (seed 42, 10 ans, meme config gelee), mais avec
le correctif applique dans builder_rail.nut::OpexBuildTrains -- le puits d'une ligne fret ne pose
plus OF_FULL_LOAD_ANY (seule la source, qui produit reellement le cargo, continue de le faire).

Avant le correctif, les 3 lignes fret de cette graine s'effondraient (note -1, revenu 0) des la
2e annee suivant la construction -- diagnostic dans docs/opex_freight_diag.json (train bloque en
VS_AT_STATION a l'ordre du puits). Ce script confirme si la note et le revenu restent reels plus
longtemps apres le correctif.
"""
import json
import re
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
RESULT = ROOT / "docs" / "opex_predict_vs_actual_postfix_freight_v2.json"

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
SEED = 42
YEARS = 10

CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""

RE_OF = re.compile(r"^OF\|(\d+)\|(-?\d+)$")
RE_OJ = re.compile(r"^OJ\|(\d+)\|(-?\d+)$")
RE_OK = re.compile(r"^OK\|(\d+)\|(-?\d+)$")
RE_OQ = re.compile(r"^OQ\|(\d+)\|(-?\d+)\|(\d+)$")
RE_OT = re.compile(r"^OT\|(\d+)\|(-?\d+)$")
RE_OY = re.compile(r"^OY\|(\d+)\|(\d+)\|(-?\d+)\|(-?\d+)$")
RE_OZ = re.compile(r"^OZ\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OU = re.compile(r"^OU\|(\d+)\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OO = re.compile(r"^OO\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OR = re.compile(r"^OR\|(\d+)\|(\d+)\|(\d+)\|(\w+)$")
RE_PK = re.compile(r"^PK\|(\d+)\|([PF])\|(\d+)$")
RE_IA = re.compile(r"^IA\|(\d+)\|(\d+)\|(-?\d)\|(-?\d)\|(-?\d+)$")


def keep(row):
    signs = [s["name"] for s in row["chunks"].get("SIGN", {}).values()]
    return ({"date": str(row["date"]), "signs": signs},)


def parse(all_signs):
    predicted = {}
    actual_series = {}
    built = {}

    for sign in all_signs:
        if m := RE_OF.match(sign):
            idx = int(m.group(1)); predicted.setdefault(idx, {})["revenueAnnual"] = int(m.group(2))
        elif m := RE_OJ.match(sign):
            idx = int(m.group(1)); predicted.setdefault(idx, {})["runningAnnual"] = int(m.group(2))
        elif m := RE_OK.match(sign):
            idx = int(m.group(1)); predicted.setdefault(idx, {})["amortAnnual"] = int(m.group(2))
        elif m := RE_OQ.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})["carried"] = int(m.group(2))
            predicted[idx]["trains"] = int(m.group(3))
        elif m := RE_OT.match(sign):
            idx = int(m.group(1)); predicted.setdefault(idx, {})["oneWayDays"] = int(m.group(2))
        elif m := RE_OY.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            actual_series.setdefault(idx, {}).setdefault(year, {})["ratingA"] = int(m.group(3))
            actual_series[idx][year]["ratingB"] = int(m.group(4))
        elif m := RE_OZ.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            actual_series.setdefault(idx, {}).setdefault(year, {})["profit"] = int(m.group(3))
        elif m := RE_OU.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            actual_series.setdefault(idx, {}).setdefault(year, {})["vehCount"] = int(m.group(3))
            actual_series[idx][year]["runCost"] = int(m.group(4))
        elif m := RE_OO.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            actual_series.setdefault(idx, {}).setdefault(year, {})["revenue"] = int(m.group(3))
        elif m := RE_IA.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            d = actual_series.setdefault(idx, {}).setdefault(year, {})
            d["srcAlive"] = int(m.group(3)); d["dstAlive"] = int(m.group(4)); d["srcProd"] = int(m.group(5))
        elif m := RE_OR.match(sign):
            idx = int(m.group(1))
            if m.group(4) == "OK":
                built[idx] = {"distance": int(m.group(2)), "iterations": int(m.group(3))}
        elif m := RE_PK.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})["kind"] = "pax" if m.group(2) == "P" else "freight"
            predicted[idx]["monthly"] = int(m.group(3))

    lines = []
    for idx in sorted(built):
        pred = predicted.get(idx, {})
        pred["profitAnnual"] = pred.get("revenueAnnual", 0) - pred.get("runningAnnual", 0) - pred.get("amortAnnual", 0)
        years = actual_series.get(idx, {})
        last_year = max(years) if years else None
        last = years.get(last_year, {}) if last_year is not None else {}
        lines.append({
            "line_index": idx,
            "distance": built[idx]["distance"],
            "iterations": built[idx]["iterations"],
            "predicted": pred,
            "actual_last_year": last_year,
            "actual": last,
            "actual_series": years,
        })
    return lines


def main():
    experiments = [{
        "seed": SEED, "days": 365 * YEARS, "openttd_config": CFG,
        "ais": (local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ()),),
    }]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION, max_workers=1,
        result_processor=keep, experiments=experiments,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
    ))
    rows.sort(key=lambda r: r["date"])
    final = rows[-1]
    lines = parse(final["signs"])
    payload = {
        "openttd_version": OPENTTD_VERSION, "opengfx_version": OPENGFX_VERSION,
        "seed": SEED, "years": YEARS, "openttd_config": CFG,
        "n_savegames": len(rows), "final_date": final["date"],
        "lines": lines, "raw_signs_final": final["signs"],
    }
    RESULT.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    print("ecrit", RESULT)


if __name__ == "__main__":
    main()
