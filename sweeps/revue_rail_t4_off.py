"""Strict, idempotent removal of the T4 review instrumentation (04/11/2026).

Newest layer: removed before RAIL-KEEP, RAIL-FILL and RAIL-LOOP. Measurement
only, inside the DECISION_LOG block of _continueRailSearch: the V214_PATH line
gains ninety= (U-shaped 90 degree turns, forbidden by pf.forbid_90_deg) and
segments=. The projection restores the historical V214_PATH call byte for byte.
"""

REPLACED = {
    "task_rail.nut": ((
        "        local geo = OpexV214PathGeometry(v214Tiles);\n"
        "        /* Revue T4 (mesure seule) : coudes a 90 deg, trois pas unitaires en U, que\n"
        "         * l'A* refuse sauf a la jonction de deux segments (source sans grand-parent). */\n"
        "        local ninety = 0;\n"
        "        for (local k = 0; k + 3 < v214Tiles.len(); k++) {\n"
        "          if (AIMap.DistanceManhattan(v214Tiles[k], v214Tiles[k + 3]) == 1\n"
        "              && AIMap.DistanceManhattan(v214Tiles[k], v214Tiles[k + 1]) == 1\n"
        "              && AIMap.DistanceManhattan(v214Tiles[k + 1], v214Tiles[k + 2]) == 1\n"
        "              && AIMap.DistanceManhattan(v214Tiles[k + 2], v214Tiles[k + 3]) == 1) ninety++;\n"
        "        }\n"
        "        OpexDecide(\"V214_PATH\", \"start=\" + v214Tiles[0] + \" end=\" + v214Tiles[v214Tiles.len() - 1]\n"
        "                   + \" steps=\" + geo.steps + \" turns=\" + geo.turns + \" exits=\" + geo.exits\n"
        "                   + \" tight=\" + geo.tight + \" turn_cost=\" + V214_RAIL_TURN_COST\n"
        "                   + \" tight_cost=\" + V214_RAIL_TIGHT_TURN_COST + \" ninety=\" + ninety\n"
        "                   + \" segments=\" + ((\"segments\" in slice) ? slice.segments : 1));\n",
        "        local geo = OpexV214PathGeometry(v214Tiles);\n"
        "        OpexDecide(\"V214_PATH\", \"start=\" + v214Tiles[0] + \" end=\" + v214Tiles[v214Tiles.len() - 1]\n"
        "                   + \" steps=\" + geo.steps + \" turns=\" + geo.turns + \" exits=\" + geo.exits\n"
        "                   + \" tight=\" + geo.tight + \" turn_cost=\" + V214_RAIL_TURN_COST\n"
        "                   + \" tight_cost=\" + V214_RAIL_TIGHT_TURN_COST);\n",
    ),),
}

MARKERS = ("Revue T4", " ninety=")


def off_source(name, source):
    replaced = REPLACED.get(name, ())
    if not replaced:
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T4 {name}: unrecognized source hunk")
        return source
    counts = [source.count(new) for new, _ in replaced]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T4 {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"REVUE-T4 {name}: unexpected replacement count")
    for new, old in replaced:
        source = source.replace(new, old, 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"REVUE-T4 {name}: residual marker after projection")
    return source
