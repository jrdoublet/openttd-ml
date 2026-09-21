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
            "days": 365 * 10,
            "ais": (bananas_ai("54524149", "trAIns", ai_params=(), md5=TRAINS_MD5),),
        },
    ),
)

print(json.dumps(results[0]["chunks"]["PLYR"]["0"], indent=2, default=str)[:3000])
