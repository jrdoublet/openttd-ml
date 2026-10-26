"""N75-MC, P6 and P3 isolation: remove ONLY the exact opt-in additions.

Historical inventory ceilings and PO01C byte hashes must continue to cover
the same 58 legacy settings and the exact original bytes. Never rebaseline.
"""

import hashlib


INFO_DELTA = (
    b'    AddSetting({ name = "n75_multi_cargo",\n'
    b'      description = "1972+ cash-idle rail refill: 0=off, 1=shadow, 2=one extra freight cargo on empty funded rail pool (default 2)",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 2, medium_value = 2, hard_value = 2, custom_value = 2,\n'
    b'      flags = 0 });\n'
)
SETTINGS_DELTA = (
    b'  local n75MultiCargo = AIController.GetSetting("n75_multi_cargo");\n'
    b'  N75_MULTI_CARGO = (n75MultiCargo >= 1 && n75MultiCargo <= 2) ? n75MultiCargo : 0;\n'
    b'  N75_MC_LAST_MONTH = (N75_MULTI_CARGO > 0) ? N75_MC_SAVED_MONTH : -1;\n'
    b'  N75_MC_SAVED_MONTH = -1;\n'
)

# P6 is an independent, opt-in experiment. Its three source additions are
# deliberately removed from the PO01D byte snapshot without changing the
# historical SHA or concealing changes elsewhere in these source files.
P6_INFO_DELTA = (
    b'    AddSetting({ name = "p6_air_firstline_window",\n'
    b'      description = "P6 experimental first AIR line: 0=immediate historical build (default), 1=wait for at most one additional catalog publication (32 ticks / 160000 scan opcodes) when two affordable distinct AIR pairs are already selected",\n'
    b'      min_value = 0, max_value = 1,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = AICONFIG_BOOLEAN });\n'
)
P6_SETTINGS_DELTA = (
    b'  P6_AIR_FIRSTLINE_WINDOW = AIController.GetSetting("p6_air_firstline_window");\n'
)
P6_MAIN_DELTA = (
    b'  /* P6 : l\'attente est consommee une fois, y compris apres Save/Load. */\n'
    b'  _p6FirstlineWindowConsumed = false;\n'
    b'  _p6FirstlineWindow = null;\n'
)
P6_DELTAS = {
    "info.nut": P6_INFO_DELTA,
    "settings.nut": P6_SETTINGS_DELTA,
    "main.nut": P6_MAIN_DELTA,
}

# P3 default-OFF is a separate worktree behavioral experiment. Historical
# byte snapshots retain their original hashes, not a new P3-derived baseline.
P3_INFO_DELTA = (
    b'    AddSetting({ name = "air_fleet_yield_rightsize",\n'
    b'      description = "P3 mature AIR 2->3+ reinforcement: 0=off (default), 1=C117 shadow, 2=conservative low-yield veto",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });\n'
)
P3_SETTINGS_DELTA = (
    b'  local p3AirFleetYield = AIController.GetSetting("air_fleet_yield_rightsize");\n'
    b'  P3_AIR_FLEET_YIELD = (p3AirFleetYield == 1 || p3AirFleetYield == 2) ? p3AirFleetYield : 0;\n'
    b'  P3_AIR_FLEET_WINDOWS = {};\n'
)
P3_DELTAS = {"info.nut": P3_INFO_DELTA, "settings.nut": P3_SETTINGS_DELTA}

# FRONT-PAX-2 is an independent default-OFF option. Subtract its exact bytes
# from frozen legacy inventories without altering any historical hash.
FP2_INFO_DELTA = (
    b'    AddSetting({ name = "front_pax2_bounded_overlap",\n'
    b'      description = "FRONT-PAX-2 AIR PASS only: 0=historical (default), 1=passive bounded shortlist, 2=up to one additional C121 candidate per arm per completed ALL-band scan",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });\n'
)
FP2_SETTINGS_DELTA = (
    b'  local fp2Overlap = AIController.GetSetting("front_pax2_bounded_overlap");\n'
    b'  FRONT_PAX2_BOUNDED_OVERLAP = (fp2Overlap == 1 || fp2Overlap == 2) ? fp2Overlap : 0;\n'
)
FP2_DELTAS = {"info.nut": FP2_INFO_DELTA, "settings.nut": FP2_SETTINGS_DELTA}

