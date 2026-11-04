"""Strict, idempotent removal of the RAIL-LOOP opt-in wiring (04/11/2026).

RAIL-LOOP is the newest layer: it is removed first, before every older OFF
projector, so that all historical fixtures keep their original hashes.
Only explicitly enumerated additive fragments are removed; a partial or
modified hunk fails the projection instead of silently changing history.
The module file ``rail_loop.nut`` itself is new and simply absent OFF.
"""

INSERTIONS = {
    "globals_pre.nut": (
        "/* RAIL-LOOP : voie 2 de retour par l'arriere des quais, boucle a sens unique, strict opt-in. */\n"
        "RAIL_LOOP <- false;\n",
    ),
    "settings.nut": (
        '  RAIL_LOOP = AIController.GetSetting("rail_loop") == 1;\n',
    ),
    "info.nut": (
        '    AddSetting({ name = "rail_loop",\n'
        '      description = "RAIL-LOOP: one-way return track through the back of both platforms, PBS loop and fleet growth (default 0)",\n'
        '      min_value = 0, max_value = 1,\n'
        '      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
        '      flags = AICONFIG_BOOLEAN });\n',
    ),
    "main.nut": (
        "  _railLoopState = null; // RAIL-LOOP : recherche/armement transitoire, hors slot _railSearch.\n",
        'require("rail_loop.nut");\n',
    ),
    "task_rail.nut": (
        "  if (RAIL_LOOP && OpexRailLoopSelect(this, year)) return;\n",
        '        if (RAIL_LOOP && ("railLoop" in line) && line.railLoop > 0) continue;\n',
    ),
    "scheduler.nut": (
        "  if (RAIL_LOOP && this._railLoopState != null) OpexRailLoopStep(this);\n",
    ),
}

# "RAIL_LOOP" seul est deja un tag historique de journal V181 (builder_rail.nut).
MARKERS = ("RAIL_LOOP <-", "RAIL_LOOP =", "RAIL_LOOP &&", '"rail_loop"', "rail_loop.nut",
           "_railLoopState", "OpexRailLoop")


def off_source(name, source):
    fragments = INSERTIONS.get(name)
    if fragments is None:
        if name != "rail_loop.nut" and any(m in source for m in MARKERS):
            raise AssertionError(f"RAIL-LOOP {name}: unrecognized source hunk")
        return source
    present = [fragment in source for fragment in fragments]
    if not any(present):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"RAIL-LOOP {name}: unrecognized source hunk")
        return source
    if not all(present) or any(source.count(f) != 1 for f in fragments):
        raise AssertionError(f"RAIL-LOOP {name}: unexpected insertion count")
    for fragment in fragments:
        source = source.replace(fragment, "", 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"RAIL-LOOP {name}: residual marker after projection")
    return source
