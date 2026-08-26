"""Diagnostic de population des villes OpenTTD 13.4.

CITY ne serialize pas le champ de population dans les savegames 13.4 (verifie sur un vrai
savegame). Une IA-sonde ephemere ecrit donc des panneaux POPD au debut et a la fin de chaque
partie. Ces panneaux sont lus dans SIGN, canal deja valide dans ce depot, sans construire de
transport ni modifier l'economie des villes.
"""
import atexit
from datetime import date, timedelta
import json
import os
import re
import shutil
import statistics

from openttdlab import local_folder, run_experiments


DAYS = 365 * 10
FINAL_PROBE_TICK = 66500  # calibre via debug_ai.py : quelques semaines avant le stop de 10 ans.
SEEDS = (1, 2, 3, 4, 5, 6, 7, 42)
SOURCE_AI_DIR = "ai/TrainLineAI"
SCRATCH_AI_DIR = "/tmp/openttd-ml-town-population-probe"
PROBE_AI_NAME = "TownPopulationProbe"
OUTPUT_JSON = "docs/phase0_town_distribution.json"

# Confirme par une sonde du openttd.cfg reellement genere puis relu par le binaire 13.4 : 0..4
# sont conserves, 5 et 6 sont clamped a 4. La valeur 4 est le mode custom et lit
# game_creation.custom_town_number (defaut genere 1, donc PAS une densite tres elevee). Les valeurs
# custom 1, 50, 75, 100, 255 et 256 sont elles aussi preservees. Le meme cfg genere contient
# [economy] town_growth_rate = 2. Les configs laissent ce defaut historique intact pendant le
# diagnostic ; la decision Phase 0 ne sera revisee qu'apres lecture des resultats.
NUMBER_TOWNS_VALID_VALUES = (0, 1, 2, 3, 4)
GENERATED_TOWN_GROWTH_RATE_DEFAULT = 2

CONFIGS = (
    ("baseline_d2_y1950", 2, 1950, None),
    ("density_d3_y1950", 3, 1950, None),
    ("custom_d4_n75_y1950", 4, 1950, 75),
    ("later_d2_y1970", 2, 1970, None),
    ("later_d2_y1990", 2, 1990, None),
    ("candidate_d3_y1970", 3, 1970, None),
)

POP_RE = re.compile(r"^POPD\|([EF])\|(\d+)\|(\d+)(?:\|(\d+))?$")


def openttd_config(number_towns, starting_year, custom_town_number):
    custom = "" if custom_town_number is None else f"custom_town_number = {custom_town_number}\n"
    return f"""
[difficulty]
number_towns = {number_towns}
industry_density = 4

[economy]
inflation = false

[game_creation]
starting_year = {starting_year}
map_x = 8
map_y = 8
{custom}"""


def make_probe_ai():
    """Creer dans /tmp une IA qui publie les populations via SIGN, puis se nettoie a la sortie."""
    if os.path.exists(SCRATCH_AI_DIR):
        raise RuntimeError(f"Sonde temporaire deja presente : {SCRATCH_AI_DIR}")
    os.makedirs(SCRATCH_AI_DIR)
    with open(os.path.join(SCRATCH_AI_DIR, "info.nut"), "w") as output:
        output.write(f'''class {PROBE_AI_NAME}Info extends AIInfo {{
  function GetAuthor()      {{ return "openttd-ml"; }}
  function GetName()        {{ return "{PROBE_AI_NAME}"; }}
  function GetDescription() {{ return "Temporary town-population measurement probe"; }}
  function GetVersion()     {{ return 1; }}
  function GetDate()        {{ return "2026-08-26"; }}
  function CreateInstance() {{ return "{PROBE_AI_NAME}"; }}
  function GetShortName()   {{ return "TPRB"; }}
  function GetAPIVersion()  {{ return "13"; }}
}}
RegisterAI({PROBE_AI_NAME}Info());
''')
    with open(os.path.join(SCRATCH_AI_DIR, "main.nut"), "w") as output:
        output.write(f'''class {PROBE_AI_NAME} extends AIController {{}}

function {PROBE_AI_NAME}::_report(phase)
{{
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  foreach (town, population in towns) {{
    /* POPD|phase|raw_town_id|population[|date] -- under AISign's 31-char limit. */
    local location = AITown.GetLocation(town);
    /* One sign per tile: keep the final snapshot adjacent to the early one. */
    if (phase == "F") location = location + 1;
    local name = "POPD|" + phase + "|" + town + "|" + population;
    if (phase == "F") name += "|" + AIDate.GetCurrentDate();
    AISign.BuildSign(location, name);
  }}
}}

function {PROBE_AI_NAME}::Start()
{{
  this._report("E");
  /* AIController ticks are empirically slower than -vnull ticks; 66500 is near the 10-year stop. */
  local finalTick = {FINAL_PROBE_TICK};
  while (AIController.GetTick() < finalTick) {{
    local remaining = finalTick - AIController.GetTick();
    this.Sleep(remaining > 100 ? 100 : 1);
  }}
  this._report("F");
  while (true) this.Sleep(1000);
}}
''')


def populations_from_signs(signs):
    snapshots = {"E": {}, "F": {}, "final_probe_raw_dates": set()}
    for sign in signs.values():
        match = POP_RE.match(sign["name"])
        if match:
            phase, town_id, population, raw_date = match.groups()
            snapshots[phase][int(town_id)] = int(population)
            if phase == "F" and raw_date is not None:
                snapshots["final_probe_raw_dates"].add(int(raw_date))
    return snapshots