# P2 is an opt-in, default-OFF rank experiment. Its exact settings bytes are
# excluded from the frozen historic inventory; all prior digests stay fixed.
P2_INFO_DELTA = (
    b'    AddSetting({ name = "rail_cargo_opportunity_rank",\n'
    b'      description = "P2 prepared RAIL freight opportunity: 0=historical (default), 1=passive top-K shadow, 2=one adjacent same-C77-tier promotion (8% score, 93% fund, 80% profit)",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });\n'
)
P2_SETTINGS_DELTA = (
    b'  local p2Opportunity = AIController.GetSetting("rail_cargo_opportunity_rank");\n'
    b'  P2_RAIL_CARGO_OPPORTUNITY_RANK = (p2Opportunity == 1 || p2Opportunity == 2) ? p2Opportunity : 0;\n'
    b'  P2_OPPORTUNITY_STAMP = 0;\n'
)
P2_DELTAS = {"info.nut": P2_INFO_DELTA, "settings.nut": P2_SETTINGS_DELTA}

# P1 is an independent opt-in C121 rail experiment; retain the frozen
# historical contract by subtracting ONLY its exact additions. In particular,
# P1's auxiliary freight candidate must never rebaseline PO01D's rail scan.
P1_INFO_DELTA = (
    b'    AddSetting({ name = "rail_long_value_rank",\n'
    b'      description = "P1: C121/C80 one-train freight 160-300 beyond railMax; 0=off (default), 1=passive proxy shadow, 2=one physically prepared long option",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });\n'
)
P1_SETTINGS_DELTA = (
    b'  local p1LongRank = AIController.GetSetting("rail_long_value_rank");\n'
    b'  P1_RAIL_LONG_VALUE_RANK = (p1LongRank == 1 || p1LongRank == 2) ? p1LongRank : 0;\n'
)
P1_DELTAS = {"info.nut": P1_INFO_DELTA, "settings.nut": P1_SETTINGS_DELTA}

P1_CANDIDATES_BLOCK_START = b"/* P1 : le balayage industriel normal"
P1_CANDIDATES_BLOCK_END = b"/* Ne garder que les K meilleurs"
P1_CANDIDATES_BLOCK_SHA256 = "69db60bef45147f21364ae192cd82c961764469b7a719a0e56da49409e99879f"
P1_BUILDER_RAIL_DELTA = (
    b'  /* P1 : un trajet reel plus long peut transformer une rame en deux et activer\n'
    b'   * la recherche BLOQUANTE de seconde voie juste dessous. Ce chemin experimental\n'
    b'   * abandonne avant cet A* et conserve l\'unique recherche segmentee C80. */\n'
    b'  if (("p1Long" in candidate) && candidate.p1Long) {\n'
    b'    if (candidate.trains != 1 || OpexV190Active()) {\n'
    b'      plan.reason = "P1FLEET";\n'
    b'      return plan;\n'
    b'    }\n'
    b'    if (candidate.profitAnnual < 25000 || candidate.roi < 150) {\n'
    b'      plan.reason = "P1VALUE";\n'
    b'      return plan;\n'
    b'    }\n'
    b'  }\n\n'
)
P1_CANDIDATES_EDITS = (
    (
        b'function OpexFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null, targetKind = null, targetId = -1, p1LongState = null)\n',
        b'function OpexFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null, targetKind = null, targetId = -1)\n',
    ),
    (
        b'        /* P1 : les paires hors railMax ne doivent pas evincer les courtes du TopK\n'
        b'         * papier. En shadow les stats historiques restent identiques. */\n'
        b'        if (p1LongState != null && monthly > 0\n'
        b'            && OpexP1LongOffer(p1LongState, catalog, cargo, source, industries[di],\n'
        b'                               monthly, isTransformer)) {\n'
        b'          stats.distanceLong++;\n'
        b'          continue;\n'
        b'        }\n',
        b'',
    ),
    (
        b'function OpexBuildCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, paxProfile = null, paxCandidateProfile = null, paxCruiseCache = null, freightCruiseCache = null, generatePax = true, generateFreight = true, paxBand = PAX_BAND_ALL, freightCargo = null, targetKind = null, targetId = -1, p1LongState = null)\n',
        b'function OpexBuildCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, paxProfile = null, paxCandidateProfile = null, paxCruiseCache = null, freightCruiseCache = null, generatePax = true, generateFreight = true, paxBand = PAX_BAND_ALL, freightCargo = null, targetKind = null, targetId = -1)\n',
    ),
    (
        b'                          freightCargo, targetKind, targetId, p1LongState);\n',
        b'                          freightCargo, targetKind, targetId);\n',
    ),
    (
        b'  /* P1 : l\'economie n\'est calculee qu\'APRES le scan, pour l\'unique meilleur\n'
        b'   * proxy. Le candidat reste hors `all` et hors `best` jusqu\'a la preuve C80. */\n'
        b'  if (p1LongState != null && p1LongState.best != null) {\n'
        b'    if (P1_RAIL_LONG_VALUE_RANK == 2)\n'
        b'      p1LongState.candidate = OpexP1LongEvaluate(catalog, p1LongState, stats);\n'
        b'    if (DECISION_LOG) OpexDecide("P1_LONG_SHADOW", "mode=" + P1_RAIL_LONG_VALUE_RANK\n'
        b'        + " count=" + p1LongState.observed + " cargo=" + p1LongState.best.cargo\n'
        b'        + " src=" + p1LongState.best.src + " dst=" + p1LongState.best.dst\n'
        b'        + " dist=" + p1LongState.best.distance\n'
        b'        + " candidate=" + (p1LongState.candidate != null ? 1 : 0));\n'
        b'  }\n\n',
        b'',
    ),
)

