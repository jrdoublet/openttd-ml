"""N75-MC isolation: remove ONLY the known opt-in setting additions.

Historical inventory ceilings and PO01C byte hashes must continue to cover
the same 58 legacy settings and the exact original bytes. Never rebaseline.
"""


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


# air_site_funnel stays opt-in at 0. Stripping these fragments restores the
# frozen info/settings/air_sites bytes. Do not rebaseline the SHA table.
AIR_FUNNEL_INFO_DELTA = (
    b'    AddSetting({\n'
    b'      name = "air_site_funnel",\n'
    b'      description = "Airport site search: 0 = current ring spiral (default), 1 = same spiral with a native footprint predicate",\n'
    b'      min_value = 0, max_value = 1,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0,\n'
    b'      custom_value = 0, flags = 0, step_size = 1\n'
    b'    });\n'
)
AIR_FUNNEL_SETTINGS_DELTA = (
    b'  local airSiteFunnel = AIController.GetSetting("air_site_funnel");\n'
    b'  AIR_SITE_FUNNEL = (airSiteFunnel == 1) ? 1 : 0;\n'
    b'  if (AIR_SITE_FUNNEL > 0) OpexAirFunnelInstall();\n'
)
AIR_SITE_C96_HEAD_NEW = (
    b"  if (best == null) return;\n"
    b"  local ops = -1;\n"
    b"  if (AIR_SITE_OPS_MARK != null) ops = OpexOpsMeasureEnd(AIR_SITE_OPS_MARK);\n"
    b"  local firstDist = OpexAirDistanceToRect(town.tile, firstAnchor, airport.width, airport.height);\n"
)
AIR_SITE_C96_HEAD_OLD = (
    b"  if (best == null) return;\n"
    b"  local firstDist = OpexAirDistanceToRect(town.tile, firstAnchor, airport.width, airport.height);\n"
)
AIR_SITE_C96_TAIL_NEW = b'      + " best_ring=" + bestRing + " probes=" + used + " ops=" + ops);\n'
AIR_SITE_C96_TAIL_OLD = b'      + " best_ring=" + bestRing + " probes=" + used);\n'

# Telemetrie AIR_SITE_SEARCH sur les deux lignes AIR_PLAN_PERF. Le gel
# po01d reste le fichier sans ces deux champs.
AIR_PLAN_PERF_DECIDE_NEW = (
    b'               + " plans=" + (projects != null ? projects.len() : (bestPlan != null ? 1 : 0))\n'
    b'               + " site_search_ops=" + AIR_SITE_SEARCH_OPS\n'
    b'               + " site_search_calls=" + AIR_SITE_SEARCH_CALLS);\n'
)
AIR_PLAN_PERF_DECIDE_OLD = (
    b'               + " plans=" + (projects != null ? projects.len() : (bestPlan != null ? 1 : 0)));\n'
)
AIR_PLAN_PERF_LOG_NEW = (
    b'             + " c121_endpoint_misses=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.endpointMisses : 0)\n'
    b'             + " site_search_ops=" + AIR_SITE_SEARCH_OPS\n'
    b'             + " site_search_calls=" + AIR_SITE_SEARCH_CALLS);\n'
)
AIR_PLAN_PERF_LOG_OLD = (
    b'             + " c121_endpoint_misses=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.endpointMisses : 0));\n'
)


def _strip_once(raw, name, delta, replacement=b""):
    assert raw.count(delta) == 1, f"{name}: expected precisely one unchanged opt-in fragment"
    return raw.replace(delta, replacement, 1)


def historical_bytes(name, raw):
    if name == "air_sites.nut":
        raw = _strip_once(raw, name, AIR_SITE_C96_HEAD_NEW, AIR_SITE_C96_HEAD_OLD)
        return _strip_once(raw, name, AIR_SITE_C96_TAIL_NEW, AIR_SITE_C96_TAIL_OLD)
    if name == "air_planning.nut":
        raw = _strip_once(raw, name, AIR_PLAN_PERF_DECIDE_NEW, AIR_PLAN_PERF_DECIDE_OLD)
        return _strip_once(raw, name, AIR_PLAN_PERF_LOG_NEW, AIR_PLAN_PERF_LOG_OLD)
    deltas = {
        "info.nut": (INFO_DELTA, AIR_FUNNEL_INFO_DELTA),
        "settings.nut": (SETTINGS_DELTA, AIR_FUNNEL_SETTINGS_DELTA),
    }.get(name)
    if deltas is None:
        return raw
    for delta in deltas:
        raw = _strip_once(raw, name, delta)
    return raw


def historical_info(info):
    return historical_bytes("info.nut", info.encode("utf-8")).decode("utf-8")