def openttd_date_to_iso(raw_date):
    """Meme convention que _run_experiment d'OpenTTDLab (jour 0 precede l'an 1 de 366 jours)."""
    return str(date(1, 1, 1) + timedelta(days=raw_date - 366))


def keep_population_signs(row):
    return ({
        "config_name": row["experiment"]["config_name"],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "populations": populations_from_signs(row["chunks"].get("SIGN", {})),
    },)


def summary(values):
    if not values:
        return None
    bins = ((0, 249), (250, 499), (500, 999), (1000, 1999), (2000, 4999), (5000, None))
    histogram = {}
    for low, high in bins:
        label = f"{low}+" if high is None else f"{low}-{high}"
        histogram[label] = sum(low <= value and (high is None or value <= high) for value in values)
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "mean": round(statistics.mean(values), 2),
        "histogram": histogram,
    }


if __name__ == "__main__":
    make_probe_ai()
    atexit.register(shutil.rmtree, SCRATCH_AI_DIR, ignore_errors=True)

    config_by_name = {name: {"number_towns": towns, "starting_year": year,
                             "custom_town_number": custom}
                      for name, towns, year, custom in CONFIGS}
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=3,
        result_processor=keep_population_signs,
        experiments=tuple(
            {
                "config_name": config_name,
                "seed": seed,
                "days": DAYS,
                "openttd_config": openttd_config(number_towns, starting_year, custom_town_number),
                "ais": (local_folder(SCRATCH_AI_DIR, PROBE_AI_NAME),),
            }
            for config_name, number_towns, starting_year, custom_town_number in CONFIGS
            for seed in SEEDS
        ),
    )

    # Chaque experience peut avoir plusieurs autosaves mensuels : ne retenir que le dernier,
    # qui doit contenir les deux jeux de panneaux E/F de la sonde.
    latest = {}
    for result in results:
        key = (result["config_name"], result["seed"])
        previous = latest.get(key)
        if previous is None or result["date"] > previous["date"]:
            latest[key] = result
    expected = {(name, seed) for name, _, _, _ in CONFIGS for seed in SEEDS}
    if set(latest) != expected:
        raise RuntimeError(f"Experiences manquantes : attendu {len(expected)}, obtenu {len(latest)}")

    records = []
    summaries = {}
    for config_name, _, _, _ in CONFIGS:
        early_values = []
        final_values = []
        growth_values = []
        town_counts = []
        for seed in SEEDS:
            result = latest[(config_name, seed)]
            early = result["populations"]["E"]
            final = result["populations"]["F"]
            raw_dates = result["populations"]["final_probe_raw_dates"]
            if not early or not final or set(early) != set(final) or not raw_dates:
                raise RuntimeError(f"Panneaux population incomplets pour {config_name}, seed={seed}: "
                                   f"E={len(early)}, F={len(final)}, dates={sorted(raw_dates)}")
            growth = {town_id: final[town_id] - early[town_id] for town_id in early}
            records.append({
                "config_name": config_name,
                "seed": seed,
                "capture_date": result["date"],
                "final_probe_date_range": [openttd_date_to_iso(raw_date) for raw_date in sorted(raw_dates)],
                "early_populations": early,
                "final_populations": final,
                "growth_by_town": growth,
            })
            early_values.extend(early.values())
            final_values.extend(final.values())
            growth_values.extend(growth.values())
            town_counts.append(len(early))
        summaries[config_name] = {
            "config": config_by_name[config_name],
            "town_count_per_seed": summary(town_counts),
            "early_population": summary(early_values),
            "final_population": summary(final_values),
            "growth_over_10_years_per_town": summary(growth_values),
        }

    print("Population towns: min / median / max; histogram bins are population counts")
    for config_name, _, _, _ in CONFIGS:
        report = summaries[config_name]
        early = report["early_population"]
        final = report["final_population"]
        growth = report["growth_over_10_years_per_town"]
        print(f"{config_name:24s} towns/seed med={report['town_count_per_seed']['median']:4g} | "
              f"early {early['min']:4g}/{early['median']:5g}/{early['max']:5g} "
              f"hist={early['histogram']} | final {final['min']:4g}/{final['median']:5g}/{final['max']:5g} "
              f"| growth med={growth['median']:5g}, range={growth['min']:g}..{growth['max']:g}")

    payload = {
        "openttd_13_4_settings_verification": {
            "number_towns_valid_values": list(NUMBER_TOWNS_VALID_VALUES),
            "number_towns_values_5_and_6_clamped_to": 4,
            "number_towns_value_4_mode": "custom_town_number",
            "custom_town_number_values_verified_persisted": [1, 50, 75, 100, 255, 256],
            "generated_town_growth_rate_setting": "town_growth_rate",
            "generated_town_growth_rate_default": GENERATED_TOWN_GROWTH_RATE_DEFAULT,
        },
        "city_chunk_population_field_available": False,
        "city_chunk_note": "CITY parsed records were inspected on a real 13.4 savegame; no population field was present.",
        "days": DAYS,
        "seeds": list(SEEDS),
        "configs": config_by_name,
        "summaries": summaries,
        "records": records,
    }
    with open(OUTPUT_JSON, "w") as output:
        json.dump(payload, output, indent=2)
    print(f"\nEcrit dans {OUTPUT_JSON}")
