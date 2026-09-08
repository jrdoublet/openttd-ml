"""Banc de comparaison : notre IA contre les IA de reference, parties isolees.

Etape 0 du programme "faire mieux qu'AAAHogEx". Chaque IA joue SEULE sa propre partie, sur la
meme graine et la meme configuration : on mesure la qualite de jeu, pas l'interaction. Le face a
face dans une partie partagee viendra aux jalons, avec un autre script.

OpenTTD 15.3 obligatoire, et c'est la seule version possible :
  - AAAHogEx declare GetAPIVersion() = "14", donc il exige OpenTTD >= 14 ;
  - OpenTTDLab 0.0.75 (openttdlab.py:195-204) ne supporte que 12 <= major < 14 (mode autosave)
    et major >= 15 (mode console-script) -- la 14.x leve une exception.
Le binaire >= 15 exige libgomp1 et libglib2.0-0, ajoutes au Dockerfile.

Metrique : PLYR[0]["old_economy"][0] donne company_value et performance_history (le score
officiel 0-1000) de la DERNIERE ANNEE CLOTUREE. cur_economy a company_value = 0 : ne pas
l'utiliser. max_loan est parse en -9223372036854775808 a cette version : champ ininterpretable.
"""
import json
from pathlib import Path

from openttdlab import bananas_ai, bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
RESULT = ROOT / "results" / "bench_v1.json"

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
TRAINS_MD5 = "c4c069dc797674e545411b59867ad0c2"  # identique aux scripts phase0
YEARS = 10
SEEDS = (42, 100, 7, 999, 2026)
MAX_WORKERS = 3

# Configuration gelee du projet (voir docs/methode.md) : carte 256x256, depart 1970.
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


def opponents():
    """Les adversaires disponibles localement, du plus faible au plus fort.

    Les trois sont hors depot (.gitignore) : on les EXECUTE comme adversaires, on ne lit ni ne
    copie leur code dans notre IA.

    Deux reparations ont ete necessaires cote AdmiralAI, toutes deux dans notre copie locale :
      - `version.nut` manquait (fichier genere par son Makefile via `hg id`, donc jamais clone) ;
        sans lui `info.nut` ne compile pas et AUCUNE compagnie n'est creee -- l'echec est
        silencieux dans les chunks, il ne se voit que dans `row["output"]`.
      - il importe `queue.fibonacci_heap` version 2, or BaNaNaS ne publie plus que la 3 ;
        l'import a ete passe a 3 dans notre copie.
    """
    return {
        "trAIns": bananas_ai("54524149", "trAIns", ai_params=(), md5=TRAINS_MD5),
        "AdmiralAI": local_folder(str(ROOT / "ai" / "AdmiralAI"), "AdmiralAI", ()),
        "AAAHogEx": local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ()),
    }


def keep(row):
    """Une ligne par sauvegarde mensuelle : la serie temporelle, pas seulement le point final."""
    chunks = row["chunks"]
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    return ({
        "run": row["experiment"]["bench_run"],
        "date": str(row["date"]),
        "company_value": last_closed.get("company_value"),
        "performance_history": last_closed.get("performance_history"),
        "income_last_year": last_closed.get("income"),
        "expenses_last_year": last_closed.get("expenses"),
        "money": (player or {}).get("money"),
        "current_loan": (player or {}).get("current_loan"),
        "months_of_bankruptcy": (player or {}).get("months_of_bankruptcy"),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
    },)


def experiments():
    """Une partie par (IA, graine), plus une repetition de controle du non-determinisme.

    Deux executions strictement identiques d'AAAHogEx ont donne 194 gares puis 190 lors du
    sondage de faisabilite. La repetition ci-dessous tranche : si elle rend exactement les memes
    chiffres, le moteur est deterministe et un tirage suffit ; sinon le banc exige des moyennes.
    """
    runs = [(name, seed, 0) for name in opponents() for seed in SEEDS]
    runs += [("AAAHogEx", SEEDS[0], 1)]  # repetition de controle
    built = opponents()
    return [{
        "seed": seed,
        "days": 365 * YEARS,
        "openttd_config": CFG,
        "ais": (built[name],),
        "bench_run": [name, seed, repeat],
    } for name, seed, repeat in runs]


def summarise(rows):
    """Point final par partie : la derniere sauvegarde ayant une annee clôturee."""
    by_run = {}
    for row in rows:
        key = tuple(row["run"])
        by_run.setdefault(key, []).append(row)
    summary = []
    for key, series in sorted(by_run.items(), key=lambda item: str(item[0])):
        series.sort(key=lambda r: r["date"])
        final = series[-1]
        summary.append({
            "ai": key[0], "seed": key[1], "repeat": key[2],
            "last_date": final["date"],
            "company_value": final["company_value"],
            "performance_history": final["performance_history"],
            "income_last_year": final["income_last_year"],
            "money": final["money"], "current_loan": final["current_loan"],
            "n_vehicles": final["n_vehicles"], "n_stations": final["n_stations"],
            "months_of_bankruptcy": final["months_of_bankruptcy"],
            "n_savegames": len(series),
        })
    return summary


def main():
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=MAX_WORKERS, result_processor=keep, experiments=experiments(),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),),
    ))
    summary = summarise(rows)
    RESULT.write_text(json.dumps({
        "openttd_version": OPENTTD_VERSION, "opengfx_version": OPENGFX_VERSION,
        "years": YEARS, "seeds": list(SEEDS), "openttd_config": CFG,
        "metric": "PLYR[0].old_economy[0] : company_value et performance_history (0-1000)",
        "summary": summary, "series": rows,
    }, indent=1))
    for record in summary:
        print(f"{record['ai']:>10} seed={record['seed']:<5} rep={record['repeat']} "
              f"value={record['company_value']} rating={record['performance_history']} "
              f"veh={record['n_vehicles']} st={record['n_stations']}")
    print("ecrit", RESULT)


if __name__ == "__main__":
    main()
