"""Strict, idempotent removal of the T7 review instrumentation (04/11/2026).

Newest layer: removed before RAIL-KEEP, RAIL-FILL and RAIL-LOOP. Measurement
only, inside the DECISION_LOG block of _recordRailAttempt: RAIL_ATTEMPT gains
pred_trains= (trains of the economic quote) and built_trains= (trains laid).
"""

REPLACED = {
    "task_rail.nut": ((
        "               + \" pred_astar=\" + ((\"iterations\" in candidate) ? candidate.iterations : -1)\n"
        "               /* Revue T7 (mesure seule) : rames du devis contre rames posees (voie unique = 1). */\n"
        "               + \" pred_trains=\" + ((\"trains\" in candidate) ? candidate.trains : -1)\n"
        "               + \" built_trains=\" + ((\"trains\" in result) ? result.trains : -1)\n",
        "               + \" pred_astar=\" + ((\"iterations\" in candidate) ? candidate.iterations : -1)\n",
    ),),
}

MARKERS = ("Revue T7", " pred_trains=")


def off_source(name, source):
    replaced = REPLACED.get(name, ())
    if not replaced:
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T7 {name}: unrecognized source hunk")
        return source
    counts = [source.count(new) for new, _ in replaced]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T7 {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"REVUE-T7 {name}: unexpected replacement count")
    for new, old in replaced:
        source = source.replace(new, old, 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"REVUE-T7 {name}: residual marker after projection")
    return source
