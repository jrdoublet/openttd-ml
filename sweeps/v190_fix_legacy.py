"""Strict historical OFF projection for the opt-in V190-FIX implementation.

Remove only reviewed V190-FIX additions before inherited SHA contracts.
Never rebaseline their hashes: a changed or partial fix must fail closed.
This is a static source projection, not a substitute for engine smokes.
"""

import hashlib

INDEPENDENT_START = "/* V190-FIX : deux voies physiques independantes"
INDEPENDENT_END = "/* V190 : Repli securise de la seconde voie."
INDEPENDENT_SHA256 = "7057112d3bdc8484b76966b7bce3440a76746e38f8950c6893701c7613aa2f03"

REPLACEMENTS = {
    "builder_rail.nut": [
        (
            """            /* V233L conserve sa boucle historique ; V190 n'en a plus besoin.
             * Chaque rame a deja deux ordres propres et une voie isolée. */
            local networkOk = OpexV233LIs(candidate)
                ? OpexConvertDoubleTrackToLoop(loopLine, loopDiag)
                : OpexV190VerifyIndependentDouble(loopLine, depot, depot2);
            if (!networkOk && !OpexV233LIs(candidate) && loopDiag != null)
              loopDiag.step <- "INDEPENDENT_TRACK_CHECK";
            if (networkOk) {
""",
            "            if (OpexConvertDoubleTrackToLoop(loopLine, loopDiag)) {\n",
        ),
        ("              if (!OpexV233LIs(candidate)) result.v190Independent <- true;\n", ""),
        (
            '    result.v181Loop <- !("v190Independent" in result) || !result.v190Independent;\n',
            "    result.v181Loop <- true;\n",
        ),
    ],
    "task_rail.nut": [
        (
            """          /* La double voie V190-FIX a une rame PAR voie sans aiguillage.
           * Un clone supplementaire ferait se rencontrer deux trains sur
           * la meme voie bidirectionnelle. */
          if (("v190Independent" in line) && line.v190Independent) continue;
""",
            "",
        ),
        ('      v190Independent = ("v190Independent" in result) ? result.v190Independent : false,\n', ""),
        (
            """      if ((("v181Loop" in result) && result.v181Loop)
          || (("v190Independent" in result) && result.v190Independent)) {
""",
            '      if (("v181Loop" in result) && result.v181Loop) {\n',
        ),
    ],
}


# A second pass over a fully projected merge is already OFF.  Re-entering the
# newer RAIL-LONG/INVEST-STALL projector with those bytes would fail its
# independent ON-source SHA guard.  Only these frozen, actually reviewed
# outputs bypass that preprocessor; no marker-based permissive shortcut.
_MERGED_V190_ALREADY_OFF_SHA256 = {
    "builder_rail.nut": "d570af06efdfcd02899a45a2be6b8250fb225a66a7f4f7533d05208b21c4a7f5",
    "task_rail.nut": "4ced6a57b893a2f599a845720d90f8380f7ee721095fa83b34ab4984c2873899",
}

# When the frozen SEARCH-PRIO source layer has already been removed first,
# V190's equally strict OFF output is a different approved merge stage.
_MERGED_V190_PRIO_FIRST_OFF_TASK_RAIL_SHA256 = "d3588288a7f3f6e2b610fe3d7e3331b8d215f157fb8147830b2ac855db773e26"


def off_source(name, source):
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if digest == _MERGED_V190_ALREADY_OFF_SHA256.get(name) or (
        name == "task_rail.nut" and digest == _MERGED_V190_PRIO_FIRST_OFF_TASK_RAIL_SHA256
    ):
        return source
    from rail_depot_signal_legacy import strip_if_present as depot_signal_off
    source = depot_signal_off(name, source)
    replacements = REPLACEMENTS.get(name, ())
    matches = [source.count(new) for new, _ in replacements]
    has_helper = name == "builder_rail.nut" and INDEPENDENT_START in source
    if any(n > 1 for n in matches) or (name == "builder_rail.nut" and source.count(INDEPENDENT_START) > 1):
        raise AssertionError(f"V190-FIX {name}: nonunique source")
    if not any(matches) and not has_helper:
        return source
    if not all(n == 1 for n in matches) or (name == "builder_rail.nut" and not has_helper):
        raise AssertionError(f"V190-FIX {name}: partial or modified source")
    if has_helper:
        assert source.count(INDEPENDENT_END) == 1, "V190-FIX: missing old rollback anchor"
        a = source.index(INDEPENDENT_START)
        b = source.index(INDEPENDENT_END, a)
        block = source[a:b]
        assert hashlib.sha256(block.encode("utf-8")).hexdigest() == INDEPENDENT_SHA256, (
            "V190-FIX: independent-track guard changed"
        )
        source = source[:a] + source[b:]
    for new, old in replacements:
        source = source.replace(new, old, 1)
    return source
