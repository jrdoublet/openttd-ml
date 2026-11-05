"""Projection soustractive de l'infrastructure multihead RAIL-LONG v3.

Retire UNIQUEMENT la tranche multihead + l'integration upgrade v3 convenue
avec le prime avant la projection deja figee de la tranche initiale.
Un marqueur de fichier incomplet ou un doublon est une erreur de contrat.
Les fixtures v1/v2 et l'etat pre-v3 ne sont jamais reecrits.
"""


def _replace(source, old, new, times=1):
    if source.count(new) != times:
        raise AssertionError(
            f"v3 multi: hunk attendu {times}, trouve {source.count(new)}: {new[:65]!r}"
        )
    return source.replace(new, old)


def _drop_span(source, first, following, times=1):
    if source.count(first) != times or source.count(following) < times:
        raise AssertionError(f"v3 multi: span absent ou duplique {first[:65]!r}")
    for _ in range(times):
        start = source.index(first)
        finish = source.index(following, start)
        source = source[:start] + source[finish:]
    return source


def upgrade_reservation_off(name, source):
    """Retire seulement la reservation 04/11, avant les couches historiques."""
    reservation = '  if (this._railLongV3UpgradePending != null) return; // reservation jusqu\'au commit/rollback v3.\n'
    if name == "task_rail.nut" and reservation in source:
        return _replace(source, "", reservation)
    return source


