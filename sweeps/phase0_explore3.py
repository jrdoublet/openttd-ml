import json
from openttdlab import run_experiments, bananas_ai

TRAINS_MD5 = "c4c069dc797674e545411b59867ad0c2"

results = run_experiments(
    openttd_version="13.4",
    opengfx_version="7.1",
    max_workers=1,
    experiments=(
        {
            "seed": 300,
            "days": 365 * 2,
            "ais": (bananas_ai("54524149", "trAIns", ai_params=(), md5=TRAINS_MD5),),
        },
    ),
)

results_sorted = sorted(results, key=lambda r: r["date"])

def compact(e):
    return {k: e[k] for k in ("income", "expenses", "company_value", "performance_history")}

for r in results_sorted:
    plyr = r["chunks"]["PLYR"]["0"]
    old = plyr["old_economy"]
    print(r["date"], "cur=", compact(plyr["cur_economy"][0]), "len(old)=", len(old))

print("\n=== old_economy complet a la derniere sauvegarde ===")
last = results_sorted[-1]
for i, e in enumerate(last["chunks"]["PLYR"]["0"]["old_economy"]):
    print(i, compact(e))
