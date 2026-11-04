"""Strict, idempotent removal of the T8 review fix (04/11/2026).

Newest layer: removed before RAIL-KEEP, RAIL-FILL and RAIL-LOOP. Fix in the
INVEST-STALL depot recheck of task_v284.nut (invest_stall, default 0): a
locomotive without cargo reports AIEngine.GetCapacity == -1, so the historic
"== 0" homogeneity guard cancelled every fleet top-up. The projection restores
the historic line byte for byte.
"""

REPLACED = {
    "task_v284.nut": ((
        "    /* Revue T8 : une locomotive sans cargo rend -1, pas 0 (mesure moteur 10/10,\n"
        "     * docs/invest_stall_diagnostic_p0_20261104.md). Meme predicat que la selection. */\n"
        "    local homogeneous = AIEngine.GetCapacity(AIVehicle.GetEngineType(oldVehicle)) <= 0;\n",
        "    local homogeneous = AIEngine.GetCapacity(AIVehicle.GetEngineType(oldVehicle)) == 0;\n",
    ),),
}

MARKERS = ("Revue T8",)


def off_source(name, source):
    replaced = REPLACED.get(name, ())
    if not replaced:
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T8 {name}: unrecognized source hunk")
        return source
    counts = [source.count(new) for new, _ in replaced]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T8 {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"REVUE-T8 {name}: unexpected replacement count")
    for new, old in replaced:
        source = source.replace(new, old, 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"REVUE-T8 {name}: residual marker after projection")
    return source
