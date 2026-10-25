"""Exact byte subtraction for the N75-GSP experiment.

Restores the GOOD-source *already frozen* predecessor for PO01C SHA
comparisons. This does not edit any historical digest or policy default.
"""


ORIGINAL_INFO = (
    b'      description = "GOOD source rail: deliver goods from a factory already supplied by own NON-GOOD rail, joining its existing station A (experimental; 0=off)",\n'
    b'      min_value = 0, max_value = 1,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = AICONFIG_BOOLEAN });'
)
NEW_INFO = (
    b'      description = "GOOD source rail: 0=off, 1=parallel join only, 2=also try a bounded V264 spread join on the GOOD-producing origin if parallel fails",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });'
)
ORIGINAL_SETTINGS = b'  GOOD_SOURCE_RAIL_JOIN = AIController.GetSetting("good_source_rail_join") != 0;'
NEW_SETTINGS = (
    b'  local goodSourceJoinMode = AIController.GetSetting("good_source_rail_join");\n'
    b'  GOOD_SOURCE_RAIL_JOIN = goodSourceJoinMode >= 1 && goodSourceJoinMode <= 2;\n'
    b'  N75_GOOD_SOURCE_SPREAD = goodSourceJoinMode == 2;'
)
ADDED_BUILDER = (
    b'        /* N75-GSP mode 2 (strict opt-in): V264 already enforces station\n'
    b'         * ownership, spread and distant-join policy with AITestMode.\n'
    b'         * Try it ONLY when no parallel A platform can both join and pick\n'
    b'         * up GOOD. Never fall back to an independent station. */\n'
    b'        if (N75_GOOD_SOURCE_SPREAD && jointPlansA.len() == 0) {\n'
    b'          local spread = OpexV264SpreadJoinPlans(candidate.joinPlatform,\n'
    b'              candidate.joinStationId, statsA);\n'
    b'          local producingSpread = [];\n'
    b'          foreach (p in spread) {\n'
    b'            if (OpexRailPlatformCargoValue(p.anchor, p.step, p.length,\n'
    b'                    candidate.cargo, catalog.railCoverage, true) > 0)\n'
    b'              producingSpread.append(p);\n'
    b'          }\n'
    b'          jointPlansA = producingSpread;\n'
    b'          statsA.nCargo = jointPlansA.len();\n'
    b'          if (DECISION_LOG) OpexDecide("N75_GOOD_SPREAD", "phase=siteA"\n'
    b'              + " source=" + candidate.src + " station=" + candidate.joinStationId\n'
    b'              + " scanned=" + spread.len() + " productive=" + jointPlansA.len());\n'
    b'        }\n'
)


def historical_bytes(name, data):
    if name == "info.nut":
        assert data.count(NEW_INFO) == 1, "N75-GSP info insertion changed"
        return data.replace(NEW_INFO, ORIGINAL_INFO, 1)
    if name == "settings.nut":
        assert data.count(NEW_SETTINGS) == 1, "N75-GSP settings insertion changed"
        return data.replace(NEW_SETTINGS, ORIGINAL_SETTINGS, 1)
    if name == "builder_rail.nut":
        assert data.count(ADDED_BUILDER) == 1, "N75-GSP builder insertion changed"
        return data.replace(ADDED_BUILDER, b"", 1)
    return data
