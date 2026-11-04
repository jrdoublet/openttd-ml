"""Strict, idempotent removal of the RAIL-FILL opt-in wiring (04/11/2026).

RAIL-FILL is newer than RAIL-LOOP: it is removed first. Only enumerated
fragments are touched; a partial or modified hunk fails the projection.
The module file ``rail_fill.nut`` itself is new and simply absent OFF.
"""

INSERTIONS = {
    "globals_pre.nut": (
        "/* RAIL-FILL : V284 remplit les quais existants des 250 k£ de caisse, strict opt-in. */\n"
        "RAIL_FILL <- false;\n",
    ),
    "settings.nut": (
        '  RAIL_FILL = AIController.GetSetting("rail_fill") == 1;\n',
    ),
    "info.nut": (
        '    AddSetting({ name = "rail_fill",\n'
        '      description = "RAIL-FILL: V284 fills existing freight platforms from 250k cash, sized on real production, protected from V257 (default 0)",\n'
        '      min_value = 0, max_value = 1,\n'
        '      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
        '      flags = AICONFIG_BOOLEAN });\n',
    ),
    "main.nut": ('require("rail_fill.nut");\n',),
    "task_v257.nut": ('  if (RAIL_FILL && ("railFill" in line) && line.railFill) return;\n',),
    "task_v284.nut": (
        "    if (RAIL_FILL && atLimit && !v233Input && !OpexRailFillAddAllowed()) continue;\n",
        "  local railFillPlan = (RAIL_FILL && !best.add && !v233Input && (ESTIM_UNIFIE & 4) == 0)\n"
        "      ? OpexRailFillPlan(line, best.vehicle, best.wagon, best.number,\n"
        "          OpexRailNominalMaxWagons(OpexV284Limit(line))) : null;\n"
        "  if (railFillPlan != null) { number = railFillPlan.number; equipment = railFillPlan.equipment; }\n",
        "  if (railFillPlan != null) state.pending.railFill <- true;\n",
        '  if (RAIL_FILL && ("railFill" in pending) && pending.railFill) line.rawset("railFill", true);\n',
    ),
}

REPLACED = {
    "task_v284.nut": ((
        "  if (!v233Input && RAIL_FILL) {\n"
        "    if (OpexRailFillGateClosed(year)) return false;\n"
        "  } else if (!v233Input && (year < OPEX_START_YEAR + V284_RAIL_GROWTH || OpexAvailableCapital() < 1000000)) return false;\n",
        "  if (!v233Input && (year < OPEX_START_YEAR + V284_RAIL_GROWTH || OpexAvailableCapital() < 1000000)) return false;\n",
    ),),
}

MARKERS = ("RAIL_FILL", '"rail_fill"', "rail_fill.nut", "OpexRailFill", "railFill")


def off_source(name, source):
    fragments = INSERTIONS.get(name, ())
    replaced = REPLACED.get(name, ())
    if not fragments and not replaced:
        if name != "rail_fill.nut" and any(m in source for m in MARKERS):
            raise AssertionError(f"RAIL-FILL {name}: unrecognized source hunk")
        return source
    counts = [source.count(f) for f in fragments] + [source.count(new) for new, _ in replaced]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"RAIL-FILL {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"RAIL-FILL {name}: unexpected insertion count")
    for fragment in fragments:
        source = source.replace(fragment, "", 1)
    for new, old in replaced:
        source = source.replace(new, old, 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"RAIL-FILL {name}: residual marker after projection")
    return source
