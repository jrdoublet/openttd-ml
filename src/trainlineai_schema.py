"""Source unique pour les parametres de TrainLineAI : genere info.nut ET construit les
ai_params Python depuis le meme dictionnaire. Un typo sur un nom de parametre, ou une valeur
hors bornes, devient une ValueError immediate cote Python au lieu d'etre avale silencieusement
par OpenTTD a l'execution (verifie empiriquement, voir docs/methode.md).
"""

META = {
    "class_name": "TrainLineAI",
    "author": "openttd-ml",
    "description": "Builds a single train line between the two largest towns in year 1, then idles.",
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
