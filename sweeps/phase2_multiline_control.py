"""Experience de controle : mesure l'ampleur reelle de la cannibalisation de passagers quand
plusieurs instances de TrainLineAI tournent SIMULTANEMENT dans la MEME partie -- avant
d'implementer le correctif "villes disjointes" (voir docs/methode.md et le plan de session).

Jusqu'ici, chaque dico d'experience passe a `run_experiments()` (dans tous les scripts sweeps/)
n'a jamais contenu qu'UNE seule entree `local_folder(...)` dans son tuple `ais` -- confirme par
lecture directe du code source d'OpenTTDLab (`run_experiments`/`_run_experiment`) qu'une partie
est alors entierement isolee (une compagnie, un processus OpenTTD dedie). Aucune cannibalisation
n'est donc possible dans les bancs `phase2_trainline_run.py`/`phase2_pair_rank_run.py`.

Ce script utilise pour la premiere fois plusieurs entrees `local_folder(...)` dans UN MEME dico
d'experience : `_run_experiment` demarre alors bien plusieurs compagnies IA simultanees dans une
seule partie partagee (mecanisme confirme en lisant son code, jamais exploite dans ce depot
avant ce script). C'est l'"orchestrateur multi-lignes" deja anticipe (mais non implemente) dans
docs/methode.md.

Meme graine (42), meme config, meme premiere paire (pair_rank=0 -> T6-2 pour cette graine,
cout=41520, deja mesuree en isolation totale dans phase2_pair_rank_run.py : profit_ligne=-154257,
sum_profit_last_year=-152360 -- et +64216/+62319 dans l'ancien banc phase2_trainline_run.py, une
divergence separee et non expliquee par la cannibalisation, voir la note dans docs/methode.md).
N=1/5/15 compagnies simultanees : la compagnie pair_rank=0/line_index=0 est le point de reference
fixe present dans les trois experiences ; les autres (pair_rank=1..N-1) sont les lignes
concurrentes qui cannibalisent potentiellement ses passagers en partageant le meme bassin de
villes. Ce run tourne SANS le correctif "villes disjointes" -- volontairement, pour mesurer le
biais brut avant de le corriger.

Parsing owner-aware (deviation necessaire par rapport a phase2_pair_rank_run.py, qui n'avait
jamais qu'une compagnie/owner par savegame) : le chunk SIGN expose owner en plus de name (deja
documente dans docs/methode.md) -- on le garde ici pour batir la correspondance
line_index -> owner a partir du panneau de statut, puis on appelle line_profit(chunks, owner=...)
avec l'owner resolu au lieu du defaut code en dur owner=0. Reste valable de grouper par owner
seul (pas besoin de suivre la chaine ORDR) puisque chaque COMPAGNIE ne construit toujours qu'UNE
seule ligne ici -- c'est le nombre de compagnies par partie qui change, pas le nombre de lignes
par compagnie.
"""
import json
import re
from openttdlab import run_experiments, bananas_ai_library, local_folder

INFRA_LIFE_YEARS = 30  # hypothese assumee, documentee dans docs/methode.md (voir phase2_profit_ligne.py)

# Configuration historique volontairement épinglée : docs/phase2_multiline_control.json et
# docs/phase2_multiline_verify.json ont été produits en 1950/densité 2. La config révisée
# pour les nouveaux travaux est documentée dans README.md et la note de révision de docs/methode.md.
OPENTTD_CONFIG = """
[difficulty]
number_towns = 2
industry_density = 4

[economy]
inflation = false

[game_creation]
starting_year = 1950
map_x = 8
map_y = 8
"""

DAYS = 365 * 10  # duree de partie Phase 0 -- voir README.md
SEED = 42
N_VALUES = (1, 15)      # etape 3 (verification post-correctif) : N=5 saute, les deux extremes
                        # suffisent a confirmer l'effet -- voir docs/methode.md
OUTPUT_JSON = "docs/phase2_multiline_verify.json"  # etape 1 (controle pre-correctif) ecrivait
                        # docs/phase2_multiline_control.json avec N_VALUES=(1,5,15) -- change ici
                        # a la main pour la re-verification post-correctif (meme script, cf. plan)
NUM_TRAINS = 2
WAGONS_PER_TRAIN = 2
ENGINE_RANK = 1

STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE_COST_RE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")


