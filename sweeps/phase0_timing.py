import json, os, platform, time
from openttdlab import run_experiments, bananas_ai

MACHINE = os.environ.get("MACHINE", "unknown")
DAYS = 365 * 10  # révisé après phase0_vps.json #1 : plus rapide que prévu
TRAINS_MD5 = "c4c069dc797674e545411b59867ad0c2"  # ai/54524149, trAIns 2.1, GPL v2 — figé pour reproductibilité

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
        "runs": {},
    }

    for workers in (1, 2, 3, 4, 6):
        if workers > (os.cpu_count() or 1):
            continue
        elapsed, results = timed(range(100, 100 + workers), workers)
        report["runs"][workers] = {
            "wallclock_s": round(elapsed, 1),
            "s_per_game": round(elapsed / workers, 1),
            "rows": len(results),
        }
        print(workers, report["runs"][workers])

    with open(f"docs/phase0_{MACHINE}.json", "w") as f:
        json.dump(report, f, indent=2)