# The two PO01D-frozen producer files gained FP2 helpers and guarded call
# sites. Verify the precise independent helper contents and delete ONLY those
# additions for historical byte-hash checks. Never change the frozen digests.
FP2_PLANNING_BLOCK_START = b"/* FRONT-PAX-2 : un seul dossier"
FP2_PLANNING_BLOCK_END = b"/* 1. Preparation"
FP2_PLANNING_BLOCK_SHA256 = "065bb2d87059671e152c71e2d62818e551eb14fd72990bedf69770bdd145396c"
FP2_CANDIDATES_BLOCK_START = b"/* FRONT-PAX-2 : comparaison CINEMATIQUE"
FP2_CANDIDATES_BLOCK_END = b"function OpexComputeAirMaxDistance"
FP2_CANDIDATES_BLOCK_SHA256 = "cd0257813fb12f5982c074b27c0fcb21b6dd6340d902a63c824b08d75606e8ab"
FP2_PLANNING_INSERTS = (
    b'        if (ctx.fp2 != null) OpexFP2Shortlist(ctx, 0, sites[a], sites[b],\n'
    b'            airport, plane, distance, flightDistance, orderDistance, minDist);\n',
    b'        if (ctx.fp2 != null) OpexFP2Shortlist(ctx, 1, hub, site,\n'
    b'            airport, plane, distance, flightDistance, orderDistance, 20);\n',
    b'        if (ctx.fp2 != null) OpexFP2Shortlist(ctx, 2, hub1, hub2,\n'
    b'            airport, plane, distance, flightDistance, orderDistance, 20);\n',
    b'  /* Mutating evaluation is restricted to ON and to the completed scan.\n'
    b'   * Shadow reports only the selected references and arithmetic shortlist. */\n'
    b'  if (ctx.fp2 != null) OpexFP2Finalize(ctx);\n'
    b'  if (ctx.fp2 != null && ctx.sliced\n'
    b'      && ("frontPax2Bounded" in ctx.resumeState))\n'
    b'    delete ctx.resumeState.frontPax2Bounded;\n',
    b'    fp2 = null,\n',
    b'  if (FRONT_PAX2_BOUNDED_OVERLAP > 0 && paxBand == PAX_BAND_ALL\n'
    b'      && catalog != null && catalog.bounds != null) {\n'
    b'    if (resumeState != null && ("frontPax2Bounded" in resumeState)) {\n'
    b'      ctx.fp2 = resumeState.frontPax2Bounded;\n'
    b'    } else {\n'
    b'      ctx.fp2 = OpexFP2NewShortlist(catalog.bounds);\n'
    b'      if (resumeState != null) resumeState.frontPax2Bounded <- ctx.fp2;\n'
    b'    }\n'
    b'  }\n\n',
)


