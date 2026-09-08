"""Gradient de difficulte controle sur le choix de paire de villes, au lieu du "essaie 12 paires,
prend la premiere qui marche" precedent (voir sweeps/phase2_trainline_run.py, commit 37db73b).

ai/TrainLineAI/main.nut trie desormais TOUTES les paires candidates par score decroissant
(population_a*population_b/distance -- l'heuristique qui a regle les NOPATH, inchangee) et prend
directement celle au rang `pair_rank` (nouveau parametre d'IA ; 0 = meilleur score = la paire que
l'ancienne boucle essayait en premier, donc encore faisable en pratique aujourd'hui). Un seul
preflight, sans repli automatique sur une autre paire si celle-ci echoue : un echec au rang N est
maintenant un vrai point de donnee sur la difficulte de ce rang (NOPATH/STNFAIL/PAIROOR...),
pas un echec cache par un fallback. Voir docs/methode.md et [[trainlineai-construction-bugs]]
pour le detail du changement.

Echantillonnage de `pair_rank` non uniforme (geometrique, `random.Random` seede pour la
reproductibilite) plutot qu'un balayage uniforme 0..N : la zone interessante (autour de la
frontiere faisable/infaisable) est proche de 0 pour la plupart des paires de villes rencontrees
en pratique (verifie par sondage manuel avant ce run -- voir la memoire du projet), donc un
balayage uniforme jusqu'a un rang eleve gaspillerait la majorite des parties sur des paires
clairement absurdes (deux petites villes tres eloignees, quasi surement NOPATH) sans densifier
la transition qui nous interesse. `pair_rank=0` est toujours inclus par construction (point de
reference connu-faisable).

100 lignes = 5 graines (des cartes/topographies differentes -- le pool de paires candidates et
donc la signification concrete d'un rang donne varient par carte) x 20 rangs de paire par graine.
num_trains/wagons_per_train/engine_rank fixes (config "medium" deja utilisee dans
phase2_trainline_run.py) pour isoler le seul axe etudie ici plutot que le confondre avec les axes
moteur/materiel deja couverts par l'autre campagne.
"""
import json
import math
import random
import re
from openttdlab import run_experiments, bananas_ai_library, local_folder

INFRA_LIFE_YEARS = 30  # hypothese assumee, documentee dans docs/methode.md (voir phase2_profit_ligne.py)

