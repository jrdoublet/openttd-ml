"""Strict, idempotent removal of the T5 review instrumentation (04/11/2026).

Newest layer: removed before RAIL-KEEP, RAIL-FILL and RAIL-LOOP. Measurement
only, inside the DECISION_LOG block of _recordRailAttempt: the RAIL_BUILD line
gains len_a/len_b and back_a/back_b (rear of each platform free and flat at
build time, the exact RAIL-LOOP back_lead criterion). The projection restores
the historical RAIL_BUILD call byte for byte.
"""

REPLACED = {
    "task_rail.nut": ((
        "                      + \" pred_revenue2=\" + candidate.revenue2 : \"\") + p2Trace\n"
        "                 /* Revue T5 (mesure seule) : arriere de quai libre et plat a la pose,\n"
        "                  * critere exact du back_lead de RAIL-LOOP. */\n"
        "                 + (((\"platformA\" in result) && result.platformA != null\n"
        "                     && (\"platformB\" in result) && result.platformB != null)\n"
        "                    ? \" len_a=\" + result.platformA.length + \" len_b=\" + result.platformB.length\n"
        "                      + \" back_a=\" + (OpexRailLoopBackPlan(result.platformA) != null ? 1 : 0)\n"
        "                      + \" back_b=\" + (OpexRailLoopBackPlan(result.platformB) != null ? 1 : 0) : \"\"));\n",
        "                      + \" pred_revenue2=\" + candidate.revenue2 : \"\") + p2Trace);\n",
    ),),
}

MARKERS = ("Revue T5", " back_a=")


def off_source(name, source):
    replaced = REPLACED.get(name, ())
    if not replaced:
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T5 {name}: unrecognized source hunk")
        return source
    counts = [source.count(new) for new, _ in replaced]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T5 {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"REVUE-T5 {name}: unexpected replacement count")
    for new, old in replaced:
        source = source.replace(new, old, 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"REVUE-T5 {name}: residual marker after projection")
    return source
