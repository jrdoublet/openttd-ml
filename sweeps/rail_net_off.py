"""Strict, idempotent removal of the RAIL-NET opt-in wiring (04/11/2026).

Newest layer: removed before RAIL-KEEP, RAIL-FILL and RAIL-LOOP. Every hunk is
a pure insertion; the module rail_net.nut itself is new and has no OFF form.
"""

INSERTIONS = {
    "globals_pre.nut": (
        "/* RAIL-NET : greffe d'une source fret sur une boucle RAIL-LOOP certifiee, strict opt-in. */\n"
        "RAIL_NET <- false;\n",
    ),
    "settings.nut": ('  RAIL_NET = AIController.GetSetting("rail_net") == 1;\n',),
    "info.nut": (
        '    AddSetting({ name = "rail_net",\n'
        '      description = "RAIL-NET: graft a new freight source onto a certified RAIL-LOOP through two PBS one-way junctions instead of a new line (default 0)",\n'
        '      min_value = 0, max_value = 1,\n'
        '      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
        '      flags = AICONFIG_BOOLEAN });\n',
    ),
    "main.nut": (
        'require("rail_net.nut");\n',
        "  _railNetState = null; // RAIL-NET : greffe transitoire (recherche des embranchements).\n",
    ),
    "task_rail.nut": (
        "  if (RAIL_NET && OpexRailNetSelect(this, year)) return;\n",
        "        if (OpexRailNetOwned(line)) continue;\n",
    ),
    "scheduler.nut": ("  if (RAIL_NET && this._railNetState != null) OpexRailNetStep(this);\n",),
    "rail_loop.nut": (
        "      && !OpexRailNetOwned(line)\n",
        "  if (RAIL_NET && !OpexRailNetHostMayGrow(owner, line)) return false;\n",
    ),
    "task_v284.nut": ("    if (OpexRailNetOwned(line)) continue;\n",),
}

MARKERS = ("RAIL_NET", '"rail_net"', "rail_net.nut", "OpexRailNet", "_railNetState")


def off_source(name, source):
    fragments = INSERTIONS.get(name, ())
    if not fragments:
        if name != "rail_net.nut" and any(m in source for m in MARKERS):
            raise AssertionError(f"RAIL-NET {name}: unrecognized source hunk")
        return source
    counts = [source.count(f) for f in fragments]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"RAIL-NET {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"RAIL-NET {name}: unexpected insertion count")
    for fragment in fragments:
        source = source.replace(fragment, "", 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"RAIL-NET {name}: residual marker after projection")
    return source
