"""Strict, idempotent removal of the T3 review fix (04/11/2026).

Newest layer: removed before RAIL-KEEP, RAIL-FILL and RAIL-LOOP. Both fixes are
unconditional and live in one hunk of _consumeRailUpgrade, in front of the
historical OpexExecuteUpgradeAfterSearch call:
  F2: RAIL-LOOP took the line during the upgrade A* -> release the slot;
  F1: M4/16.2 invariant, no upgrade infrastructure without a train slot.
The projection restores the two historical lines byte for byte.
"""

REPLACED = {
    "task_rail.nut": ((
        "  /* Revue T3 : RAIL-LOOP a pris la ligne pendant l'A* (meme garde que\n"
        "   * _expandRailLines, rejouee a la transaction). Rendre le slot sans poser\n"
        "   * ni memoriser : la ligne n'est pas en echec, la boucle la gere. */\n"
        "  if (RAIL_LOOP && (\"railLoop\" in state.line) && state.line.railLoop > 0) {\n"
        "    if (DECISION_LOG) OpexDecide(\"RAIL_EXPAND\", \"action=double_track line=\" + state.line.lineId\n"
        "        + \" reason=RLOOP_OWNED ok=0\");\n"
        "    this._railSearch = null;\n"
        "    return;\n"
        "  }\n"
        "  /* Revue T3 : invariant M4/16.2, aucune infrastructure sans slot train.\n"
        "   * Sans lui, voie 2, gares et depot sont poses, le train echoue, tout est\n"
        "   * demoli (TRAINFAIL). Meme memoire d'echec qu'avant, sans depense. */\n"
        "  local upgrade = OpexRailVehicleSlotAvailable()\n"
        "      ? OpexExecuteUpgradeAfterSearch(this._catalog, this._budget, state.line,\n"
        "                                      state.search, state.prep)\n"
        "      : { ok = false, reason = \"NOVEHSLOT\", cost = 0, train = null };\n",
        "  local upgrade = OpexExecuteUpgradeAfterSearch(this._catalog, this._budget, state.line,\n"
        "                                                state.search, state.prep);\n",
    ),),
}

MARKERS = ("NOVEHSLOT", "RLOOP_OWNED", "Revue T3 :")


def off_source(name, source):
    replaced = REPLACED.get(name, ())
    if not replaced:
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T3 {name}: unrecognized source hunk")
        return source
    counts = [source.count(new) for new, _ in replaced]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T3 {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"REVUE-T3 {name}: unexpected replacement count")
    for new, old in replaced:
        source = source.replace(new, old, 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"REVUE-T3 {name}: residual marker after projection")
    return source
