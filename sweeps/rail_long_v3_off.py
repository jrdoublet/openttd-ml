"""RAIL-LONG v3, couche opt-in : projection strictement soustractive.

Les fixtures RAIL-LONG v1/v2 et INVEST-STALL restent immuables. Ce projecteur
retire exclusivement les ajouts v3 avant de consulter les empreintes v2.
Un hunk incomplet ou duplique provoque une erreur plutot qu'un OFF plausible.
"""

from __future__ import annotations


def _strip(name, source, changes):
    active = any(after in source for before, after, _ in changes)
    if not active:
        return source
    for before, after, count in changes:
        if source.count(after) != count:
            raise AssertionError(
                f"RAIL-LONG v3 {name}: hunk attendu {count}, observe {source.count(after)}"
            )
        source = source.replace(after, before)
    if "RAIL_LONG_V3" in source or "railLongV3" in source:
        raise AssertionError(f"RAIL-LONG v3 {name}: residu apres projection")
    return source


def _off_source(name, source):
    from rail_long_v3_multi_off import off_source as multi_off
    source = multi_off(name, source)
    if name == "globals_pre.nut":
        return _strip(name, source, [
            ("", "/* RAIL-LONG v3 : creation fret 7->6->court, sans changer les modes 1/2. */\nRAIL_LONG_V3 <- false;\n", 1),
        ])
    if name == "info.nut":
        return _strip(name, source, [
            ('      description = "RAIL-LONG: 1=production-based long train; 2=6-7 tile freight platforms, demand-sized trains and later upgrades (default 0)",\n'
             '      min_value = 0, max_value = 2, step_size = 1,\n',
             '      description = "RAIL-LONG: 1=production based; 2=6-7 tile platforms with upgrades; 3=initial long freight consist 7 then 6 tiles (default 0)",\n'
             '      min_value = 0, max_value = 3, step_size = 1,\n', 1),
        ])
    if name == "settings.nut":
        return _strip(name, source, [
            ("", "  RAIL_LONG_V3 = railLongMode == 3;\n", 1),
        ])
    if name == "main.nut":
        return _strip(name, source, [
            ("", 'require("rail_long_v3.nut");\n', 1),
        ])
    if name == "builder_rail.nut":
        return _strip(name, source, [
            ('if ((RAIL_LONG || RAIL_LONG_V2) && candidate.kind == "freight") {',
             'if ((RAIL_LONG || RAIL_LONG_V2 || RAIL_LONG_V3) && candidate.kind == "freight") {', 2),
            ('  local railLongLength = RAIL_LONG_V2 ? OpexRailLongV2SiteLength(catalog, candidate)\n'
             '      : OpexRailLongSiteLength(catalog, candidate);\n',
             '  local railLongLength = RAIL_LONG_V3 ? OpexRailLongV3SiteLength(catalog, candidate)\n'
             '      : (RAIL_LONG_V2 ? OpexRailLongV2SiteLength(catalog, candidate)\n'
             '                       : OpexRailLongSiteLength(catalog, candidate));\n', 1),
            ("",
             '    if (RAIL_LONG_V3) {\n'
             '      if (!("railLongV3Chosen" in candidate)) candidate.railLongV3Chosen <- false;\n'
             '      else candidate.railLongV3Chosen = false;\n'
             '    }\n', 1),
            ('OpexV163CandidateSecondary(candidate), false, RAIL_LONG);',
             'OpexV163CandidateSecondary(candidate), false, RAIL_LONG || RAIL_LONG_V3);', 1),
            ('            + (RAIL_LONG_V2 ? 100000 : 0) : 0;',
             '            + (RAIL_LONG_V2 ? 100000 : (RAIL_LONG_V3 ? 50000 : 0)) : 0;', 1),
            ("",
             '        if (RAIL_LONG_V3 && DECISION_LOG)\n'
             '          OpexDecide("RAIL_LONG_V3", "event=quote src=" + candidate.src\n'
             '              + " dst=" + candidate.dst + " len=" + length\n'
             '              + " cash=" + OpexAvailableCapital()\n'
             '              + " quoted_capital=" + (quote != null ? quote.capital : -1)\n'
             '              + " need=" + longCashNeed + " reserve=50000"\n'
             '              + " wagons=" + (quote != null ? quote.wagons : 0)\n'
             '              + " capacity=" + (quote != null ? quote.perTrain : 0)\n'
             '              + " profit=" + (quote != null ? quote.profitAnnual : -1));\n', 1),
            ("",
             '          if (RAIL_LONG_V3) {\n'
             '            candidate.railLongV3Chosen = true;\n'
             '            OpexRailLongV3Log("site", candidate, "LEN_" + length\n'
             '                + "_WAGONS_" + quote.wagons + "_CAP_" + quote.perTrain);\n'
             '          }\n', 1),
            ("", '    if (RAIL_LONG_V3) OpexRailLongV3Log("fallback", candidate, "SITE_ROI_OR_CASH");\n', 1),
            ('                                      RAIL_LONG && ("railLongChosen" in candidate) && candidate.railLongChosen);',
             '                                      (RAIL_LONG || RAIL_LONG_V3)\n'
             '                                          && ("railLongChosen" in candidate) && candidate.railLongChosen);', 1),
            ('                                        RAIL_LONG && ("railLongChosen" in candidate) && candidate.railLongChosen);',
             '                                        (RAIL_LONG || RAIL_LONG_V3)\n'
             '                                            && ("railLongChosen" in candidate) && candidate.railLongChosen);', 1),
            ("",
             '    /* Un detour A* peut invalider la marge ou la vitesse de la rame longue.\n'
             '     * Ne pas garder le devis Manhattan v3 pour construire sur ce detour. */\n'
             '    if (RAIL_LONG_V3 && ("railLongV3Chosen" in candidate)\n'
             '        && candidate.railLongV3Chosen\n'
             '        && (economics == null || economics.profitAnnual <= 0 || economics.roi <= 0)) {\n'
             '      plan.reason = "V3_ROUTE_ECON";\n'
             '      OpexRailLongV3Log("route_reject", candidate, "ECON_OR_TRACTION");\n'
             '      return plan;\n'
             '    }\n', 1),
            ("",
             '  if (!trains.failed && !OpexRailLongV3TrainsCertified(candidate, trains, catalog)) {\n'
             '    trains.failed = true;\n'
             '    trains.failure = "LENGTH";\n'
             '    trains.error = 0;\n'
             '  }\n', 2),
        ])
    if name == "economy.nut":
        return _strip(name, source, [
            ("",
             '  /* v3 only : l\'economie DOIT commander assez de wagons pour une rame\n'
             '   * initiale de >=200 unites, sans payer un quai de 7 pour 3 wagons.\n'
             '   * L\'absence d\'une loco de traction suffisante retourne un refus du devis\n'
             '   * long, jamais une rame silencieusement sous-motorisee. */\n'
             '  if (RAIL_LONG_V3 && railLongFill && kind == "freight" && fixedPlatformLength >= 6) {\n'
             '    local minimum = OpexRailLongV3WagonFloor(wagon, fixedPlatformLength);\n'
             '    if (minimum == 0 || minimum > maxWagons) return null;\n'
             '    if (correctedWagons < minimum) correctedWagons = minimum;\n'
             '  }\n', 1),
            ("",
             '  if (RAIL_LONG_V3 && railLongFill && kind == "freight" && fixedPlatformLength >= 6\n'
             '      && !OpexRailLongV3SingleTractionOK(loco, wagon, wagons)) return null;\n', 1),
        ])
    if name == "task_rail.nut":
        return _strip(name, source, [
            ("",
             '    if (RAIL_LONG_V3 && ("railLongV3Chosen" in candidate) && candidate.railLongV3Chosen) {\n'
             '      local builtV3 = this._lines[this._lines.len() - 1];\n'
             '      builtV3.rawset("railLongV3", true);\n'
             '      builtV3.rawset("railLongV3Build", true);\n'
             '      if (DECISION_LOG)\n'
             '        OpexDecide("RAIL_LONG_V3", "event=build line=" + idx\n'
             '            + " src=" + candidate.src + " dst=" + candidate.dst\n'
             '            + " len_a=" + result.platformA.length\n'
             '            + " len_b=" + result.platformB.length\n'
             '            + " wagons=" + builtV3.wagons\n'
             '            + " capacity=" + AIVehicle.GetCapacity(builtV3.vehicles[0], builtV3.cargo)\n'
             '            + " length16=" + AIVehicle.GetLength(builtV3.vehicles[0])\n'
             '            + " cash=" + OpexAvailableCapital());\n'
             '    }\n', 1),
        ])
    return source


def off_source(name, source):
    from rail_long_merged_off import verify_stage
    # A broken v3 require must not be accepted just because multi-off
    # successfully deletes the later requires first.
    if (name == "main.nut"
            and 'require("rail_long_v3_multi.nut");' in source
            and source.count('require("rail_long_v3.nut");') != 1):
        raise AssertionError("RAIL-LONG v3 main.nut: initial require missing/duplicated")
    result = _off_source(name, source)
    verify_stage("v3", name, source, result)
    return result
