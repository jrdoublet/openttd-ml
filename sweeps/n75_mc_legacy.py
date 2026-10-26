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


def historical_bytes(name, raw):
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
