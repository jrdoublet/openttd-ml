"""Verifie que ai_params atteint bien l'IA et change effectivement le resultat.

Meme graine, deux valeurs de maximum_buses (parametre de ParameterisedAI, voir
ai/ParameterisedAI/ — source figee sur le commit 74662403e0764329112dc78e5b279d7f1b5fd510
de https://github.com/michalc/ParameterisedAI). Carte/graine identiques dans les deux runs :
toute difference de resultat vient forcement du parametre, pas du hasard.
"""
import json
from openttdlab import run_experiments, bananas_ai_library, local_folder

SEED = 42
DAYS = 365 * 2 + 1  # 2 ans : assez pour que la route de bus tourne et separe les deux cas
MAX_BUSES_VALUES = (1, 8)

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


def keep_money_and_params(row):
    return ({
        "maximum_buses": row["experiment"]["ais"][0][1][0][1],
        "ai_params_raw": row["experiment"]["ais"][0][1],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "money": row["chunks"]["PLYR"]["0"]["money"],
    },)


if __name__ == "__main__":
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=2,
        result_processor=keep_money_and_params,
        ai_libraries=(
            bananas_ai_library("5046524f", "Pathfinder.Road"),
        ),
        experiments=(
            {
                "seed": SEED,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": (
                    local_folder(
                        "ai/ParameterisedAI", "ParameterisedAI",
                        ai_params=(("maximum_buses", maximum_buses),),
                    ),
                ),
            }
            for maximum_buses in MAX_BUSES_VALUES
        ),
    )

    by_param = {}
    for r in results:
        by_param.setdefault(r["maximum_buses"], []).append(r)

    print("=== Le parametre arrive-t-il jusqu'a l'experiment ? ===")
    for v, rows in sorted(by_param.items()):
        print(f"maximum_buses={v} : {len(rows)} savegames, ai_params brut = {rows[0]['ai_params_raw']}")

    print("\n=== Trajectoire money par valeur de maximum_buses (meme graine) ===")
    finals = {}
    for v in sorted(by_param):
        rows = sorted(by_param[v], key=lambda r: r["date"])
        finals[v] = rows[-1]["money"]
        print(f"maximum_buses={v}:")
        for r in rows:
            print(f"  {r['date']}  money={r['money']}")

    v1, v2 = sorted(by_param)
    print(f"\n=== Verdict ===")
    print(f"money final maximum_buses={v1}: {finals[v1]}")
    print(f"money final maximum_buses={v2}: {finals[v2]}")
    if finals[v1] != finals[v2]:
        print("-> DIFFERENT : le parametre change bien le resultat (meme graine, seule variable = maximum_buses).")
    else:
        print("-> IDENTIQUE : suspect, le parametre ne semble pas avoir eu d'effet.")

    with open("results/phase0_parameterised_ai_check.json", "w") as f:
        json.dump({
            str(v): [dict(r) for r in sorted(by_param[v], key=lambda r: r["date"])]
            for v in by_param
        }, f, indent=2)
