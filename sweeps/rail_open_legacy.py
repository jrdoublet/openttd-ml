"""Reviewed strict OFF projection for opt-in RAIL-OPEN.

The frozen comparator is the RAIL-SIBLING 40x5 bundle. It excludes
concurrent RAIL-CONSIST additions, which must survive this projection.
Never regenerate the fixture implicitly during tests.
"""

import json
from pathlib import Path

FIXTURE = json.loads((Path(__file__).parent / "fixtures/rail_open_off.json")
                     .read_text(encoding="utf-8"))
SIGNATURES = {
    "builder_rail.nut": ("RAIL_OPEN_JOIN_FAILURES", "OpexRailOpenNewStationFunded"),
    "candidates.nut": ("function OpexRailOpenCashReady(", "RAIL_OPEN_REJECT"),
    "globals_pre.nut": ("RAIL_OPEN <-",),
    "info.nut": ('name = "rail_open"',),
    "po01c_generators.nut": ("RAIL_OPEN_REJECT",),
    "settings.nut": ('GetSetting("rail_open")',),
}


def off_source(name, source):
    """Remove exactly RAIL-OPEN while preserving sibling and unrelated work."""
    if name in ("builder_rail.nut", "candidates.nut", "po01c_generators.nut", "lines.nut", "task_v284.nut") and (
        "INVEST_STALL" in source or "investStall" in source
    ):
        from invest_stall_source_off import project_off as invest_stall_off
        source = invest_stall_off(name, source)
    from rail_pair_legacy import off_source as rail_pair_off
    source = rail_pair_off(name, source)
    edits = FIXTURE["files"].get(name)
    if edits is None:
        return source
    states = []
    for i, edit in enumerate(edits):
        n = source.count(edit["new"])
        if n > 1:
            raise AssertionError(f"RAIL-OPEN {name} hunk {i}: nonunique anchor")
        states.append(n == 1)
    if any(states) and not all(states):
        raise AssertionError(f"RAIL-OPEN {name}: partially modified opt-in")
    if not any(states):
        if any(marker in source for marker in SIGNATURES.get(name, ())):
            raise AssertionError(f"RAIL-OPEN {name}: changed source hunk")
        return source
    for edit in reversed(edits):
        source = source.replace(edit["new"], edit["old"], 1)
    return source


def off_bytes(name, raw):
    return off_source(name, raw.decode("utf-8")).encode("utf-8")
