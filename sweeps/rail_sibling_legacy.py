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
    "globals_pre.nut": "b616affff691e3d6b04063c44c0b901aca09c71ab33a155c94aad72a103935a0",
    "info.nut": "6e65c6b45d05ef02b6598d1b92fbf38f4b4f8fc246a840f57712d9419ca21532",
}


def _merge_fixture():
    root = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
    current = {name: (root / name).read_text(encoding="utf-8") for name in _MERGE_SHA}
    if any(hashlib.sha256(current[name].encode("utf-8")).hexdigest() != sha
           for name, sha in _MERGE_SHA.items()):
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
