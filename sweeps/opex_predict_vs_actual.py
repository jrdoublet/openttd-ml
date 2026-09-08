"""Predit-vs-reel pour l'etage 1 d'OpexAI (economy.nut).

Objectif de la tache du 2026-08-28 : l'ancienne mesure (docs/opexai...) montrait un profit reel
~10x plus bas que le profit predit par OpexLineEconomics. Ce script fait tourner OpexAI 10 ans,
graine 42 (comportement connu : 3 lignes construites), avec l'instrumentation ajoutee dans
main.nut/candidates.nut (signs OF/OJ/OK/OQ/OT au moment de la construction = predit ; signs
OY/OZ/OU/OO chaque annee = reel mesure), puis rassemble les deux series par ligne.

Meme config gelee que sweeps/bench.py : OpenTTD 15.3, OpenGFX 7.1, carte 256x256, depart 1970.
"""
import json
import re
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
RESULT = ROOT / "results" / "opex_predict_vs_actual.json"

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

# Predit, logue une fois au moment de la construction (idx = index dans _lines).
RE_OF = re.compile(r"^OF\|(\d+)\|(-?\d+)$")   # revenueAnnual predit
RE_OJ = re.compile(r"^OJ\|(\d+)\|(-?\d+)$")   # runningAnnual predit
RE_OK = re.compile(r"^OK\|(\d+)\|(-?\d+)$")   # amortAnnual predit
RE_OQ = re.compile(r"^OQ\|(\d+)\|(-?\d+)\|(\d+)$")  # carried predit, trains predit
RE_OT = re.compile(r"^OT\|(\d+)\|(-?\d+)$")   # oneWayDays predit

# Reel, logue chaque annee (idx, year).
RE_OY = re.compile(r"^OY\|(\d+)\|(\d+)\|(-?\d+)\|(-?\d+)$")           # ratingA, ratingB
RE_OZ = re.compile(r"^OZ\|(\d+)\|(\d+)\|(-?\d+)$")                     # profit reel (somme vehicules)
RE_OU = re.compile(r"^OU\|(\d+)\|(\d+)\|(\d+)\|(-?\d+)$")              # vehCount, runCost reel
RE_OO = re.compile(r"^OO\|(\d+)\|(\d+)\|(-?\d+)$")                     # revenue reel implicite

# Construction elle-meme, pour distance/annee de mise en service.
RE_OR = re.compile(r"^OR\|(\d+)\|(\d+)\|(\d+)\|(\w+)$")                # idx, distance, iterations, reason
RE_PK = re.compile(r"^PK\|(\d+)\|([PF])\|(\d+)$")                      # idx, kind, monthly (production brute)


def keep(row):
    signs = [s["name"] for s in row["chunks"].get("SIGN", {}).values()]
    return ({"date": str(row["date"]), "signs": signs},)


def parse(all_signs):
    predicted = {}   # idx -> dict
    actual_series = {}  # idx -> year -> dict
    built = {}        # idx -> {distance, iterations, reason}

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
        # dernier point mesure (le plus d'annees ecoulees depuis construction = etat le plus etabli)
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
