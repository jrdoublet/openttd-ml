"""Diagnostic de l'effondrement de note des lignes fret (tache du 2026-08-28).

Deux hypotheses en jeu, aucune verifiee sur de l'etat de jeu reel avant cette tache :
  1. l'industrie source ou puits ferme ;
  2. OF_FULL_LOAD_ANY est pose aux DEUX bouts (builder_rail.nut ~L302-305) alors qu'une ligne
     fret est structurellement a sens unique (candidates.nut : producteur -> accepteur du MEME
     cargo, jamais l'inverse) -- le train se coincerait au puits, attendant un plein chargement de
     retour qui n'arrive jamais.

Instrumentation ajoutee dans main.nut::_reportLines pour trancher, chaque annee et par ligne fret :
  - IA|idx|year|srcAlive|dstAlive|srcProd  (industries valides ? production source ?)
  - VS|idx|year|state|order                 (etat du vehicule, index d'ordre courant : 0=source, 1=puits)
  - VL|idx|year|speed|load                  (vitesse courante, chargement du cargo de la ligne)

Court (4 ans) : les donnees deja recueillies (results/opex_predict_vs_actual_postfix_freight.json)
montrent l'effondrement de la note du puits des la premiere mesure post-construction, donc 4 ans
suffisent a observer construction + collapse pour au moins 2 lignes fret.

Meme config gelee que sweeps/opex_predict_vs_actual.py : OpenTTD 15.3, OpenGFX 7.1, carte 256x256,
graine 42, depart 1970.
"""
import json
import re
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
RESULT = ROOT / "results" / "opex_freight_diag.json"

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
SEED = 42
YEARS = 4

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

RE_OR = re.compile(r"^OR\|(\d+)\|(\d+)\|(\d+)\|(\w+)$")
RE_PK = re.compile(r"^PK\|(\d+)\|([PF])\|(\d+)$")
RE_OY = re.compile(r"^OY\|(\d+)\|(\d+)\|(-?\d+)\|(-?\d+)$")
RE_OO = re.compile(r"^OO\|(\d+)\|(\d+)\|(-?\d+)$")
RE_IA = re.compile(r"^IA\|(\d+)\|(\d+)\|(-?\d)\|(-?\d)\|(-?\d+)$")
RE_VS = re.compile(r"^VS\|(\d+)\|(\d+)\|(\d+)\|(-?\d+)\|(-?\d+)$")
RE_VL = re.compile(r"^VL\|(\d+)\|(\d+)\|(\d+)\|(-?\d+)\|(-?\d+)$")


def keep(row):
    signs = [s["name"] for s in row["chunks"].get("SIGN", {}).values()]
    return ({"date": str(row["date"]), "signs": signs},)


def parse(all_signs):
    built = {}
    kind = {}
    series = {}  # idx -> year -> dict

    for sign in all_signs:
        if m := RE_OR.match(sign):
            idx = int(m.group(1))
            if m.group(4) == "OK":
                built[idx] = {"distance": int(m.group(2)), "iterations": int(m.group(3))}
        elif m := RE_PK.match(sign):
            idx = int(m.group(1))
            kind[idx] = "pax" if m.group(2) == "P" else "freight"
        elif m := RE_OY.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            series.setdefault(idx, {}).setdefault(year, {})["ratingA"] = int(m.group(3))
            series[idx][year]["ratingB"] = int(m.group(4))
        elif m := RE_OO.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            series.setdefault(idx, {}).setdefault(year, {})["revenue"] = int(m.group(3))
        elif m := RE_IA.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            d = series.setdefault(idx, {}).setdefault(year, {})
            d["srcAlive"] = int(m.group(3))
            d["dstAlive"] = int(m.group(4))
            d["srcProd"] = int(m.group(5))
        elif m := RE_VS.match(sign):
            idx, year, slot = int(m.group(1)), int(m.group(2)), int(m.group(3))
            d = series.setdefault(idx, {}).setdefault(year, {}).setdefault("vehicles", {}).setdefault(slot, {})
            d["state"] = int(m.group(4))
            d["order"] = int(m.group(5))
        elif m := RE_VL.match(sign):
            idx, year, slot = int(m.group(1)), int(m.group(2)), int(m.group(3))
            d = series.setdefault(idx, {}).setdefault(year, {}).setdefault("vehicles", {}).setdefault(slot, {})
            d["speed"] = int(m.group(4))
            d["load"] = int(m.group(5))

    lines = []
    for idx in sorted(built):
        lines.append({
            "line_index": idx,
            "kind": kind.get(idx, "?"),
            "distance": built[idx]["distance"],
            "series": series.get(idx, {}),
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
