"""Diagnostic RED: selected PO01C copied branches versus current live policy.

Only source tokens and small, explicit decision tables are checked. These fixtures
model the named guards with all other filters satisfied; they do not execute
Squirrel, resolve missing globals, or prove side effects, suspension safety,
opcode costs, or full equivalence. C83/V133/V134 scenarios with retired flags
enabled are *hypothetical*; the current symbols are no longer defined. A V233
joinContext is not passed by the current PAX caller, so the obsolete V233 branch
is a source hazard rather than a demonstrated reachable production branch. V269
extends *freight*, while the only copied MakePaxCandidate caller requests pax;
the missing V269 tokens are therefore also not a demonstrated PAX divergence.

Intentional FAILs are diagnostic witnesses, not tests to fix by rebaselining.
"""

from dataclasses import dataclass
from pathlib import Path
import re

from po01c_generate import function


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def body(file_name, function_name):
    text = (AI / file_name).read_text(encoding="utf-8")
    return re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", function(text, function_name))


LIVE_FIND = body("air_planning.nut", "OpexAirPlansFindSites")
COPY_FIND = body("po01c_generators.nut", "OpexPO01CAirPlansFindSites")
LIVE_HUB = body("air_planning.nut", "OpexAirPlansDiscoverHubs")
COPY_HUB = body("po01c_generators.nut", "OpexPO01CAirPlansDiscoverHubs")
LIVE_PAX = body("candidates.nut", "OpexMakeCandidate")
COPY_PAX = body("po01c_generators.nut", "OpexPO01CMakePaxCandidate")
LIVE_FREIGHT_CAP = body("candidates.nut", "OpexRailFreightMaxDistance")


@dataclass(frozen=True)
class AirState:
    # Remaining filters (level, station capacity, population, site existence) pass.
    served: bool = False
    own_second_slot: bool = False
    target_rank: int = -1
    current_rank: int = 0
    retired_c83_enabled: bool = False
    quarantined: bool = False
    retired_v133_enabled: bool = False
    v134_eligible: bool = False
    retired_v134_enabled: bool = False
    repair_combo: bool = False


def air_outcome(source, state, *, hub=False):
    """Evaluate only branches whose exact source guards are detected below."""
    if hub and "!ctx.c83RepairCombo && sites.len()" in source and state.repair_combo:
        return "hub_pool_not_scanned"
    if ("C83_FIXES && targetTownId >= 0" in source
            and state.retired_c83_enabled and state.target_rank >= 0
            and state.current_rank > state.target_rank):
        return "outside_truncated_scan"
    if ("V133_AIR_BUILD_RETRY && OpexV133AirTownSkip" in source
            and state.retired_v133_enabled and state.quarantined):
        return "quarantined_skip"
    if state.served and not state.own_second_slot:
        if (not hub and "skipServed = !v134Eligible" in source
                and "V134_AIR_P2P_SATURATED_HUB && isServed" in source
                and state.retired_v134_enabled and state.v134_eligible):
            return "search_site"
        return "served_skip"
    return "search_site"


@dataclass(frozen=True)
class PaxState:
    distance: int
    normal_max: int = 200
    normal_min: int = 5
    long_freight_cap: int = 0


def pax_distance_outcome(source, state):
    """The kind='pax' arm uses railMin/railMax and ignores V269 freight caps."""
    assert "if (kind == \"pax\")" in source
    assert "distance < bounds.railMin" in source
    assert "distance > bounds.railMax" in source
    if state.distance < state.normal_min:
        return "reject_distance_short"
    if state.distance > state.normal_max:
        return "reject_distance_long"
    return "admit_distance"


def test_source_anchors_for_decision_tables():
    """PASS: changing source guard shapes must invalidate this limited oracle."""
    assert "local skipServed = isServed && !c83OwnSecondSlot;" in LIVE_FIND
    assert "if (isServed && !c83OwnSecondSlot) continue;" in LIVE_HUB
    assert "if (isServed && !c83OwnSecondSlot) skipServed = !v134Eligible;" in COPY_FIND
    assert "!ctx.c83RepairCombo && sites.len()" in COPY_HUB
    assert "OpexC83RepairFindSites(ctx, comboIndex, combo, airport, plane)" in COPY_FIND
    assert "V133_AIR_BUILD_RETRY && OpexV133AirTownSkip" in COPY_FIND
    assert "V133_AIR_BUILD_RETRY && OpexV133AirTownSkip" in COPY_HUB
    assert "V269_RAIL_LONG_MAX > 0" in LIVE_PAX
    assert "OpexRailFreightMaxDistance(catalog, bounds, cargo)" in LIVE_PAX
    assert "v269FreightCap" in LIVE_FREIGHT_CAP


