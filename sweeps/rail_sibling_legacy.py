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
        "06d784ef3eb2826b7ede17b488f46bb92ddcab9e433fed3af68077a2de1d9d4f",
        "15a280f6fdd072baaec3b8673d5e353b87cfa6533ca9506b4ff635c174b492a9",
        "f6945c1dabf0ce9d09a33e34d27aa0e29d4d9d89fc263d0510d9db849d5d055b",
        "b239d48d284d3241eafe76c7803938924e6f9398e34de658e47c3217a235632f",
        "8e6a25b11f83cbff9005b50043c886c960f4655ad8e406271506a620a306c9f6",
        "ce6ca4ff83cb27399557b443fe6453f9d66799f9ce38b190febdc574e6850ea7",
        "bef4ff20d7d24d7dcb89589871c293e776233f5a0e947f36a5ad08aef36e8738",
        "ebec56a6b0bb226f6b50a5a42ad3da51be89872324a75c63a2853e35feea665b",
    ),
    "info.nut": (
        "0e6e6e30aaae1b814dc8afbaad515347e2dc05aea133cd12983a7abc1fce26f1",
        "3e2fda7483d4cd0bc4d0937d3a5dc8e2450640c0e7935b74bcf184ac10992dc9",
        "9bd1c94dd11441204f2ab2ed4471a72a826ff00a5e417776e975f60c89d3f9a3",
        "57f790a6d211835b18331ec573f65806b9c0f7d967aaeeda8dfcdb6ee6364717",
        "2cd70817628b7a33a1116c4384c812bc0634d69b88ad2f0394349fa25e74e84e",
        "605f36dfea83f44e461d9518e900eaf9b78c1762590ee5d4400fa67da8d153cf",
        "daf834ee9d61a4790976237bb40800da44eb372df78b6f893cafe1da57ff117c",
        "65852a5588e3346d1158ebedca15bdd557e91ba8c376f1e08b06d60cda690cee",
        "2e5508b92c2a095868a12eca413f2927b20d11e621397692b154f8282e241863",
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
