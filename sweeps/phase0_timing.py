import json, os, platform, time
from openttdlab import run_experiments, bananas_ai

MACHINE = os.environ.get("MACHINE", "unknown")
DAYS = 365 * 10  # révisé après phase0_vps.json #1 : plus rapide que prévu
TRAINS_MD5 = "c4c069dc797674e545411b59867ad0c2"  # ai/54524149, trAIns 2.1, GPL v2 — figé pour reproductibilité
BATCH_SEEDS = list(range(1000, 1024))  # 24 graines fixes : même batch à chaque niveau de worker, pour mesurer le vrai coût marginal du parallélisme (et pas juste "plus de workers = plus de parties lancées")

# Figé pour que rien ne bouge sous nos pieds entre deux versions/exécutions.
# Vérifié dans le vrai openttd.cfg généré par le binaire (13.4), pas recopié de mémoire :
# inflation était déjà à false par défaut sur cette build, mais on le fixe explicitement quand même.
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


def keep_last_only(row):
    """Ne conserve que le strict minimum : protège la RAM du VPS."""
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "money": row["chunks"]["PLYR"]["0"]["money"],
    },)


def timed(seeds, max_workers):
    t0 = time.monotonic()
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=max_workers,
        result_processor=keep_last_only,
        experiments=(
            {
                "seed": seed,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": (bananas_ai("54524149", "trAIns", ai_params=(), md5=TRAINS_MD5),),
            }
            for seed in seeds
        ),
    )
    return time.monotonic() - t0, results


if __name__ == "__main__":
    # 1er appel : télécharge OpenTTD/OpenGFX/trAIns. Non chronométrable.
    print("warmup...")
    timed([9999], 1)

    report = {
        "machine": MACHINE,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "batch_size": len(BATCH_SEEDS),
        "runs": {},
    }

    for workers in (1, 2, 3, 4, 6):
        if workers > (os.cpu_count() or 1):
            continue
        # Même batch de 24 graines à chaque niveau de worker : coût marginal réel, pas un artefact
        # de "on lance autant de parties que de workers".
        elapsed, results = timed(BATCH_SEEDS, workers)
        report["runs"][workers] = {
            "wallclock_s": round(elapsed, 1),
            "s_per_game": round(elapsed / len(BATCH_SEEDS), 1),
            "rows": len(results),
        }
        print(workers, report["runs"][workers])

    with open(f"docs/phase0_{MACHINE}.json", "w") as f:
        json.dump(report, f, indent=2)
