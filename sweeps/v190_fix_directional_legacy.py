"""Strict, idempotent OFF projection of V190-FIX2.

The pre-FIX2 text is frozen in the exact old fragments below. Never refresh
historic SHA hashes to accommodate this opt-in. Source projection cannot
validate Squirrel compilation or an OpenTTD railway topology.
"""

import hashlib

# A second projection of the exact merged task_rail.nut OFF source must not
# re-enter INVEST-STALL platform's ON-source SHA gate.  This digest is the
# reviewed output of a complete first directional+RAIL-LONG projection, never
# a pattern-based exemption for a partly edited source.
_MERGED_TASK_RAIL_ALREADY_OFF_SHA256 = (
    "867f75ed9480ea7f48829ab36217746c807ede0c83b5e76cb28daae97f74e9eb"
)

REPLACEMENTS = {
    "info.nut": [(
        '''    AddSetting({
      name = "v190_fix_directional",
      description = "V190-FIX2 experimental two-crossovers, one track per direction and PBS one-way; requires V190+V197 (default 0)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

''', "")],
    "globals_pre.nut": [(
        "/* V190-FIX2 : boucle deux aiguillages et signaux directionnels (strict opt-in). */\n"
        "V190_FIX_DIRECTIONAL <- false;\n", "")],
    "settings.nut": [(
        '  V190_FIX_DIRECTIONAL = AIController.GetSetting("v190_fix_directional") != 0;\n', "")],
    "main.nut": [(
        'require("v190_fix_directional.nut");\n', "")],
    "builder_rail.nut": [(
        '''            /* V233L conserve sa boucle historique. V190-FIX1 reste en deux
             * voies isolees. V190-FIX2 sous V190+V197 et reglage opt-in
             * essaie une boucle a DEUX aiguillages, chacun hors gorge,
             * avec des signaux de voie 1 A->B et voie 2 B->A. */
            local v190Directional = !OpexV233LIs(candidate) &&
                V190_FIX_DIRECTIONAL && V197_GUIDED_DOUBLE;
            local networkOk = OpexV233LIs(candidate)
                ? OpexConvertDoubleTrackToLoop(loopLine, loopDiag)
                : (v190Directional
                    ? OpexV190Fix2BuildDirectional(loopLine, depot, depot2, candidate.platformLength, loopDiag)
                    : OpexV190VerifyIndependentDouble(loopLine, depot, depot2));
            if (!networkOk && !OpexV233LIs(candidate) && !v190Directional && loopDiag != null)
              loopDiag.step <- "INDEPENDENT_TRACK_CHECK";
''',
        '''            /* V233L conserve sa boucle historique ; V190 n'en a plus besoin.
             * Chaque rame a deja deux ordres propres et une voie isolée. */
            local networkOk = OpexV233LIs(candidate)
                ? OpexConvertDoubleTrackToLoop(loopLine, loopDiag)
                : OpexV190VerifyIndependentDouble(loopLine, depot, depot2);
            if (!networkOk && !OpexV233LIs(candidate) && loopDiag != null)
              loopDiag.step <- "INDEPENDENT_TRACK_CHECK";
'''),
        ('''              if (!OpexV233LIs(candidate) && !v190Directional) result.v190Independent <- true;
              if (v190Directional) result.v190Directional <- true;
''', '''              if (!OpexV233LIs(candidate)) result.v190Independent <- true;
''')],
    "task_rail.nut": [(
        '      v190Directional = ("v190Directional" in result) ? result.v190Directional : false,\n', ""),
        ('''    if (DECISION_LOG && ("v190Directional" in result) && result.v190Directional) {
      OpexDecide("V190_FIX", "phase=commission line=" + idx
          + " trains=" + result.trains
          + " loco1=" + (result.vehicles.len() > 0 ? result.vehicles[0] : -1)
          + " loco2=" + (result.vehicles.len() > 1 ? result.vehicles[1] : -1)
          + " a1=" + AIStation.GetStationID(result.stationA)
          + " a2=" + AIStation.GetStationID(result.stationA2)
          + " b1=" + AIStation.GetStationID(result.stationB)
          + " b2=" + AIStation.GetStationID(result.stationB2)
          + " orders1=" + (result.vehicles.len() > 0 ? AIOrder.GetOrderCount(result.vehicles[0]) : -1)
          + " orders2=" + (result.vehicles.len() > 1 ? AIOrder.GetOrderCount(result.vehicles[1]) : -1));
    }
''', "")],
}

SIGNATURES = {
    "info.nut": ('name = "v190_fix_directional"',),
    "globals_pre.nut": ('V190_FIX_DIRECTIONAL <-',),
    "settings.nut": ('GetSetting("v190_fix_directional")',),
    "main.nut": ('require("v190_fix_directional.nut")',),
    "builder_rail.nut": ("v190Directional", "OpexV190Fix2BuildDirectional"),
    "task_rail.nut": ("v190Directional",),
}


def off_source(name, source):
    if name == "task_rail.nut" and hashlib.sha256(source.encode("utf-8")).hexdigest() == (
            _MERGED_TASK_RAIL_ALREADY_OFF_SHA256):
        if any(marker in source for marker in SIGNATURES[name]):
            raise AssertionError("V190-FIX2 task_rail.nut: reviewed OFF SHA has ON markers")
        return source
    # The newer RAIL-LONG fleet helper also mentions v190Directional.  It
    # must be projected first to preserve V190-FIX2's strict signatures.
    from rail_long_source_off import off_source as rail_long_off
    source = rail_long_off(name, source)
    replacements = REPLACEMENTS.get(name, ())
    if not replacements:
        return source
    counts = [source.count(new) for new, _ in replacements]
    if any(n > 1 for n in counts):
        raise AssertionError(f"V190-FIX2 duplicate hunk in {name}")
    if not any(counts):
        if any(marker in source for marker in SIGNATURES.get(name, ())):
            raise AssertionError(f"V190-FIX2 unreviewed hunk in {name}")
        return source
    if not all(n == 1 for n in counts):
        raise AssertionError(f"V190-FIX2 partial hunk in {name}")
    for new, old in reversed(replacements):
        source = source.replace(new, old, 1)
    return source
