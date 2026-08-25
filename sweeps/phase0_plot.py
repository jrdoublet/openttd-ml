import pandas as pd
import plotly.express as px
from openttdlab import run_experiments, bananas_ai

DAYS = 365 * 10  # révisé après phase0_vps.json #1 : plus rapide que prévu
TRAINS_MD5 = "c4c069dc797674e545411b59867ad0c2"  # ai/54524149, trAIns 2.1, GPL v2 — figé pour reproductibilité
SEEDS = range(300, 310)  # 10 graines

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


def closed_quarter_start(d):
    """Date de début du trimestre le plus récemment clos, déduite de la date du savegame
    (old_economy[0] gèle jusqu'à la clôture du trimestre suivant)."""
    quarter_start_month = (d.month - 1) // 3 * 3 + 1
    if quarter_start_month == 1:
        return d.year - 1, 10
    return d.year, quarter_start_month - 3


def keep_company_value(row):
    """Un point par trimestre clos, dédupliqué sur la date calendaire réelle — pas sur
    len(old_economy), qui plafonne à 24 (fenêtre glissante de 6 ans) et perdrait silencieusement
    tout trimestre au-delà sur une partie de 10 ans. company_value est net de l'emprunt,
    contrairement à money."""
    old = row["chunks"]["PLYR"]["0"]["old_economy"]
    if not old:
        return ()
    year, month = closed_quarter_start(row["date"])
    return ({
        "seed": row["experiment"]["seed"],
        "quarter_year": year,
        "quarter_month": month,
        "company_value": old[0]["company_value"],
    },)


if __name__ == "__main__":
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=3,  # point d'inflexion mesuré en phase0_timing.py sur ce VPS
        result_processor=keep_company_value,
        experiments=(
            {
                "seed": seed,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": (bananas_ai("54524149", "trAIns", ai_params=(), md5=TRAINS_MD5),),
            }
            for seed in SEEDS
        ),
    )

    df = pd.DataFrame(results)
    # Plusieurs savegames mensuels partagent le même trimestre clos (old_economy[0] gèle entre
    # deux clôtures) : on déduplique sur (seed, trimestre calendaire) avant de tracer.
    df = df.drop_duplicates(subset=["seed", "quarter_year", "quarter_month"])
    df["date"] = pd.to_datetime({"year": df["quarter_year"], "month": df["quarter_month"], "day": 1})
    df["seed"] = df["seed"].astype(str)
    df = df.sort_values(["seed", "date"])
    df.to_csv("docs/phase0_company_value_vs_date.csv", index=False)

    fig = px.line(
        df,
        x="date", y="company_value", color="seed",
        title="Company value over time — 10 graines, trAIns, 10 ans de jeu (OpenTTD 13.4)",
    )
    fig.write_html("docs/phase0_company_value_vs_date.html")
    print(df.groupby("seed").size())