def off_source(name, source):
    from fleet_arb_off import off_source as fleet_off
    source = fleet_off(name, source)
    source = upgrade_reservation_off(name, source)
    if name == "main.nut" and 'require("rail_long_v3_multi.nut");' in source:
        source = _replace(source, "", 'require("rail_long_v3_multi.nut");\n')
        source = _replace(source, "", 'require("rail_long_v3_upgrade.nut");\n')
        source = _replace(source, "",
                          "  _railLongV3UpgradePending = null; // upgrade v3 transactionnel, reprise apres Save/Load.\n")
    elif name == "builder_rail.nut" and "v3LocoCount = 1" in source:
        source = _replace(source,
            "                         cargo2 = -1, wagons2 = 0)",
            "                         cargo2 = -1, wagons2 = 0, v3LocoCount = 1)")
        source = _drop_span(source,
            "  /* Avant TOUT achat, brancher le constructeur 2/3 motrices uniquement sur\n",
            "  local wagon = catalog.wagonByCargo[cargo];\n")
        source = _replace(source,
            "                                 OpexV163Cargo2(candidate), OpexV163Wagons2(candidate));",
            '                                 OpexV163Cargo2(candidate), OpexV163Wagons2(candidate),\n'
            '                                 (RAIL_LONG_V3 && ("railLongV3Chosen" in candidate)\n'
            '                                     && candidate.railLongV3Chosen\n'
            '                                     && ("railLongV3LocoCount" in candidate))\n'
            '                                     ? candidate.railLongV3LocoCount : 1);')
        source = _replace(source,
            "                                 candidate.wagons, candidate.platformLength, false);",
            '                                 candidate.wagons, candidate.platformLength, false,\n'
            '                                 -1, 0,\n'
            '                                 (RAIL_LONG_V3 && ("railLongV3Chosen" in candidate)\n'
            '                                     && candidate.railLongV3Chosen\n'
            '                                     && ("railLongV3LocoCount" in candidate))\n'
            '                                     ? candidate.railLongV3LocoCount : 1);')
    elif name == "economy.nut" and "local railLongV3Multi = null;" in source:
        source = _replace(source,
            '  if (RAIL_LONG_V3 && railLongFill && kind == "freight" && fixedPlatformLength >= 6\n'
            '      && !OpexRailLongV3SingleTractionOK(loco, wagon, wagons)) return null;\n',
            '  /* Mode 3 seulement : selectionner une, puis deux, puis trois locomotives\n'
            '   * avec la pente de partie et TOUS les wagons charges. L\'ancien estimateur\n'
            '   * restaure son chemin strictement identique en modes 0/1/2. */\n'
            '  local railLongV3Multi = null;\n'
            '  if (RAIL_LONG_V3 && railLongFill && kind == "freight" && fixedPlatformLength >= 6) {\n'
            '    railLongV3Multi = OpexRailLongV3MultiChoose(catalog, cargo,\n'
            '        fixedPlatformLength, wagons, travelDist);\n'
            '    if (railLongV3Multi == null) return null;\n'
            '    loco = railLongV3Multi.profile;\n'
            '    effectiveSpeed = railLongV3Multi.speed;\n'
            '    oneWayDays = travelDist.tofloat() / (0.036 * effectiveSpeed);\n'
            '    if (oneWayDays < 1) oneWayDays = 1;\n'
            '    roundTripDays = 2 * oneWayDays;\n'
            '    tripsPerMonth = OpexLoadedTripsPerMonth(oneWayDays + dwellDays,\n'
            '        roundTripDays + dwellDays, false);\n'
            '  }\n')
        source = _replace(source, "",
            '  /* Le constructeur v3 multihead est reserve a UNE rame fret sur UNE voie\n'
            '   * dediee. Il ne donne aucun permis de construire un second train. */\n'
            '  if (railLongV3Multi != null) maxTrains = 1;\n')
        source = _replace(source, "",
            '  if (railLongV3Multi != null) {\n'
            '    result.railLongV3LocoCount <- railLongV3Multi.count;\n'
            '    result.railLongV3GradeSpeed <- railLongV3Multi.gradeSpeed;\n'
            '  }\n')
        source = _replace(source, "",
            '  if (RAIL_LONG_V3) {\n'
            '    candidate.rawset("railLongV3LocoCount",\n'
            '        ("railLongV3LocoCount" in economics) ? economics.railLongV3LocoCount : 1);\n'
            '    candidate.rawset("railLongV3GradeSpeed",\n'
            '        ("railLongV3GradeSpeed" in economics) ? economics.railLongV3GradeSpeed : 0);\n'
            '  }\n')
    elif name == "task_rail.nut" and 'builtV3.rawset("railLongV3Multihead"' in source:
        source = _replace(source, "",
            '  if (RAIL_LONG_V3 && OpexRailLongV3UpgradeSelect(this, year)) return;\n')
        source = _replace(source, "",
            '      local v3Motors = ("railLongV3LocoCount" in candidate)\n'
            '          ? candidate.railLongV3LocoCount : 1;\n'
            '      builtV3.rawset("railLongV3LocoCount", v3Motors);\n'
            '      builtV3.rawset("railLongV3Multihead", v3Motors > 1);\n')
        source = _replace(source, "", '            + " locos=" + v3Motors\n')
    elif name == "task_v257.nut" and "OpexRailLongV3MultiLine(line)" in source:
        source = _replace(source, "",
            '  /* Le plan V257 de renouvellement ne connait qu\'un moteur en tete.\n'
            '   * Ne jamais remplacer une rame RAIL-LONG v3 multihead par son faux\n'
            '   * equivalent mono-locomotive, meme apres changement du reglage v3. */\n'
            '  if (OpexRailLongV3MultiLine(line)) return;\n')
        source = _replace(source, "",
            '  if (OpexRailLongV3MultiLine(line)) {\n'
            '    /* Annuler la transaction V257 devenue obsolete, rendre le service.\n'
            '     * Aucun nouveau train n\'a encore ete construit. */\n'
            '    if (AIVehicle.IsStoppedInDepot(oldVehicle)) AIVehicle.StartStopVehicle(oldVehicle);\n'
            '    else AIVehicle.SendVehicleToDepot(oldVehicle);\n'
            '    this._v257Pending = null; this._v257PendingLine = null;\n'
            '    return;\n'
            '  }\n')
    elif name == "task_v284.nut" and "OpexRailLongV3MultiLine(line)" in source:
        source = _replace(source, "", "    if (OpexRailLongV3MultiLine(line)) continue;\n")
        source = _replace(source, "",
            '  if (OpexRailLongV3MultiLine(line) && pending.phase != "committed")\n'
            '    pending.phase = "rollback";\n')
    elif name == "invest_stall.nut" and "OpexRailLongV3MultiLine(line)" in source:
        source = _replace(source, "",
            '  /* La formule monohead ne peut pas etre appliquee a un multihead : ni\n'
            '   * nombre de wagons = total-1, ni vitesse d\'un seul moteur. La porte\n'
            '   * SourceGap refusera toute origine concerneee plutot que creer une\n'
            '   * offre fictive a partir de ce zero conservateur. */\n'
            '  if (OpexRailLongV3MultiLine(line)) return 0.0;\n')
        source = _replace(source, "",
            '    if (existingId == industry && OpexRailLongV3MultiLine(existing)) {\n'
            '      missing.reason = "multihead_unmodelled";\n'
            '      return missing;\n'
            '    }\n')
    elif name == "invest_stall_fleet.nut" and "OpexRailLongV3MultiLine(line)" in source:
        source = _replace(source, "", "    if (OpexRailLongV3MultiLine(line)) continue;\n")
    elif name == "candidates.nut" and "OpexRailLongV3MultiLine(mother)" in source:
        source = _replace(source, "", "  if (OpexRailLongV3MultiLine(mother)) return false;\n")
    elif name == "orchestrator.nut" and "_railLongV3UpgradePending" in source:
        source = _replace(source, "",
            '  /* RAIL-LONG v3 : terminer ou annuler proprement une transaction deja\n'
            '   * engagee, meme si le reglage a ete coupe entre Save et Load. */\n'
            '  if (this._railLongV3UpgradePending != null) OpexRailLongV3UpgradeStep(this);\n\n')
        source = _replace(source,
            '  if (V284_RAIL_GROWTH > 0 || V233_LONG_GOOD > 0 || (INVEST_STALL && OpexV284Busy(this))',
            '  if (this._railLongV3UpgradePending == null &&\n'
            '      (V284_RAIL_GROWTH > 0 || V233_LONG_GOOD > 0 || (INVEST_STALL && OpexV284Busy(this))')
        source = _replace(source,
            '      || OpexInvestStallPending(this) || OpexRailLongV2FleetPending(this)) OpexV284Tick(this);',
            '      || OpexInvestStallPending(this) || OpexRailLongV2FleetPending(this))) OpexV284Tick(this);')
        source = _replace(source,
            '  if (this._railLongV2Pending == null &&',
            '  if (this._railLongV3UpgradePending == null && this._railLongV2Pending == null &&')
    elif name == "persist.nut" and "railLongV3Upgrade" in source:
        source = _replace(source, "",
            '  if (RAIL_LONG_V3 || this._railLongV3UpgradePending != null)\n'
            '    saveObj.railLongV3Upgrade <- this._railLongV3UpgradePending;\n')
        source = _replace(source, "",
            '  if (("railLongV3Upgrade" in data) && typeof data.railLongV3Upgrade == "table")\n'
            '    this._railLongV3UpgradePending = data.railLongV3Upgrade;\n')
        source = _replace(source, "",
            '  if (this._railLongV3UpgradePending != null) OpexRailLongV3UpgradeReconcile(this);\n')
    return source
