"""Strict, idempotent removal of the T6 review fix (04/11/2026).

Newest layer: removed before RAIL-KEEP, RAIL-FILL and RAIL-LOOP. Unconditional
fix in OpexRollback: only OUR rail is undone (level crossings lose their rail,
not the road; never-built tiles are no longer demolished). The projection
restores the historical demolition loop byte for byte.
"""

REPLACED = {
    "builder_rail.nut": ((
        "  for (local i = 1; i < tiles.len() - 1; i++) {\n"
        "    local t = tiles[i];\n"
        "    /* Revue T6 : ne defaire que NOTRE rail. Un passage a niveau perd son rail,\n"
        "     * pas la route ; une case jamais posee (arbres, champ, route d'autrui\n"
        "     * apres un echec) n'est plus rasee. */\n"
        "    if (AIRail.IsLevelCrossingTile(t)) {\n"
        "      AIRail.RemoveRailTrack(t, AIRail.GetRailTracks(t));\n"
        "      continue;\n"
        "    }\n"
        "    if (!AITile.HasTransportType(t, AITile.TRANSPORT_RAIL)\n"
        "        || !AICompany.IsMine(AITile.GetOwner(t))) continue;\n"
        "    AITile.DemolishTile(t);\n"
        "  }\n"
        "}\n",
        "  for (local i = 1; i < tiles.len() - 1; i++) {\n"
        "    AITile.DemolishTile(tiles[i]);\n"
        "  }\n"
        "}\n",
    ),),
}

MARKERS = ("Revue T6",)


def off_source(name, source):
    replaced = REPLACED.get(name, ())
    if not replaced:
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T6 {name}: unrecognized source hunk")
        return source
    counts = [source.count(new) for new, _ in replaced]
    if all(c == 0 for c in counts):
        if any(m in source for m in MARKERS):
            raise AssertionError(f"REVUE-T6 {name}: unrecognized source hunk")
        return source
    if any(c != 1 for c in counts):
        raise AssertionError(f"REVUE-T6 {name}: unexpected replacement count")
    for new, old in replaced:
        source = source.replace(new, old, 1)
    if any(m in source for m in MARKERS):
        raise AssertionError(f"REVUE-T6 {name}: residual marker after projection")
    return source
