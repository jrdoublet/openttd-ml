"""Reviewed strict OFF projection for opt-in RAIL-OPEN.

The frozen comparator is the RAIL-SIBLING 40x5 bundle. It excludes
concurrent RAIL-CONSIST additions, which must survive this projection.
Never regenerate the fixture implicitly during tests.
"""

import copy
import hashlib
import json
from pathlib import Path

HISTORICAL_FIXTURE = json.loads((Path(__file__).parent / "fixtures/rail_open_off.json")
                                .read_text(encoding="utf-8"))

# ROAD+RAIL merge snapshot: the historical RAIL-OPEN fixture still describes
# the policy, but three large contextual hunks intersect later RAIL-REPAIR and
# changed public defaults.  These exact source hashes authorize the in-memory
# merge view; the historical JSON (and old-source projection path) stays frozen.
_MERGE_SHA = {
    "builder_rail.nut": (
        "1eca9310d6a3451820e5c61d721ce531a4b274213e043cfc9efef0075d9ee72e",
    ),
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
        "21be34e223d17916dae003fc4f979c9d54c48dbe5526b54a95351bda5e32592c",
        "7ae9ad7cde04ceb382314f9d1ccab05125c52fab4cb22defd177dbfd35023fd6",
        # PO-02 fleet slot, outside the RAIL-OPEN span.
        "1d37b1b21b174e2005eeb3d33ae6aa3312371fde101576bf010750a3dac3abc2",
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
        "7d66bea32e0aef3155036049d87a49aba2748f95bd3e3efda6a75fe5df067ccd",
        "6332a1c7f17f8b7054b4a0846149c57b8ecae4cd8b145c62b92ad255a4bdf27a",
    ),
}


def _merge_span(source, first, following):
    if source.count(first) != 1 or source.count(following) != 1:
        raise AssertionError("RAIL-OPEN merge: nonunique reviewed span")
    start = source.index(first)
    end = source.index(following, start)
    return source[start:end]


def _merge_replace(source, old, new):
    if source.count(old) != 1:
        raise AssertionError("RAIL-OPEN merge: altered reviewed replacement")
    return source.replace(old, new, 1)


def _merge_fixture():
    root = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
    current = {name: (root / name).read_text(encoding="utf-8") for name in _MERGE_SHA}
    if any(hashlib.sha256(current[name].encode("utf-8")).hexdigest() not in shas
           for name, shas in _MERGE_SHA.items()):
        return HISTORICAL_FIXTURE
    result = copy.deepcopy(HISTORICAL_FIXTURE)
    builder = current["builder_rail.nut"]
    a = _merge_span(builder, "      local jointPlansA = railOpenCooldown ? []",
                    "      joinHasA = jointPlansA.len() > 0;")
    a_old = _merge_replace(a,
        "      local jointPlansA = railOpenCooldown ? []\n"
        "          : OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsA);\n",
        "      local jointPlansA = OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsA);\n")
    a_old = _merge_replace(a_old, "!railOpenCooldown && RAIL_REPAIR_JOIN_SITE", "RAIL_REPAIR_JOIN_SITE")
    a_old = _merge_replace(a_old,
        "      if (railOpenSibling && jointPlansA.len() == 0 && !railOpenCooldown)\n"
        "        jointPlansA = OpexRailOpenSiblingSpreadPlans(candidate, statsA);\n", "")

    b = _merge_span(builder, "          if (DECISION_LOG && railOpenSibling)",
                    "      joinHasB = jointPlansB.len() > 0;")
    b_old = _merge_replace(b, _merge_span(b, "          if (DECISION_LOG && railOpenSibling)",
                                         "          return { plansA = jointPlansA"), "")
    b_old = _merge_replace(b_old,
        "      local jointPlansB = railOpenCooldown ? []\n"
        "          : OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsB);\n",
        "      local jointPlansB = OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsB);\n")
    b_old = _merge_replace(b_old, "!railOpenCooldown && RAIL_REPAIR_JOIN_SITE", "RAIL_REPAIR_JOIN_SITE")
    b_old = _merge_replace(b_old,
        'if (((' + '"convergent_dest" in candidate) && candidate.convergent_dest == 1) || railOpenB)',
        'if (("convergent_dest" in candidate) && candidate.convergent_dest == 1)')
    b_old = _merge_replace(b_old,
        "          if (!railOpenCooldown) {\n"
        "            jointPlansB = OpexV264SpreadJoinPlans(candidate.joinPlatform, candidate.joinStationId, statsB);\n"
        "            joinMode = \"spread\";\n"
        "          } else {\n"
        "            joinMode = \"cooldown\";\n"
        "          }\n",
        "          jointPlansB = OpexV264SpreadJoinPlans(candidate.joinPlatform, candidate.joinStationId, statsB);\n"
        "          joinMode = \"spread\";\n")

    c = _merge_span(builder, "          if (DECISION_LOG && railOpenB)",
                    "\n  /* Chercher les DEUX extremites")
    c_old = _merge_replace(c, _merge_span(c, "          if (DECISION_LOG && railOpenB)",
                                         "          return { plansA = plansA"), "")
    c_old = _merge_replace(c_old, _merge_span(c_old, "    if (railOpenJoin) {",
                                             "    if (strictOriginReuseJoin) {"), "")
    c_old = _merge_replace(c_old, _merge_span(c_old, "      local railOpenFallback = railOpenJoin",
                                             "        return { plansA = null"),
                           "      if (EB2_NEW_STATION_FALLBACK == 0) {\n")
    c_old = _merge_replace(c_old, _merge_span(c_old, "      if (DECISION_LOG && railOpenFallback) {",
                                             '        OpexDecide("EB2_FALLBACK"'),
                           "      if (DECISION_LOG) {\n")
    for i, new, old in ((2, a, a_old), (3, b, b_old), (4, c, c_old)):
        result["files"]["builder_rail.nut"][i] = {"new": new, "old": old}

    globals_pre = current["globals_pre.nut"]
    result["files"]["globals_pre.nut"][0] = {
        "new": _merge_span(globals_pre,
            "/* RAIL-OPEN : defaut 1 dans info.nut ; initialisation avant chargement a 0. */",
            "/* RAIL-PAIR : second train"), "old": "",
    }
    info = current["info.nut"]
    result["files"]["info.nut"][0] = {
        "new": _merge_span(info, '    AddSetting({ name = "rail_open",',
                           '    AddSetting({ name = "rail_pair",'), "old": "",
    }
    return result


FIXTURE = _merge_fixture()
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
    if FIXTURE is not HISTORICAL_FIXTURE and name in _MERGE_SHA:
        historical = HISTORICAL_FIXTURE["files"][name]
        if all(source.count(edit["new"]) == 1 for edit in historical):
            edits = historical
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
