"""Combien de lignes rail sont PREDITES a 2 trains, et combien en recoivent reellement ?

Contexte (docs/taches.md S0 octodecies) : la revue de code du 2026-09-02 etablit que
OpexBuildLine ne pose JAMAIS de seconde voie ni de second train a la construction initiale --
OpexTryDoubleTrack (builder_rail.nut:426-428) interroge AIStation.GetStationID sur une ancre ou
aucune gare n'existe encore, parce qu'il est appele depuis OpexPlanRailRoute (884-974, qui ne
contient aucun BuildRailStation) et non depuis OpexExecuteRailPlan (le premier BuildRailStation
est a :1015). Le garde-fou sort donc au premier test et plan.doubleTrack reste a 0.

Si c'est vrai, economy.nut peut predire trains=2 -- ce qui gonfle profitAnnual, revenueAnnual et
capital du candidat, donc son rang a l'election modale et au sac a dos -- alors que la ligne
construite ne livre que le revenu d'UN train.

Ce script ne mesure pas une performance : il COMPTE. Aucun code d'IA a modifier, la sonde existe
deja derriere le reglage rail_cost_probe (main.nut:1332) :

    DC|idx|capital|actualCost|candidate.trains|result.trains|result.doubleTrack

Verdict attendu si la revue a raison : result.trains == 1 et doubleTrack == 0 partout, et la
proportion de candidate.trains == 2 dit si l'enjeu est marginal ou majeur.
"""
import json
import re
from collections import Counter
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
RESULT = ROOT / "results" / "opex_two_trains_diag.json"

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
# Plusieurs graines : une seule ne tranche rien (docs/taches.md, banc monograine insuffisant).
SEEDS = [42, 100, 7, 999, 2026, 1, 17, 73]
YEARS = 3

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

RE_DC = re.compile(r"^DC\|(\d+)\|(-?\d+)\|(-?\d+)\|(\d+)\|(\d+)\|(\d+)$")


def keep(row):
    # keep() tourne dans les processus worker : ne rien accumuler au niveau module,
    # seule la valeur de retour franchit la frontiere de fork.
    signs = [s["name"] for s in row["chunks"].get("SIGN", {}).values()]
    return ({"date": str(row["date"]), "seed": row["experiment"]["seed"],
             "signs": [s for s in signs if s.startswith("DC|")]},)


def main():
    experiments = [{
        "seed": seed, "days": 365 * YEARS, "openttd_config": CFG,
        "ais": (local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI",
                             (("probe_cost", 1),)),),
    } for seed in SEEDS]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION, max_workers=3,
        result_processor=keep, experiments=experiments,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
    ))

    # Garder la derniere sauvegarde de chaque graine : les panneaux DC sont cumulatifs.
    last = {}
    for r in rows:
        s = r["seed"]
        if s not in last or r["date"] > last[s]["date"]:
            last[s] = r

    per_seed, pred, real, dbl = {}, Counter(), Counter(), Counter()
    unparsed = []
    for seed, r in sorted(last.items()):
        lines = []
        for sign in r["signs"]:
            m = RE_DC.match(sign)
            if not m:
                unparsed.append(sign)
                continue
            idx, capital, actual, predT, realT, doubleT = (int(g) for g in m.groups())
            lines.append({"idx": idx, "capital": capital, "actual_cost": actual,
                          "trains_predits": predT, "trains_reels": realT,
                          "double_voie": doubleT})
            pred[predT] += 1
            real[realT] += 1
            dbl[doubleT] += 1
        per_seed[seed] = {"date": r["date"], "n_lignes": len(lines), "lignes": lines}

    total = sum(pred.values())
    ecart = sum(1 for s in per_seed.values() for l in s["lignes"]
                if l["trains_predits"] != l["trains_reels"])
    payload = {
        "openttd_version": OPENTTD_VERSION, "opengfx_version": OPENGFX_VERSION,
        "seeds": SEEDS, "years": YEARS, "openttd_config": CFG,
        "total_lignes_rail": total,
        "trains_predits": dict(sorted(pred.items())),
        "trains_reels": dict(sorted(real.items())),
        "double_voie": dict(sorted(dbl.items())),
        "lignes_en_ecart_predit_vs_reel": ecart,
        "part_en_ecart_pct": round(100.0 * ecart / total, 1) if total else None,
        "signes_non_parses": unparsed,
        "par_graine": per_seed,
    }
    RESULT.write_text(json.dumps(payload, indent=2))

    print("lignes rail construites (8 graines x 3 ans) :", total)
    print("trains PREDITS  :", dict(sorted(pred.items())))
    print("trains REELS    :", dict(sorted(real.items())))
    print("double voie     :", dict(sorted(dbl.items())))
    print("lignes en ecart predit-vs-reel : %s / %s (%s%%)"
          % (ecart, total, payload["part_en_ecart_pct"]))
    if unparsed:
        print("panneaux non parses :", len(unparsed), unparsed[:3])
    print("ecrit", RESULT)


if __name__ == "__main__":
    main()
