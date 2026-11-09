"""Exact, idempotent OFF projection for the RAIL-SIBLING lot-1 additions.

The reviewed fixture is a fixed copy of the opt-in hunks, not a fresh Git diff.
Never update historical byte hashes to accommodate a new OFF-by-default feature.
"""

import copy
import hashlib
import json
from pathlib import Path


HISTORICAL_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/rail_sibling_lot1_off.json").read_text(encoding="utf-8")
)

# The 2026-11-05 union promotes RAIL-SIBLING to default 1.  Its two setting
# hunks therefore differ from the frozen default-0 experiment, even though
# the policy itself is otherwise identical.  Export a reviewed, SHA-bounded
# in-memory view for callers inspecting FIXTURE; do not rewrite the JSON or
# silently allow modified partial settings.
_MERGE_SHA = {
    "globals_pre.nut": (
        "d0548c85cd11d62de13e4eb1566088d77a15ab6490b3a30a01fb27eda3110424",
        "14092ce902f853a19d77980467627b727cf6e32e9d4bc094c8a9145e296bdac9",
        "f914642ec34f9347436c1b4cfbebfc7eecd8ae38940dae65af12bdd7dde6dc46",
        "14e4b9b83ebee2b2b51d60fdfad0a572bf8cd5bdd04befe832b48649084a0c6e",
        "441a9528e465b0390dc985a322db92f8f8d78991e744fb196f275d798aef8015",
        "9f7a522edbfe2a69411113be6d0de489ab8b472fc42f5553f72955273f7ae598",
        "cdee1071263ab7b49708b74de5dd0af5281531a7b929a5a2065b89274a519d55",
        "e57223f2564507f2922c84ce2727d51dd995d18052c7a978cb4fd9235e98e8df",
        "278abdf5abda355fee630bf82967065ad8fd60e2dc10420da694c25b77532179",
    ),
    "info.nut": (
        "0e6e6e30aaae1b814dc8afbaad515347e2dc05aea133cd12983a7abc1fce26f1",
        "dea79bb97b5153aab3fe91e659451c6021ac30660846342cf1e0ae4382877613",
        "6f4107a4c5100fcfabb2d9caf8d4f204101fd6a92534b72c2a9d102da71dff11",
        "92870d608bf4a6e575c142beca2fd24783d419a75a05e1e22b6801c498633d76",
        "851ef126ab645d062200e4f9fec36db07f4860deb3cd586c3a2474c3fb354173",
        "a91f430ec17fa802db2b1fb02b6498a6dcaed31662073abff6685a63abb44342",
        "28a3871a6b6d919666429206e0c63ee396dd0e2ee0ad8694339d7350b50d343a",
        "896d4bd56a1bc78dba3d092710279c876b62d60fb4a10955708d3984a37fc3cd",
        "6097ae6ec6dba1454112a4aae6e698c611e44fc38ebff090adc0e404b04c8448",
    ),
}


def _merge_fixture():
    root = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
    current = {name: (root / name).read_text(encoding="utf-8") for name in _MERGE_SHA}
    if any(hashlib.sha256(current[name].encode("utf-8")).hexdigest() not in shas
           for name, shas in _MERGE_SHA.items()):
        return HISTORICAL_FIXTURE
    result = copy.deepcopy(HISTORICAL_FIXTURE)
    spans = {
        "globals_pre.nut": (
            "/* RAIL-SIBLING lot 1 : defaut 1 dans info.nut ; initialisation avant chargement a 0. */",
            "/* RAIL-OPEN : defaut 1",
        ),
        "info.nut": ('    AddSetting({ name = "rail_sibling",',
                     '    AddSetting({ name = "rail_open",'),
    }
    for name, (begin, end) in spans.items():
        source = current[name]
        if source.count(begin) != 1 or source.count(end) != 1:
            raise AssertionError(f"RAIL-SIBLING {name}: merge fixture anchor changed")
        i = source.index(begin)
        j = source.index(end, i)
        result["files"][name][0] = {"old": "", "new": source[i:j]}
    return result


FIXTURE = _merge_fixture()

# A partly edited opt-in must not be silently treated as already projected.
# These signatures also catch a damaged single-hunk setting or builder guard.
SIGNATURES = {
    "builder_rail.nut": ('"sibling_src"',),
    "candidates.nut": ("function OpexRailSiblingParent(", "local sibling = (RAIL_SIBLING",),
    "economy.nut": ("OpexRailSiblingApplyRevenue(candidate)",),
    "globals_pre.nut": ("RAIL_SIBLING <-",),
    "info.nut": ('name = "rail_sibling"',),
    "po01c_generators.nut": ("local sibling = (RAIL_SIBLING",),
    "settings.nut": ('GetSetting("rail_sibling")',),
}


def off_source(name, code):
    """Subtract only exact reviewed sibling hunks, retaining unrelated edits."""
    from v190_fix_legacy import off_source as v190_fix_off
    code = v190_fix_off(name, code)
    from rail_pair_legacy import off_source as rail_pair_off
    code = rail_pair_off(name, code)
    from rail_open_legacy import off_source as rail_open_off
    code = rail_open_off(name, code)
    from rail_consist_legacy import off_source as rail_consist_off
    code = rail_consist_off(name, code)
    edits = FIXTURE["files"].get(name)
    if FIXTURE is not HISTORICAL_FIXTURE and name in _MERGE_SHA:
        historical = HISTORICAL_FIXTURE["files"][name]
        if all(code.count(edit["new"]) == 1 for edit in historical):
            edits = historical
    if edits is None:
        return code
    present = []
    for index, edit in enumerate(edits):
        count = code.count(edit["new"])
        if count > 1:
            raise AssertionError(f"RAIL-SIBLING {name} hunk {index}: duplicate opt-in bytes")
        present.append(count == 1)
    if any(present) and not all(present):
        raise AssertionError(f"RAIL-SIBLING {name}: partial or modified OFF source")
    if not any(present):
        if any(marker in code for marker in SIGNATURES[name]):
            raise AssertionError(f"RAIL-SIBLING {name}: reviewed OFF fragment changed")
        return code
    for edit in reversed(edits):
        code = code.replace(edit["new"], edit["old"], 1)
    return code


def off_bytes(name, raw):
    return off_source(name, raw.decode("utf-8")).encode("utf-8")
