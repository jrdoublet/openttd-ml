"""Projection exacte et soustractive de la télémétrie INVEST-STALL du 04/11.

Aucun fixture historique n'est réécrit. Supprime seulement les blocs et les
fragments du diagnostic passif pour pouvoir appliquer ensuite la projection
de la révision de quais et vérifier son hash d'origine.
"""


def _undo(source, new, old):
    if source.count(new) != 1:
        raise AssertionError(f"diagnostic INVEST-STALL: bloc attendu une fois, vu {source.count(new)}: {new[:75]!r}")
    return source.replace(new, old, 1)


def off_source(name, source):
    # RAIL-LOOP (04/11) est la couche la plus recente : la retirer d'abord
    # garde toutes les empreintes historiques sans les reecrire.
    from revue_rail_t2_off import off_source as revue_t2_off
    source = revue_t2_off(name, source)
    from rail_keep_off import off_source as rail_keep_off
    source = rail_keep_off(name, source)
    from rail_fill_off import off_source as rail_fill_off
    source = rail_fill_off(name, source)
    from rail_loop_off import off_source as rail_loop_off
    source = rail_loop_off(name, source)
    if name == "invest_stall_fleet.nut":
        marker = "/* INVEST-STALL diagnostic seul : pas de nouvel etat décisionnel."
        if marker not in source:
            if "OpexInvestStallPlatformDiagnostic(owner, line)" in source:
                raise AssertionError("diagnostic INVEST-STALL: fonctions manquantes")
            return source
        if source.count(marker) != 1:
            raise AssertionError("diagnostic INVEST-STALL: fonctions dupliquées")
        first = source.index(marker)
        following = "/* Une distance exploitable, une offre mesurable"
        end = source.index(following, first)
        source = source[:first] + source[end:]
        source = _undo(source,
            "    if (DECISION_LOG) OpexInvestStallPlatformDiagnostic(owner, line);\n", "")
        source = _undo(source,
            '        + " monthly_gain=" + best.margin.monthly + " cash=" + OpexAvailableCapital()\n'
            '        + " txn=" + line.lineId + "_" + best.vehicle + "_" + now);',
            '        + " monthly_gain=" + best.margin.monthly + " cash=" + OpexAvailableCapital());')
        source = _undo(source,
            "    investStall = true, traceStart = now\n", "    investStall = true\n")
        source = _undo(source,
            '      + " production=" + best.gap.production + " capacity_month=" + best.gap.capacity\n'
            '      + " txn=" + OpexInvestStallTraceId(state.pending));',
            '      + " production=" + best.gap.production + " capacity_month=" + best.gap.capacity);')
        return source

    if name == "task_v284.nut":
        marker = "OpexInvestStallRecheckDiagnostic(owner, line, pending,"
        if marker not in source:
            if "OpexInvestStallTraceId(pending)" in source:
                raise AssertionError("diagnostic INVEST-STALL: recheck absent")
            return source
        source = _undo(source,
            '        + " capacity=" + AIVehicle.GetCapacity(newVehicle, line.cargo)\n'
            '        + " txn=" + OpexInvestStallTraceId(pending));',
            '        + " capacity=" + AIVehicle.GetCapacity(newVehicle, line.cargo));')
        source = _undo(source,
            '    OpexInvestStallFleetLog("skip", pending.lineId, "reason=" + reason\n'
            '        + " txn=" + OpexInvestStallTraceId(pending));',
            '    OpexInvestStallFleetLog("skip", pending.lineId, "reason=" + reason);')
        source = _undo(source,
            '    if (("investStall" in pending) && pending.investStall)\n'
            '      OpexInvestStallFleetLog("rolled_back", pending.lineId,\n'
            '          "kind=wagon txn=" + OpexInvestStallTraceId(pending));\n',
            "")
        source = _undo(source,
            '        OpexInvestStallFleetLog("skip", pending.lineId,\n'
            '            "reason=approach_timeout txn=" + OpexInvestStallTraceId(pending)\n'
            '            + " elapsed_days=" + (AIDate.GetCurrentDate()\n'
            '                - (("traceStart" in pending) ? pending.traceStart : AIDate.GetCurrentDate()))\n'
            '            + " cargo_load=" + (line == null ? -1\n'
            '                : AIVehicle.GetCargoLoad(oldVehicle, line.cargo))\n'
            '            + " depot_distance=" + (line == null ? -1\n'
            '                : AIMap.DistanceManhattan(AIVehicle.GetLocation(oldVehicle), line.depot)));',
            '        OpexInvestStallFleetLog("skip", pending.lineId, "reason=approach_timeout");')
        source = _undo(source,
            '    if (("investStall" in pending) && pending.investStall)\n'
            '      OpexInvestStallFleetLog("approach", pending.lineId,\n'
            '          "kind=wagon txn=" + OpexInvestStallTraceId(pending)\n'
            '          + " elapsed_days=" + (AIDate.GetCurrentDate()\n'
            '              - (("traceStart" in pending) ? pending.traceStart : AIDate.GetCurrentDate())));\n',
            "")
        source = _undo(source,
            '        OpexInvestStallFleetLog("skip", pending.lineId, "reason=depot_timeout"\n'
            '            + " txn=" + OpexInvestStallTraceId(pending));',
            '        OpexInvestStallFleetLog("skip", pending.lineId, "reason=depot_timeout");')
        source = _undo(source,
            '  if (investStall)\n'
            '    OpexInvestStallFleetLog("depot", pending.lineId,\n'
            '        "kind=wagon txn=" + OpexInvestStallTraceId(pending)\n'
            '        + " elapsed_days=" + (AIDate.GetCurrentDate()\n'
            '            - (("traceStart" in pending) ? pending.traceStart : AIDate.GetCurrentDate())));\n',
            "")
        source = _undo(source,
            '      if (DECISION_LOG) OpexInvestStallRecheckDiagnostic(owner, line, pending,\n'
            '          oldVehicle, wagon, gap, margin, homogeneous, waitingNow);\n',
            "")
        if "OpexInvestStallRecheckDiagnostic(" in source or "OpexInvestStallTraceId(pending)" in source:
            raise AssertionError("diagnostic INVEST-STALL: résidu ou diagnostic dupliqué")
        return source

    return source
