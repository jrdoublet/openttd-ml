"""Verifie si le chunk VEHS expose un profit par vehicule (profit_this_year/profit_last_year,
noms a confirmer) et si ORDR permet de retrouver la paire de gares d'une ligne -- AVANT d'engager
quoi que ce soit sur cette piste pour la cible ligne-level. old_economy (PLYR) est company-level,
non exploitable au niveau ligne (voir docs/methode.md).

Meme methode de verification que pour old_economy (sweeps/phase0_explore3.py) : inspection directe
du savegame parse par OpenTTDLab, pas de suppositions sur les noms de champs.
"""
import json
from openttdlab import run_experiments, bananas_ai_library, local_folder

SEED = 42
DAYS = 365 * 3  # assez pour qu'au moins un trimestre de profit vehicule s'accumule

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

if __name__ == "__main__":
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=1,
        ai_libraries=(
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
        experiments=(
            {
                "seed": SEED,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": (
                    local_folder(
                        "ai/TrainLineAI", "TrainLineAI",
                        ai_params=(
                            ("num_trains", 2),
                            ("wagons_per_train", 2),
                            ("town_a_rank", 0),
                            ("town_b_rank", 1),
                            ("engine_rank", 0),
                        ),
                    ),
                ),
            },
        ),
    )

    results_sorted = sorted(results, key=lambda r: r["date"])
    last = results_sorted[-1]
    chunks = last["chunks"]

    print("=== chunks presents ===")
    print(sorted(chunks.keys()))

    print("\n=== SIGN (pour retrouver la compagnie/owner) ===")
    print(json.dumps(chunks.get("SIGN"), indent=2)[:2000])

    print("\n=== VEHS : structure brute d'un vehicule (1er trouve) ===")
    vehs = chunks.get("VEHS")
    if vehs:
        first_key = next(iter(vehs))
        print("cle exemple:", first_key)
        print(json.dumps(vehs[first_key], indent=2))
        print("\nchamps contenant 'profit' sur tous les vehicules :")
        for k, v in vehs.items():
            profit_fields = {kk: vv for kk, vv in v.items() if "profit" in kk.lower()}
            if profit_fields:
                print(k, profit_fields)
    else:
        print("ABSENT")

    print("\n=== ORDR : structure brute (1er trouve) ===")
    ordr = chunks.get("ORDR")
    if ordr:
        first_key = next(iter(ordr))
        print("cle exemple:", first_key)
        print(json.dumps(ordr[first_key], indent=2)[:2000])
    else:
        print("ABSENT")

    print("\n=== STNN : structure brute (1er trouve) ===")
    stnn = chunks.get("STNN")
    if stnn:
        first_key = next(iter(stnn))
        print("cle exemple:", first_key)
        print(json.dumps(stnn[first_key], indent=2)[:2000])
    else:
        print("ABSENT")

    # Seulement les chunks pertinents pour cette verification -- les chunks carte (MAP*, RAIL,
    # ROAD, ...) pesent plusieurs centaines de Ko a eux seuls et n'apportent rien ici.
    relevant = {k: chunks[k] for k in ("SIGN", "VEHS", "ORDR", "STNN", "PLYR") if k in chunks}
    with open("docs/phase2_vehs_explore.json", "w") as f:
        json.dump(relevant, f, indent=2, default=str)
    print("\nDump (chunks pertinents seulement) ecrit dans docs/phase2_vehs_explore.json")