def _strip_fp2_block(raw, name, begin, end, digest):
    assert raw.count(begin) == 1, f"FP2 {name}: missing or repeated helper start"
    assert raw.count(end) == 1, f"FP2 {name}: missing or repeated original next function"
    start_at = raw.index(begin)
    end_at = raw.index(end, start_at)
    block = raw[start_at:end_at]
    assert hashlib.sha256(block).hexdigest() == digest, (
        f"FP2 {name}: helper changed; review and update its independent digest"
    )
    return raw[:start_at] + raw[end_at:]

# P3 adds one standalone helper block and exactly two guarded call sites to
# C117's existing lean path. Extract by unique function boundaries, verify the
# independent P3 block hash, then subtract only these additions before checking
# the frozen PO01D hash. A changed historical source remains an error.
P3_PROBES_BLOCK_PREFIX = b"/* P3 : cette signature n'est calculee que pour shadow/ON"
P3_PROBES_BLOCK_END = b"function OpexC117FlushLine(line, state)"
P3_PROBES_BLOCK_SHA256 = "a42b7b5002fb57e5c73c5fd291d7b6840d236cccf390e9b82fab96c6e1ae0215"
P3_PROBES_CALLS = (
    b'    if (P3_AIR_FLEET_YIELD > 0) OpexP3MatureFlush(line, state);\n',
    b'    if (P3_AIR_FLEET_YIELD > 0)\n'
    b'      OpexP3MatureSample(line, state, ageDays, live, mixedEngine);\n',
)

# V303 est un ajout indépendant opt-in, défini APRES les empreintes historiques
# PO01D/N75/P1. Ces fragments sont retirés de la vue historique sans jamais
# recalculer les SHA du témoin. L'extraction du helper est elle-même gelée.
V303_INFO_BEGIN = b'    AddSetting({\n      name = "v303_reverse_probe_sliced",\n'
V303_INFO_END = b'    AddSetting({\n      name = "v294_rail_weight_pct",\n'
V303_SETTINGS = (
    b'  local v303Sliced = AIController.GetSetting("v303_reverse_probe_sliced");\n'
    b'  V303_REVERSE_PROBE_SLICED = (v303Sliced == 1 || v303Sliced == 2) ? v303Sliced : 0;\n'
)
V303_MAIN = b'  function _v303BeginForwardAfterProbe(state);\n'
V303_ORCHESTRATOR_NEW = (
    b'  if (ai._railSearch == null || (ai._railSearch.phase != "search"\n'
    b'      && ai._railSearch.phase != "reverse")) {\n'
)
V303_ORCHESTRATOR_OLD = (
    b'  if (ai._railSearch == null || ai._railSearch.phase != "search") {\n'
)
V303_BUILDER_BEGIN = b'/* V303 : reprendre le MEME pathfinder inverse'
V303_BUILDER_END = b"/* Une tranche d'A*. `spent` est le cumul"
V303_BUILDER_SHA256 = 'e5f65dbc01247dbd0bc1af93183380ce7f4aa224f5e6abd018f240a9eedfd8c1'


def _strip_v303(name, raw):
    if name == 'info.nut':
        assert raw.count(V303_INFO_BEGIN) == 1 and raw.count(V303_INFO_END) == 1
        start = raw.index(V303_INFO_BEGIN)
        end = raw.index(V303_INFO_END, start)
        block = raw[start:end]
        assert block.count(b'AddSetting(') == 1 and block.endswith(b'    });\n')
        assert b'easy_value = 0, medium_value = 0, hard_value = 0,' in block
        assert b'custom_value = 0, default_value = 0,' in block
        return raw[:start] + raw[end:]
    if name == 'settings.nut':
        assert raw.count(V303_SETTINGS) == 1
        return raw.replace(V303_SETTINGS, b'', 1)
    if name == 'main.nut':
        assert raw.count(V303_MAIN) == 1
        return raw.replace(V303_MAIN, b'', 1)
    if name == 'orchestrator.nut':
        assert raw.count(V303_ORCHESTRATOR_NEW) == 1
        return raw.replace(V303_ORCHESTRATOR_NEW, V303_ORCHESTRATOR_OLD, 1)
    if name == 'builder_rail.nut':
        assert raw.count(V303_BUILDER_BEGIN) == 1 and raw.count(V303_BUILDER_END) == 1
        start = raw.index(V303_BUILDER_BEGIN)
        end = raw.index(V303_BUILDER_END, start)
        block = raw[start:end]
        assert hashlib.sha256(block).hexdigest() == V303_BUILDER_SHA256, 'V303 helper changed'
        return raw[:start] + raw[end:]
    return raw


