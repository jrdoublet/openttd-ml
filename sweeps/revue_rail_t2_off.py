"""Strict, idempotent removal of the REVUE-T2 hunks (04/11/2026).

Newest layer, removed before RAIL-KEEP, RAIL-FILL and RAIL-LOOP:
- F1, unconditional slot guard in _startRailUpgradeSearch (no-op at default:
  its only caller runs after the `_railSearch != null` early return when V190
  is off);
- F2, opt-in `rail_upgrade_cash_memory` (default 0).
"""

INSERTIONS = {
    "globals_pre.nut": (
        "/* REVUE-T2 F2 : devis reel de la voie 2 memorise apres un refus CASH, strict opt-in. */\n"
        "RAIL_UPGRADE_CASH_MEMORY <- false;\n",
    ),
    "settings.nut": ('  RAIL_UPGRADE_CASH_MEMORY = AIController.GetSetting("rail_upgrade_cash_memory") == 1;\n',),
    "info.nut": (
        '    AddSetting({ name = "rail_upgrade_cash_memory",\n'
        '      description = "REVUE-T2: remember the real second-track quote after a CASH refusal and use it to admit the next upgrade (default 0)",\n'
        '      min_value = 0, max_value = 1,\n'
        '      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
        '      flags = AICONFIG_BOOLEAN });\n',
    ),
    "task_rail.nut": (
        "  /* REVUE-T2 F1 : ne jamais ecraser le slot (sous V190, _expandRailLines ne rend\n"
        "   * pas la main quand une recherche est active). Sans effet au defaut. */\n"
        "  if (this._railSearch != null) return;\n",
        '            if (RAIL_UPGRADE_CASH_MEMORY && ("upgradeCashNeed" in line) && line.upgradeCashNeed > need)\n'
        "              need = line.upgradeCashNeed;\n",
        '      if (RAIL_UPGRADE_CASH_MEMORY && upgrade.cost > 0) state.line.rawset("upgradeCashNeed", upgrade.cost);\n',
    ),
    "builder_rail.nut": ("    if (RAIL_UPGRADE_CASH_MEMORY) result.cost = totalNeeded;\n",),
}

MARKERS = ("RAIL_UPGRADE_CASH_MEMORY", '"rail_upgrade_cash_memory"', "upgradeCashNeed", "REVUE-T2")


def off_source(name, source):
    fragments = INSERTIONS.get(name)
    if fragments is None:
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T2 {name}: unrecognized source hunk")
        return source
    counts = [source.count(f) for f in fragments]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T2 {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"REVUE-T2 {name}: unexpected insertion count")
    for fragment in fragments:
        source = source.replace(fragment, "", 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"REVUE-T2 {name}: residual marker after projection")
    return source
