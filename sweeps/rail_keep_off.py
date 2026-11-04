"""Strict, idempotent removal of the RAIL-KEEP opt-in wiring (04/11/2026).

Newest layer: removed before RAIL-FILL and RAIL-LOOP. The historical V284
guard line of _expandRailLines is kept byte-identical inside the ON form, so
the projection only restores its original single-line shape.
"""

INSERTIONS = {
    "globals_pre.nut": (
        "/* RAIL-KEEP : V284 actif ne coupe plus le doublement Cas 1/2 des autres lignes fret, strict opt-in. */\n"
        "RAIL_EXPAND_KEEP <- false;\n",
    ),
    "settings.nut": ('  RAIL_EXPAND_KEEP = AIController.GetSetting("rail_expand_keep") == 1;\n',),
    "info.nut": (
        '    AddSetting({ name = "rail_expand_keep",\n'
        '      description = "RAIL-KEEP: once V284 is active, keep historical second-train/second-track expansion on other freight lines (default 0)",\n'
        '      min_value = 0, max_value = 1,\n'
        '      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
        '      flags = AICONFIG_BOOLEAN });\n',
    ),
    "main.nut": ('require("rail_keep.nut");\n',),
}

REPLACED = {
    "task_rail.nut": ((
        "        if (RAIL_EXPAND_KEEP) {\n"
        "          if (OpexRailExpandKeepSkip(this, line)) continue;\n"
        "        } else if (V284_RAIL_GROWTH > 0 && this._v284State != null && ((\"kind\" in line) && line.kind == \"freight\")) continue;\n",
        "        if (V284_RAIL_GROWTH > 0 && this._v284State != null && ((\"kind\" in line) && line.kind == \"freight\")) continue;\n",
    ),),
}

MARKERS = ("RAIL_EXPAND_KEEP", '"rail_expand_keep"', "rail_keep.nut", "OpexRailExpandKeep")


def off_source(name, source):
    fragments = INSERTIONS.get(name, ())
    replaced = REPLACED.get(name, ())
    if not fragments and not replaced:
        if name != "rail_keep.nut" and any(m in source for m in MARKERS):
            raise AssertionError(f"RAIL-KEEP {name}: unrecognized source hunk")
        return source
    counts = [source.count(f) for f in fragments] + [source.count(new) for new, _ in replaced]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"RAIL-KEEP {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"RAIL-KEEP {name}: unexpected insertion count")
    for fragment in fragments:
        source = source.replace(fragment, "", 1)
    for new, old in replaced:
        source = source.replace(new, old, 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"RAIL-KEEP {name}: residual marker after projection")
    return source
