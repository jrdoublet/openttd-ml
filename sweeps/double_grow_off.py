"""Strict, idempotent removal of DOUBLE-GROW opt-in wiring for frozen OFF checks.

Only explicitly enumerated additive fragments are removed. Unexpected partial
changes fail the projection instead of silently changing historical fixtures.
"""

INSERTIONS = {
    "globals_pre.nut": (
        "/* DOUBLE-GROW : doublement differe des lignes fret rentables, strict opt-in. */\n"
        "DOUBLE_GROW <- false;\n"
        "DOUBLE_GROW_V2 <- false;\n",
    ),
    "settings.nut": (
        '  DOUBLE_GROW = AIController.GetSetting("double_grow") == 1;\n'
        '  DOUBLE_GROW_V2 = AIController.GetSetting("double_grow") == 2;\n',
    ),
    "info.nut": (
        '    AddSetting({ name = "double_grow",\n'
        '      description = "DOUBLE-GROW: 1=parallel experiment, 2=deferred V190 retrofit and fleet growth (default 0)",\n'
        '      min_value = 0, max_value = 2,\n'
        '      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
        '      flags = 0 });\n',
    ),
    "main.nut": (
        '  _doubleGrowV2State = null; // Recherche secondaire A* opt-in, transitoire et preemptable.\n',
        'require("double_grow_geometry.nut");\n'
        'require("double_grow_fleet.nut");\n'
        'require("double_grow.nut");\n'
        'require("double_grow_v2_build.nut");\n'
        'require("double_grow_v2.nut");\n',
    ),
    "task_rail.nut": (
        '  if (DOUBLE_GROW && OpexDoubleGrowSelect(this, year)) return;\n'
        '  if (DOUBLE_GROW_V2 && OpexDoubleGrowV2Select(this, year)) return;\n',
    ),
}


def off_source(name, source):
    from fleet_arb_off import off_source as fleet_off
    source = fleet_off(name, source)
    from invest_stall_platform_off import off_source as platform_off
    source = platform_off(name, source)
    fragments = INSERTIONS.get(name)
    if fragments is None:
        return source
    present = [fragment in source for fragment in fragments]
    if not any(present):
        if "DOUBLE_GROW" in source or '"double_grow"' in source:
            raise AssertionError(f"DOUBLE-GROW {name}: unrecognized source hunk")
        return source
    if not all(present) or any(source.count(f) != 1 for f in fragments):
        raise AssertionError(f"DOUBLE-GROW {name}: unexpected insertion count")
    for fragment in fragments:
        source = source.replace(fragment, "", 1)
    return source
