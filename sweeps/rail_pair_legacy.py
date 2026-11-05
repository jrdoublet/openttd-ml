"""Strict OFF projection for RAIL-PAIR (settings, transaction and call sites).

Remove this option before the reviewed RAIL-OPEN/SIBLING historical projections.
Never modify their pinned fixtures to accommodate later experiments.
"""

import hashlib

# 2026-11-05 ROAD1Y+RAIL merge: independently reviewed exact OFF output of
# task_rail after the first RAIL-PAIR projection. A second invocation must
# not re-enter older INVEST-platform and RAIL-LONG projectors with a source
# that has already been projected. No other SHA or file receives this path.
MERGED_TASK_RAIL_PAIR_OFF_SHA256 = "70aabdbc67ae8f5ad3aefbbf18f0a836cc977c55114923f5445ac385330b906e"

CHUNKS = {
    "globals_pre.nut": "/* RAIL-PAIR : second train chargeant sur un quai source dedie, OFF par defaut. */\nRAIL_PAIR <- 0;\n",
    "info.nut": (
        '    AddSetting({ name = "rail_pair",\n'
        '      description = "RAIL-PAIR: freight second source platform and alternating trains on single track (default 0)",\n'
        '      min_value = 0, max_value = 1,\n'
        '      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
        '      flags = AICONFIG_BOOLEAN });\n'
    ),
    "settings.nut": (
        '  local railPair = AIController.GetSetting("rail_pair");\n'
        '  RAIL_PAIR = (railPair != null && railPair > 0) ? 1 : 0;\n'
    ),
    "main.nut": [
        '  _v271Pending = null; // RAIL-PAIR: transaction reprenable V271b.\n  _v271Year = -1;\n',
        '  function _v271TandemSource(year);\n  function _v271Continue();\n',
        'require("rail_pair_geometry.nut");\nrequire("task_rail_pair.nut");\n',
    ],
    "task_rail.nut": [
        '  if (RAIL_PAIR > 0) OpexRailPairReview(this);\n',
        '  if (RAIL_PAIR > 0 && this._v271TandemSource(year)) return;\n',
        '        if (RAIL_PAIR > 0 && ("v271Tandem" in line) && line.v271Tandem) continue;\n',
    ],
    "persist.nut": [
        '  if (RAIL_PAIR > 0 || this._v271Pending != null)\n'
        '    saveObj.railPair <- { year = this._v271Year, pending = this._v271Pending };\n',
        '  if ("railPair" in data && typeof data.railPair == "table") {\n'
        '    this._v271Year = ("year" in data.railPair) ? data.railPair.year : -1;\n'
        '    this._v271Pending = ("pending" in data.railPair) ? data.railPair.pending : null;\n'
        '  }\n',
        '  if (this._v271Pending != null && RAIL_PAIR == 0) {\n'
        '    if (this._v271Pending.phase != "commit") {\n'
        '      this._v271Pending.phase = "rollback";\n'
        '      this._v271Pending.reason = "disabled_after_load";\n'
        '    }\n'
        '    /* _runNextTask reprend le rollback a chaque passage sans tache fantome. */\n'
        '  }\n',
    ],
    "scheduler.nut": [
        '  /* Un chantier RAIL-PAIR partiellement sauvegarde finit meme si l\'option a ete desactivee. */\n'
        '  if (this._v271Pending != null && RAIL_PAIR == 0) this._v271Continue();\n',
    ],
    "task_v257.nut": ['  if (this._v271Pending != null) return;\n'],
    "task_report.nut": ['  if (this._v271Pending != null && this._v271Pending.lineId == line.lineId) return;\n'],
    "task_v284.nut": [
        '  if (owner._v271Pending != null) return false;\n',
        '    if (("v271Tandem" in line) && line.v271Tandem) continue;\n',
    ],
}

REPLACEMENTS = {
    "builder_rail.nut": [
        ('function OpexV190FindParallelPlatformPlans(platform, allowSlopes = false, maxSide = JOIN_PARALLEL_MAX_SIDE)',
         'function OpexV190FindParallelPlatformPlans(platform)'),
        ('for (local dist = 1; dist <= maxSide; dist++) {',
         'for (local dist = 1; dist <= JOIN_PARALLEL_MAX_SIDE; dist++) {'),
        ('(allowSlopes || AITile.GetSlope(lead2) == AITile.SLOPE_FLAT)',
         'AITile.GetSlope(lead2) == AITile.SLOPE_FLAT'),
        ('(allowSlopes || AITile.GetSlope(tile) == AITile.SLOPE_FLAT)',
         'AITile.GetSlope(tile) == AITile.SLOPE_FLAT'),
    ],
}


def off_source(name, source):
    from fleet_arb_off import off_source as fleet_off
    source = fleet_off(name, source)
    if name == "task_rail.nut" and hashlib.sha256(source.encode("utf-8")).hexdigest() == MERGED_TASK_RAIL_PAIR_OFF_SHA256:
        if "RAIL_PAIR" in source or "_v271TandemSource" in source:
            raise AssertionError("RAIL-PAIR task_rail: projected SHA contains live pair wiring")
        return source
    from rail_depot_signal_legacy import strip_if_present as depot_signal_off
    source = depot_signal_off(name, source)
    chunks = CHUNKS.get(name, [])
    if isinstance(chunks, str):
        chunks = [chunks]
    replacements = REPLACEMENTS.get(name, [])
    present = [source.count(chunk) for chunk in chunks]
    swapped = [source.count(new) for new, old in replacements]
    if any(count > 1 for count in present + swapped):
        raise AssertionError(f"RAIL-PAIR {name}: nonunique opt-in hunk")
    if any(present + swapped) and not all(count == 1 for count in present + swapped):
        raise AssertionError(f"RAIL-PAIR {name}: partial or altered opt-in")
    if any(present + swapped):
        for chunk in reversed(chunks):
            source = source.replace(chunk, "", 1)
        for new, old in replacements:
            source = source.replace(new, old, 1)
        return source
    if "RAIL_PAIR" in source or 'name = "rail_pair"' in source or 'GetSetting("rail_pair")' in source:
        raise AssertionError(f"RAIL-PAIR {name}: changed opt-in hunk")
    return source