def line_profit(chunks, owner):
    """Somme profit_last_year (annee complete) des vehicules de tete (unitnumber != 0) de LA
    compagnie `owner`, et l'age max moyen du materiel (annees) pour l'amortissement -- voir
    phase2_pair_rank_run.py. Ici owner varie par ligne (une compagnie par ligne, plusieurs
    compagnies par partie) au lieu d'etre toujours 0."""
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


def keep_signs_and_vehs(row):
    signs = row["chunks"].get("SIGN", {})
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "n_companies": len(row["experiment"]["ais"]),
        "signs": [(s["name"], s["owner"]) for s in signs.values()],
        "vehs": row["chunks"].get("VEHS", {}),
    },)


if __name__ == "__main__":
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=3,
        result_processor=keep_signs_and_vehs,
        ai_libraries=(
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
        experiments=tuple(
            {
                "seed": SEED,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": tuple(
                    local_folder(
                        "ai/TrainLineAI", "TrainLineAI",
                        ai_params=(
                            ("num_trains", NUM_TRAINS),
                            ("wagons_per_train", WAGONS_PER_TRAIN),
                            ("engine_rank", ENGINE_RANK),
                            ("pair_rank", i),
                            ("line_index", i),
                        ),
                    )
                    for i in range(n)
                ),
            }
            for n in N_VALUES
        ),
    )

    # Plusieurs savegames captures par experience (autosaves) -- garder le dernier par N (les
    # trois experiences partagent seed/config, seul n_companies les distingue ici).
    by_n = {}
    for r in results:
        n = r["n_companies"]
        prev = by_n.get(n)
        if prev is None or r["date"] > prev["date"]:
            by_n[n] = r

    all_records = {}  # n -> [rec, ...]
    for n in sorted(by_n):
        r = by_n[n]
        status_by_idx = {}
        detail_by_idx = {}
        vehcost_by_idx = {}
        owner_by_idx = {}
        for name, owner in r["signs"]:
            m = STATUS_RE.match(name)
            if m:
                idx = int(m.group(1))
                status_by_idx[idx] = m.groups()
                owner_by_idx[idx] = owner
                continue
            m = DETAIL_RE.match(name)
            if m:
                detail_by_idx[int(m.group(1))] = m.groups()
                continue
            m = VEHICLE_COST_RE.match(name)
            if m:
                vehcost_by_idx[int(m.group(1))] = int(m.group(2))

        records = []
        for idx in range(n):
            rec = {"line_index": idx, "seed": r["seed"], "n_companies": n}
            status = status_by_idx.get(idx)
            if status:
                rec.update({
                    "stage": status[1],
                    "reason": status[2],
                    "built": int(status[3]),
                    "requested": int(status[4]),
                })
            detail = detail_by_idx.get(idx)
            if detail:
                vehicle_cost = vehcost_by_idx.get(idx)
                rec.update({
                    "town_a": int(detail[1]),
                    "town_b": int(detail[2]),
                    "distance": int(detail[3]),
                    "cost": int(detail[4]),
                    "vehicle_cost": vehicle_cost,
                })
                owner = owner_by_idx.get(idx)
                veh = line_profit({"VEHS": r["vehs"]}, owner) if owner is not None else None
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
        all_records[n] = records

    for n in sorted(all_records):
        print(f"\n=== N={n} compagnies simultanees ===")
        for rec in all_records[n]:
            print(
                f"line={rec['line_index']:2d} -> {rec.get('stage','?'):8s} {rec.get('reason','?'):8s} "
                f"{rec.get('built','?')}/{rec.get('requested','?')}  "
                f"towns={rec.get('town_a','-')}-{rec.get('town_b','-')} "
                f"dist={rec.get('distance','-')} cost={rec.get('cost','-')} "
                f"profit_ligne={rec.get('profit_ligne','-')}"
            )

    print("\n=== pair_rank=0 / line_index=0 : profit_ligne selon N ===")
    for n in sorted(all_records):
        ref = all_records[n][0]
        print(f"N={n:2d} -> profit_ligne={ref.get('profit_ligne','-')} "
              f"(stage={ref.get('stage','?')}, towns={ref.get('town_a','-')}-{ref.get('town_b','-')})")

    with open(OUTPUT_JSON, "w") as f:
        json.dump(all_records, f, indent=2)
    print(f"\nEcrit dans {OUTPUT_JSON}")
