"""Source unique pour les parametres de TrainLineAI : genere info.nut ET construit les
ai_params Python depuis le meme dictionnaire. Un typo sur un nom de parametre, ou une valeur
hors bornes, devient une ValueError immediate cote Python au lieu d'etre avale silencieusement
par OpenTTD a l'execution (verifie empiriquement, voir docs/methode.md).
"""

META = {
    "class_name": "TrainLineAI",
    "author": "openttd-ml",
    "description": "Builds a single train line between two towns, chosen by population rank, in year 1, then idles.",
    "version": 1,
    "date": "2026-08-25",
    "short_name": "TRLN",
    "api_version": "13",
}

PARAMS = {
    "num_trains": {
        "min": 1, "max": 10, "default": 1,
        "description": "Number of trains to run on the line",
    },
    "wagons_per_train": {
        "min": 1, "max": 10, "default": 2,
        "description": "Number of wagons per train (excluding the engine)",
    },
    "town_a_rank": {
        "min": 0, "max": 15, "default": 0,
        "description": "Rank of town A in the population-sorted town list (0 = largest)",
    },
    "town_b_rank": {
        "min": 0, "max": 15, "default": 1,
        "description": "Rank of town B in the population-sorted town list (0 = largest)",
    },
    "pair_rank": {
        "min": 0, "max": 500, "default": 0,
        "description": "Rank of the town pair in the score-sorted (population_a*population_b/distance) list, 0 = best",
    },
    "engine_rank": {
        "min": 0, "max": 6, "default": 0,
        "description": "Rank of the engine in the speed-sorted engine list (0 = fastest)",
        "note": """Borne 6 et non 7 : mesuree sur les 50 graines de la campagne
        phase2_hurdle_dataset_v1 (2026-08-26). Le rang 7 sort de la plage reelle sur 6 graines
        (moins de 8 moteurs constructibles a cette date/carte) et produit alors ENGOOR, un echec
        de configuration qui pollue la classe negative du classifieur. Aucun ENGOOR observe au
        rang <= 6 sur ces 50 graines.""",
    },
    "line_index": {
        "min": 0, "max": 99, "default": 0,
        "description": "Identifier of this line/attempt, echoed in the status sign (does not schedule it)",
    },
    "stagger_slot": {
        "min": 0, "max": 99, "default": 0,
        "description": "Multi-company construction order slot; 0 disables stagger in isolated games",
    },
    "pathfinder_iterations_k": {
        "min": 1, "max": 300, "default": 30,
        "description": "A* search-iteration budget, in thousands (30 = historical 30000)",
        "note": """COUPLE A barrier_base_k : ne jamais relever l'un sans l'autre. Mesure du
        2026-08-27 : une iteration d'A* coute ~2700 opcodes pour un budget VM de ~10000 par tick,
        soit 3,7 iterations par tick. Les 30000 iterations par defaut consomment donc 7337 a 10519
        ticks, contre une barriere a 11000 -- on est a ~96 % de saturation. Relever ce budget seul
        ferait basculer barrier_flag a O et casserait en silence la comparabilite temporelle.""",
    },
    "barrier_base_k": {
        "min": 1, "max": 60, "default": 11,
        "description": "Base construction-barrier tick, in thousands (11 = historical 11000)",
        "note": """COUPLE A pathfinder_iterations_k -- voir sa note. Ordre de grandeur mesure :
        les 9 pires cas PATHLIM demandent 41200 a 89350 iterations et jusqu'a 27858 ticks de
        pathfinding, donc un budget de 90 exigerait une barriere vers 33.""",
    },
}


def render_info_nut(meta=META, params=PARAMS):
    lines = [f'class {meta["class_name"]}Info extends AIInfo {{']
    lines.append(f'  function GetAuthor()      {{ return "{meta["author"]}"; }}')
    lines.append(f'  function GetName()        {{ return "{meta["class_name"]}"; }}')
    lines.append(f'  function GetDescription() {{ return "{meta["description"]}"; }}')
    lines.append(f'  function GetVersion()     {{ return {meta["version"]}; }}')
    lines.append(f'  function GetDate()        {{ return "{meta["date"]}"; }}')
    lines.append(f'  function CreateInstance() {{ return "{meta["class_name"]}"; }}')
    lines.append(f'  function GetShortName()   {{ return "{meta["short_name"]}"; }}')
    lines.append(f'  function GetAPIVersion()  {{ return "{meta["api_version"]}"; }}')
    lines.append("")
    lines.append("  function GetSettings() {")
    for name, spec in params.items():
        lines.append("    AddSetting({")
        # `note` : justification mesuree d'une borne. Rendue en commentaire Squirrel pour qu'une
        # regeneration ne l'efface pas -- c'est arrive une fois, la borne engine_rank <= 6 ayant
        # perdu sa justification empirique parce qu'elle vivait dans info.nut et pas ici.
        if spec.get("note"):
            note = [l.strip() for l in spec["note"].strip().splitlines()]
            lines.append(f"      /* {note[0]}")
            for extra in note[1:]:
                lines.append(f"       * {extra}")
            lines.append("       */")
        lines.append(f'      name = "{name}",')
        lines.append(f'      description = "{spec["description"]}",')
        lines.append(f'      min_value = {spec["min"]}, max_value = {spec["max"]},')
        lines.append(f'      easy_value = {spec["default"]}, medium_value = {spec["default"]}, hard_value = {spec["default"]},')
        lines.append(f'      custom_value = {spec["default"]},')
        lines.append("      flags = 0")
        lines.append("    });")
    lines.append("  }")
    lines.append("}")
    lines.append(f'RegisterAI({meta["class_name"]}Info());')
    return "\n".join(lines) + "\n"


def make_ai_params(params=PARAMS, **values):
    unknown = set(values) - set(params)
    if unknown:
        raise ValueError(f"Parametre(s) inconnu(s) : {sorted(unknown)} -- declares : {sorted(params)}")
    result = []
    for name, spec in params.items():
        val = values.get(name, spec["default"])
        if not (spec["min"] <= val <= spec["max"]):
            raise ValueError(f"{name}={val} hors bornes [{spec['min']}, {spec['max']}]")
        result.append((name, val))
    return tuple(result)


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "..", "ai", "TrainLineAI", "info.nut")
    with open(out, "w") as f:
        f.write(render_info_nut())
    print(f"{out} regenere depuis src/trainlineai_schema.py")