OPENTTD_CONFIG = """
[difficulty]
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

DAYS = 365 * 10  # duree de partie Phase 0 -- voir README.md

SEEDS = [42, 100, 7, 999, 2026]
RANKS_PER_SEED = 20
GEOMETRIC_P = 0.1          # moyenne ~9 -- concentre pres de 0, avec une queue jusqu'a quelques dizaines
MAX_RANK = 59               # reste sous max_value=99 declare dans info.nut, avec marge
NUM_TRAINS = 2
WAGONS_PER_TRAIN = 2
ENGINE_RANK = 1

SAMPLE_SEED = 20260826       # reproductibilite de l'echantillonnage (pas une graine de partie)


def geometric_ranks(rng, n, p, max_rank):
    """n rangs uniques, 0 toujours inclus, le reste tire d'une loi geometrique tronquee a
    max_rank (inverse-CDF : k = floor(log(1-u)/log(1-p))) pour densifier les petits rangs."""
    ranks = {0}
    while len(ranks) < n:
        u = rng.random()
        k = int(math.log(1 - u) / math.log(1 - p))
        ranks.add(min(k, max_rank))
    return sorted(ranks)


_rng = random.Random(SAMPLE_SEED)
# (seed, pair_rank) -- un rang different par graine, tire independamment (le pool de paires
# candidates differe par carte, donc le meme entier de rang n'a pas le meme sens d'une graine a
# l'autre ; on ne cherche pas a aligner les rangs entre graines, seulement a couvrir le gradient
# de chacune).
RUNS = [
    (seed, pair_rank)
    for seed in SEEDS
    for pair_rank in geometric_ranks(_rng, RANKS_PER_SEED, GEOMETRIC_P, MAX_RANK)
]

STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE_COST_RE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")


def line_profit(chunks, owner=0):
    """Somme profit_last_year (annee complete) des vehicules de tete (unitnumber != 0) de cette
    compagnie, et l'age max moyen du materiel (annees) pour l'amortissement -- voir
    phase2_trainline_run.py / phase2_profit_ligne.py."""
    vehs = chunks.get("VEHS", {})
    total_profit = 0
    max_ages_days = []
    for v in vehs.values():
        if v.get("type") != 0:
            continue
        common = v["train"][0]["common"][0]
        if common["owner"] != owner or common["unitnumber"] == 0:
            continue
        total_profit += common["profit_last_year"]
        max_ages_days.append(common["max_age"])
    if not max_ages_days:
        return None
    return {
        "n_lead_vehicles": len(max_ages_days),
        "sum_profit_last_year": total_profit,
        "avg_max_age_years": round((sum(max_ages_days) / len(max_ages_days)) / 365.0, 2),
    }


def keep_signs_and_params(row):
    ai_params = dict(row["experiment"]["ais"][0][1])
    signs = row["chunks"].get("SIGN", {})
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "ai_params": ai_params,
        "signs": [s["name"] for s in signs.values()],
        "veh_summary": line_profit(row["chunks"]),
    },)


if __name__ == "__main__":
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=3,
        result_processor=keep_signs_and_params,
        ai_libraries=(
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
        experiments=(
            {
                "seed": seed,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": (
                    local_folder(
                        "ai/TrainLineAI", "TrainLineAI",
                        ai_params=(
                            ("num_trains", NUM_TRAINS),
                            ("wagons_per_train", WAGONS_PER_TRAIN),
                            ("engine_rank", ENGINE_RANK),
                            ("pair_rank", pair_rank),
                            ("line_index", i),
                        ),
                    ),
                ),
            }
            for i, (seed, pair_rank) in enumerate(RUNS)
        ),
    )

    # Une seule ligne par experience ici -- garder le dernier savegame de chacune.
    by_line = {}
    for r in results:
        idx = r["ai_params"]["line_index"]
        prev = by_line.get(idx)
        if prev is None or r["date"] > prev["date"]:
            by_line[idx] = r

    records = []
    for idx in sorted(by_line):
        r = by_line[idx]
        status = None
        detail = None
        vehicle_cost = None
        for s in r["signs"]:
            m = STATUS_RE.match(s)
            if m:
                status = m.groups()
                continue
            m = DETAIL_RE.match(s)
            if m:
                detail = m.groups()
                continue
            m = VEHICLE_COST_RE.match(s)
            if m:
                vehicle_cost = int(m.group(2))
        rec = {
            "line_index": idx,
            "seed": r["seed"],
            "pair_rank": r["ai_params"]["pair_rank"],
            "ai_params": r["ai_params"],
            "raw_signs": r["signs"],
        }
        if status:
            rec.update({
                "stage": status[1],
                "reason": status[2],
                "built": int(status[3]),
                "requested": int(status[4]),
            })
        if detail:
            rec.update({
                "town_a": int(detail[1]),
                "town_b": int(detail[2]),
                "distance": int(detail[3]),
                "cost": int(detail[4]),
                "vehicle_cost": vehicle_cost,
            })
            veh = r["veh_summary"]
            if vehicle_cost is not None and veh is not None and veh["avg_max_age_years"] > 0:
                infra_cost = rec["cost"] - vehicle_cost
                vehicle_amortization = vehicle_cost / veh["avg_max_age_years"]
                infra_amortization = infra_cost / INFRA_LIFE_YEARS
                amortization = vehicle_amortization + infra_amortization
                rec.update(veh)
                rec["infra_cost"] = infra_cost
                rec["vehicle_amortization_annual"] = round(vehicle_amortization)
                rec["infra_amortization_annual"] = round(infra_amortization)
                rec["amortization_annual"] = round(amortization)
                rec["profit_ligne"] = round(veh["sum_profit_last_year"] - amortization)
        records.append(rec)

    print(f"{len(records)} lignes / {len(results)} savegames captures\n")
    for rec in records:
        print(
            f"line={rec['line_index']:3d} seed={rec['seed']:4d} pair_rank={rec['pair_rank']:2d} -> "
            f"{rec.get('stage','?'):8s} {rec.get('reason','?'):8s} "
            f"{rec.get('built','?')}/{rec.get('requested','?')}  "
            f"towns={rec.get('town_a','-')}-{rec.get('town_b','-')} "
            f"dist={rec.get('distance','-')} cost={rec.get('cost','-')} "
            f"profit_ligne={rec.get('profit_ligne','-')}"
        )

    n_success = sum(1 for r in records if r.get("stage") == "success")
    n_pairoor = sum(1 for r in records if r.get("reason") == "PAIROOR")
    print(f"\n{n_success}/{len(records)} success, {n_pairoor} pair_rank_out_of_range")

    with open("results/phase2_pair_rank_run.json", "w") as f:
        json.dump(records, f, indent=2)
    print("\nEcrit dans results/phase2_pair_rank_run.json")
