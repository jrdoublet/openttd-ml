"""Strict, composable OFF source projection for the RAIL-LONG behavior opt-in.

Call off_source(name, source) BEFORE older feature-specific projectors: they
freeze historical hashes that predate RAIL-LONG. No source files are changed.
"""


def _remove_once(code, fragment):
    assert code.count(fragment) == 1, f"RAIL-LONG missing/duplicated fragment: {fragment[:70]}"
    return code.replace(fragment, "", 1)


def _remove_range(code, start, following):
    assert code.count(start) == 1, f"RAIL-LONG missing/duplicated start: {start[:70]}"
    assert code.count(following) == 1, f"RAIL-LONG missing/duplicated end: {following[:70]}"
    begin = code.index(start)
    finish = code.index(following, begin)
    return code[:begin] + code[finish:]


def _off_source(name, code):
    """Remove only these frozen ON hunks; repeat calls are idempotent.

    If any of the additions is present, require the complete set for that file
    to prevent an unreviewed partial OFF projection from being accepted.
    """
    from rail_long_merged_off import already_v1_off, before_v1_double_grow
    if already_v1_off(name, code):
        return code
    code = before_v1_double_grow(name, code)
    from double_grow_off import off_source as double_grow_off
    code = double_grow_off(name, code)
    from rail_long_v2_off import off_source as v2_off
    code = v2_off(name, code)
    if name in ("builder_rail.nut", "candidates.nut", "po01c_generators.nut", "lines.nut",
                "task_v284.nut", "task_rail.nut", "orchestrator.nut") and (
        "INVEST_STALL" in code or "investStall" in code
    ):
        from invest_stall_source_off import project_off as invest_stall_off
        code = invest_stall_off(name, code)
    if name == "builder_rail.nut":
        markers = (
            "/* RAIL-LONG : l'offre doit depasser",
            "  local railLongLength = OpexRailLongSiteLength(catalog, candidate);\n",
            "  /* Chercher les DEUX extremites",
        )
        if not any(marker in code for marker in markers):
            return code
        code = _remove_range(code, markers[0], "function OpexRailSiteReason(")
        code = _remove_range(code,
            '  /* Le premier devis court est le repli physique après un A* long échoué.',
            '  local railLongLength = OpexRailLongSiteLength(catalog, candidate);')
        code = _remove_range(code,
            '  if (RAIL_LONG && candidate.kind == "freight") {\n'
            '    if (!("railLongChosen" in candidate))',
            '  local sawA = false;')
        code = _remove_once(code, markers[1])
        code = _remove_range(code, markers[2],
                             "  for (local length = wanted; length >= floor; length--) {")
        code = code.replace(
            'OpexV163CandidateSecondary(candidate), OpexV233LIs(candidate),\n'
            '                                      RAIL_LONG && ("railLongChosen" in candidate) && candidate.railLongChosen);',
            'OpexV163CandidateSecondary(candidate), OpexV233LIs(candidate));',
            1,
        )
        code = code.replace(
            'OpexV163CandidateSecondary(candidate), OpexV233LIs(candidate),\n'
            '                                        RAIL_LONG && ("railLongChosen" in candidate) && candidate.railLongChosen);',
            'OpexV163CandidateSecondary(candidate), OpexV233LIs(candidate));',
            1,
        )
    elif name == "economy.nut":
        signature = '''                           wagonOverride = null, locoChoicesOverride = null, secondary = null, longGood = false,
                           railLongFill = false)
'''
        original_signature = '''                           wagonOverride = null, locoChoicesOverride = null, secondary = null, longGood = false)
'''
        merged_signature = '''                           wagonOverride = null, locoChoicesOverride = null, secondary = null,
                           longGood = false, railLongFill = false, v233Single = false)
'''
        merged_original_signature = '''                           wagonOverride = null, locoChoicesOverride = null, secondary = null,
                           longGood = false, v233Single = false)
'''
        added = '''  if ((longModel || (kind == "pax" && OpexV207Active()) || (kind != "pax" && (V301_NOTRAIN_FIX & 2))
      || (RAIL_LONG && kind == "freight"))
'''
        original = '''  if ((longModel || (kind == "pax" && OpexV207Active()) || (kind != "pax" && (V301_NOTRAIN_FIX & 2)))
'''
        marker = "  /* RAIL-LONG : le site 6/7"
        if added not in code and marker not in code:
            return code
        # La fusion sur origin/master conserve l'argument V233L `v233Single`.
        # Retirer uniquement railLongFill : ne pas transformer le parametre
        # V233L en option de remplissage ou perdre son defaut inactif.
        if code.count(merged_signature) == 1 and code.count(signature) == 0:
            code = code.replace(merged_signature, merged_original_signature, 1)
        else:
            assert code.count(signature) == 1 and code.count(merged_signature) == 0, \
                "RAIL-LONG changed economics signature"
            code = code.replace(signature, original_signature, 1)
        assert code.count(added) == 1, "RAIL-LONG damaged freight train-length clamp"
        code = code.replace(added, original, 1)
        code = _remove_range(code, marker, "  if (correctedWagons != wagons) {")
    elif name == "task_rail.nut":
        helper = "/* RAIL-LONG : la certification V190-FIX2"
        dispatch = "          /* Sur les quais RAIL-LONG"
        if helper not in code and dispatch not in code:
            return code
        code = _remove_range(code, helper, "function OpexAI::_expandRailLines(year)")
        code = _remove_range(code,
            '    /* RAIL-LONG : un A* infructueux',
            '    local plan = OpexCompleteRailRouteAfterSearch(this._catalog, state.candidate, state.plan, slice);')
        code = _remove_once(code, '''          if (RAIL_LONG && ("railLong" in line) && line.railLong)
            backlogThreshold = line.wagons * wagon.capacity * 1.5;
''')
        code = _remove_range(code, dispatch,
                             "          /* La double voie V190-FIX a une rame PAR voie")
        code = _remove_range(code,
            '    if (RAIL_LONG && ("railLongChosen" in candidate) && candidate.railLongChosen) {',
            '    if (DECISION_LOG && OpexV190Active() && candidate.kind == "freight") {')
    return code


def off_source(name, code):
    from fleet_arb_off import off_source as fleet_off
    code = fleet_off(name, code)
    from rail_long_merged_off import already_v1_off, verify_stage
    if already_v1_off(name, code):
        return code
    result = _off_source(name, code)
    verify_stage("v1", name, code, result)
    return result