def historical_bytes(name, raw):
    raw = _strip_v303(name, raw)
    delta = {"info.nut": INFO_DELTA, "settings.nut": SETTINGS_DELTA}.get(name)
    if delta is not None:
        assert raw.count(delta) == 1, f"N75-MC {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(delta, b"", 1)
    p6_delta = P6_DELTAS.get(name)
    if p6_delta is not None:
        assert raw.count(p6_delta) == 1, f"P6 {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(p6_delta, b"", 1)
    p3_delta = P3_DELTAS.get(name)
    if p3_delta is not None:
        assert raw.count(p3_delta) == 1, f"P3 {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(p3_delta, b"", 1)
    fp2_delta = FP2_DELTAS.get(name)
    if fp2_delta is not None:
        assert raw.count(fp2_delta) == 1, f"FP2 {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(fp2_delta, b"", 1)
    p2_delta = P2_DELTAS.get(name)
    if p2_delta is not None:
        assert raw.count(p2_delta) == 1, f"P2 {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(p2_delta, b"", 1)
    p1_delta = P1_DELTAS.get(name)
    if p1_delta is not None:
        assert raw.count(p1_delta) == 1, f"P1 {name}: expected one unchanged opt-in fragment"
        raw = raw.replace(p1_delta, b"", 1)
    if name == "builder_rail.nut":
        assert raw.count(P1_BUILDER_RAIL_DELTA) == 1, "P1 builder: safety guard changed or duplicated"
        raw = raw.replace(P1_BUILDER_RAIL_DELTA, b"", 1)
    if name == "air_planning.nut":
        raw = _strip_fp2_block(
            raw, name, FP2_PLANNING_BLOCK_START, FP2_PLANNING_BLOCK_END,
            FP2_PLANNING_BLOCK_SHA256,
        )
        for insert in FP2_PLANNING_INSERTS:
            assert raw.count(insert) == 1, f"FP2 {name}: guarded call changed or duplicated"
            raw = raw.replace(insert, b"", 1)
    if name == "candidates.nut":
        raw = _strip_fp2_block(raw, name, P1_CANDIDATES_BLOCK_START,
                               P1_CANDIDATES_BLOCK_END, P1_CANDIDATES_BLOCK_SHA256)
        for addition, original in P1_CANDIDATES_EDITS:
            assert raw.count(addition) == 1, "P1 candidates: addition changed or duplicated"
            raw = raw.replace(addition, original, 1)
        raw = _strip_fp2_block(
            raw, name, FP2_CANDIDATES_BLOCK_START, FP2_CANDIDATES_BLOCK_END,
            FP2_CANDIDATES_BLOCK_SHA256,
        )
    if name == "probes.nut":
        assert raw.count(P3_PROBES_BLOCK_PREFIX) == 1, "P3 probes helper begin must be unique"
        assert raw.count(P3_PROBES_BLOCK_END) == 1, "P3 probes helper end must be unique"
        begin = raw.index(P3_PROBES_BLOCK_PREFIX)
        end = raw.index(P3_PROBES_BLOCK_END, begin)
        block = raw[begin:end]
        assert hashlib.sha256(block).hexdigest() == P3_PROBES_BLOCK_SHA256, (
            "P3 probes helper changed: inspect and review its independent hash"
        )
        raw = raw[:begin] + raw[end:]
        for insertion in P3_PROBES_CALLS:
            assert raw.count(insertion) == 1, "P3 C117 call changed or duplicated"
            raw = raw.replace(insertion, b"", 1)
    return raw


def historical_info(info):
    return historical_bytes("info.nut", info.encode("utf-8")).decode("utf-8")
