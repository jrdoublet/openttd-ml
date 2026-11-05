"""Fail-closed byte-exact OFF projection for V257 uncensored demand."""

INSERTIONS = {
    "globals_pre.nut": ("V257_DEMAND <- false;\n",),
    "settings.nut": ('  V257_DEMAND = AIController.GetSetting("v257_demand") == 1;\n',),
    "info.nut": (
        '    AddSetting({ name = "v257_demand",\n'
        '      description = "V257 demand: forecast freight demand from industry production and station rating, prefer capacity at equal net income (default 1 since 2026-11-05, user decision)",\n'
        '      min_value = 0, max_value = 1,\n'
        '      easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,\n'
        '      flags = AICONFIG_BOOLEAN });\n',
    ),
    "task_v257.nut": (
        '/* V257 demande non censuree : l\'industrie est la source du flux, non la\n'
        ' * quantite que l\'ancienne petite rame a effectivement livree. Une rame a\n'
        ' * quai donne une perspective de ramassage d\'au moins 75 %, sans promettre\n'
        ' * davantage que la production mensuelle reelle. Meme division par le nombre\n'
        ' * de rames que le modele observe, pour ne pas multiplier la production. */\n'
        'function OpexV257UncensoredMonthly(line, vehicles, rating, fallback)\n'
        '{\n'
        '  if (line.kind != "freight" || vehicles == null || vehicles.len() == 0) return fallback;\n'
        '  local industry = -1;\n'
        '  if ("srcIndustry" in line) industry = line.srcIndustry;\n'
        '  else if ("originA" in line) industry = AIIndustry.GetIndustryID(line.originA);\n'
        '  if (!AIIndustry.IsValidIndustry(industry)) return fallback;\n'
        '  local production = AIIndustry.GetLastMonthProduction(industry, line.cargo);\n'
        '  if (production <= 0) return fallback;\n'
        '  local predictedRating = rating;\n'
        '  local sourceStation = AIStation.GetStationID(line.stationA);\n'
        '  if (AIStation.IsValidStation(sourceStation)) {\n'
        '    foreach (vehicle in vehicles) {\n'
        '      if (!AIVehicle.IsValidVehicle(vehicle)) continue;\n'
        '      if (AIVehicle.IsStoppedInDepot(vehicle)) continue;\n'
        '      if (AIStation.GetStationID(AIVehicle.GetLocation(vehicle)) == sourceStation) {\n'
        '        if (predictedRating < 75) predictedRating = 75;\n'
        '        break;\n'
        '      }\n'
        '    }\n'
        '  }\n'
        '  if (predictedRating < 0) return fallback;\n'
        '  if (predictedRating > 100) predictedRating = 100;\n'
        '  return production.tofloat() * predictedRating / (100.0 * vehicles.len());\n'
        '}\n\n',
        '  if (V257_DEMAND) monthly = OpexV257UncensoredMonthly(line, line.vehicles, rating, monthly);\n',
        '    if (V257_DEMAND) monthly = OpexV257UncensoredMonthly(line, line.vehicles, rating, monthly);\n',
    ),
}

REPLACED = {
    "task_v257.nut": ((
        '        if (best == null || plan.revenue - plan.running > best.revenue - best.running\n'
        '            || (plan.revenue - plan.running == best.revenue - best.running\n'
        '                && (V257_DEMAND ? (number * wagon.capacity > best.wagons * best.wagon.capacity\n'
        '                    || (number * wagon.capacity == best.wagons * best.wagon.capacity && plan.price < best.price))\n'
        '                    : plan.price < best.price))) best = plan;\n',
        '        if (best == null || plan.revenue - plan.running > best.revenue - best.running\n'
        '            || (plan.revenue - plan.running == best.revenue - best.running && plan.price < best.price)) best = plan;\n',
    ),),
}

def off_source(name, source):
    from fleet_arb_off import off_source as fleet_off
    source = fleet_off(name, source)
    fragments = list(INSERTIONS.get(name, ()))
    replacements = REPLACED.get(name, ())
    if not fragments and not replacements:
        return source
    if "V257_DEMAND" not in source and '"v257_demand"' not in source and "OpexV257UncensoredMonthly" not in source:
        return source
    counts = {}
    for fragment in fragments:
        counts[fragment] = counts.get(fragment, 0) + 1
    for fragment, expected in counts.items():
        if source.count("\n" + fragment) != expected:
            raise AssertionError(f"V257 demand {name}: missing or duplicated insertion")
    for new, _ in replacements:
        if source.count(new) != 1:
            raise AssertionError(f"V257 demand {name}: unexpected replacement")
    for fragment in sorted(fragments, key=len, reverse=True):
        source = source.replace(fragment, "", 1)
    for new, old in replacements:
        source = source.replace(new, old, 1)
    if any(tag in source for tag in ("V257_DEMAND", '"v257_demand"', "OpexV257UncensoredMonthly")):
        raise AssertionError(f"V257 demand {name}: residual opt-in")
    return source