def test_shared_control_states_agree():
    """PASS: ordinary unserved AIR and in-range pax remain useful controls."""
    base = AirState()
    for live, copied in ((LIVE_FIND, COPY_FIND), (LIVE_HUB, COPY_HUB)):
        assert air_outcome(live, base, hub=(live == LIVE_HUB)) == "search_site"
        assert air_outcome(copied, base, hub=(live == LIVE_HUB)) == "search_site"
    near = PaxState(distance=180)
    assert pax_distance_outcome(LIVE_PAX, near) == pax_distance_outcome(COPY_PAX, near)
    assert pax_distance_outcome(LIVE_PAX, near) == "admit_distance"


def test_find_sites_c83_v133_v134_branch_parity():
    """FAIL: retained historical predicates alter the modeled site scan."""
    cases = {
        "C83 target scan cut": AirState(target_rank=0, current_rank=2, retired_c83_enabled=True),
        "V133 quarantine": AirState(quarantined=True, retired_v133_enabled=True),
        "V134 served reentry": AirState(served=True, retired_v134_enabled=True, v134_eligible=True),
    }
    discrepancies = {name: (air_outcome(LIVE_FIND, state), air_outcome(COPY_FIND, state))
                     for name, state in cases.items()
                     if air_outcome(LIVE_FIND, state) != air_outcome(COPY_FIND, state)}
    assert not discrepancies, f"source-guard model differs: {discrepancies}"


def test_discover_hubs_c83_v133_branch_parity():
    """FAIL: copied hub repair skip and quarantined-town guard are obsolete."""
    cases = {
        "C83 repair combo": AirState(repair_combo=True),
        "V133 hub quarantine": AirState(quarantined=True, retired_v133_enabled=True),
    }
    discrepancies = {name: (air_outcome(LIVE_HUB, state, hub=True),
                             air_outcome(COPY_HUB, state, hub=True))
                     for name, state in cases.items()
                     if air_outcome(LIVE_HUB, state, hub=True) != air_outcome(COPY_HUB, state, hub=True)}
    assert not discrepancies, f"source-guard model differs: {discrepancies}"


def test_make_pax_candidate_v269_freight_cap_is_not_reachable():
    """PASS: the one copied caller says pax; even freight cap 380 cannot admit 320."""
    producer = body("po01c_generators.nut", "OpexPO01CPaxCandidates")
    calls = re.findall(r"OpexPO01CMakePaxCandidate\(po01dBox[^;]+;", producer)
    assert len(calls) == 1
    assert ', "pax", cargo,' in calls[0]
    assert "if (kind == \"pax\")" in LIVE_PAX and "if (kind == \"pax\")" in COPY_PAX
    case = PaxState(distance=320, normal_max=200, long_freight_cap=380)
    assert pax_distance_outcome(LIVE_PAX, case) == "reject_distance_long"
    assert pax_distance_outcome(COPY_PAX, case) == "reject_distance_long"


def test_retired_policy_symbols_absent_from_copies():
    """FAIL: references solely in stale copies; V233 joinContext is caller-unreachable."""
    retired = {
        "OpexC83RepairFindSites": (LIVE_FIND, COPY_FIND),
        "C83_FIXES": (LIVE_FIND, COPY_FIND),
        "V133_AIR_BUILD_RETRY": (LIVE_FIND, COPY_FIND),
        "V134_AIR_P2P_SATURATED_HUB": (LIVE_FIND, COPY_FIND),
        "V133_AIR_BUILD_RETRY (hub)": (LIVE_HUB, COPY_HUB),
        "V177_RAIL_PAX_MIN_DIST": (LIVE_PAX, COPY_PAX),
        "V182_RAIL_FREIGHT_MIN_DIST": (LIVE_PAX, COPY_PAX),
        "V195_V182_YEARS": (LIVE_PAX, COPY_PAX),
        "V233_GOODS_GRAFT": (LIVE_PAX, COPY_PAX),
    }
    obsolete = []
    for name, (live, copied) in retired.items():
        token = name.split(" (")[0]
        assert not re.search(r"\b" + token + r"\b", live), token
        if re.search(r"\b" + token + r"\b", copied):
            obsolete.append(name)
    # The only current call has no joinContext argument; do not claim V233 executes.
    pax_producer = body("po01c_generators.nut", "OpexPO01CPaxCandidates")
    assert re.search(r"OpexPO01CMakePaxCandidate\([^;]*cruiseCache, secondary\)",
                     pax_producer)
    assert obsolete == [], f"orphan symbols only in copied policy: {obsolete}"
