import os
import pandas as pd
import plotly.express as px
from openttdlab import run_experiments, bananas_ai

DAYS = 365 * 4 + 1
TRAINS_MD5 = "c4c069dc797674e545411b59867ad0c2"  # ai/54524149, trAIns 2.1, GPL v2 — figé pour reproductibilité
SEEDS = range(300, 310)  # 10 graines


def keep_money_series(row):
    """Un point par savegame mensuel : construit la trajectoire money x date."""
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "money": row["chunks"]["PLYR"]["0"]["money"],
    },)


if __name__ == "__main__":
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=3,  # point d'inflexion mesuré en phase0_timing.py sur ce VPS
        result_processor=keep_money_series,
        experiments=(
            {
                "seed": seed,
                "days": DAYS,
                "ais": (bananas_ai("54524149", "trAIns", ai_params=(), md5=TRAINS_MD5),),
            }
            for seed in SEEDS
        ),
    )

    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["date"])
    df["seed"] = df["seed"].astype(str)
    df.to_csv("docs/phase0_money_vs_date.csv", index=False)

    fig = px.line(
        df.sort_values("date"),
        x="date", y="money", color="seed",
        title="Money over time — 10 graines, trAIns, 4 ans de jeu (OpenTTD 13.4)",
    )
    fig.write_html("docs/phase0_money_vs_date.html")
    print(df.groupby("seed").size())
