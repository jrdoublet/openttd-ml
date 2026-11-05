"""Strict, frozen pre-RAIL-DEPOT-SIGNAL source projection.

The fixture was reviewed against six SHA-256 hashes recorded in the working
tree before implementing this opt-in. Never update hashes from live code in a
test: another concurrent workstream must be reconciled explicitly.
"""

import hashlib
import json
from pathlib import Path

FIXTURE = json.loads((Path(__file__).parent / "fixtures/rail_depot_signal_off.json").read_text(encoding="utf-8"))

# Fully reviewed ROAD+RAIL merge identities.  Keys are the actual source SHA
# passed to the RDS projector and values the actual RDS-OFF output SHA.  A
# second pair covers the legacy caller's SEARCH-PRIO/config-OFF intermediate.
# Do not substitute this mapping for the frozen 2026-11-03 witness or accept
# marker-only/partial sources: both digests must match and all fixture hunks
# still pass through strip_if_present() exactly once.
_REVIEWED_MERGE_RDS_SHA = {
    "info.nut": {
        "0e6e6e30aaae1b814dc8afbaad515347e2dc05aea133cd12983a7abc1fce26f1":
            "7ecad3705f8f51a0d94f24dbe5f2910e64af30c95d0f5be0b2021839b38b0034",
        "86d67cac63199b4a1ab267acb533513b1f2ab5391558988351eba0e7efc261aa":
            "ebb95bf341a59e795c542dc3502d7105f2f9f3413daabd753467230d4dc97ffc",
    },
    "globals_pre.nut": {
        "d0548c85cd11d62de13e4eb1566088d77a15ab6490b3a30a01fb27eda3110424":
            "63ba8781c969351ea8e1fb4c23e28255396edaac1cd65e3d94795c8388704d7e",
        "c6861e400454c652fcf150e9148be6d96d6bf7c370df15009bfedf9732bd90e9":
            "42d7708dc890be6adbf5936c4879075ece39a030a777318edcaaa77b719a86d0",
    },
    "settings.nut": {
        "32542fef11a2bad6fbc7716a4e07a52758e7a2e358af172d2b43c3ee4a0a59fc":
            "ed8abeac1738973e81eef42873962d7b7208e78178b826cfd37078e18bd890f9",
        "12ff68193bd638c2f4eb5139151fe872bb05fb163bda1a299610e3481ae1e2e3":
            "1dadbfebb825771eec820582830227c6b2d29580c2eed6f392517f731d5eb02f",
    },
    "builder_rail.nut": {
        "1eca9310d6a3451820e5c61d721ce531a4b274213e043cfc9efef0075d9ee72e":
            "c3939d214c5694811a25e77b9e060f165f6f2053f0dbd15e17cc9177a38608d1",
        "d15392a7b32964ba6463f9688d090f09142c4fafb796fa76ebb512a282c57798":
            "c3939d214c5694811a25e77b9e060f165f6f2053f0dbd15e17cc9177a38608d1",
    },
    "task_rail.nut": {
        "3d9356a9cd53cef9f75c706b1b01feeee59b7fcb791ab5f8873424e734bb12d4":
            "5947d55fb58ac59dce355db30a1b18ff2de4a5ab9827484f4d986d10bdd1ac81",
        "c5c724ea850647ca4ab882d9976eddc496ffcd298d7608183349f46d9e4dc11e":
            "61573b0524a2d40a4f30b93f9b6c2740059b8a58ba943b75aceb85e64bf3eaa0",
    },
    "main.nut": {
        "c02c66b30ce9bee501d4b593dbf98f1c26e7bbdd50addf393ebd344c90d63762":
            "808d2932b97804cfc64293317bc370cfe1175af63f11f68f474aabb428bc060a",
        "f7bd47b6f2f93e006c83a9d06fb7af22983540ae9a62a14c16fa497ddf217231":
            "808d2932b97804cfc64293317bc370cfe1175af63f11f68f474aabb428bc060a",
    },
}


def _sha(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def strip_if_present(name, source):
    """Projection reusable by older projectors, including on already-projected text."""
    if name in ("globals_pre.nut", "settings.nut", "info.nut", "main.nut", "scheduler.nut", "persist.nut",
                "task_rail.nut", "orchestrator.nut", "candidates.nut", "po01c_generators.nut",
                "lines.nut", "builder_rail.nut", "task_v284.nut") and (
        "INVEST_STALL" in source or "invest_stall" in source or "investStall" in source
    ):
        from invest_stall_source_off import project_off as invest_stall_off
        source = invest_stall_off(name, source)
    from rail_long_source_off import off_source as rail_long_off
    source = rail_long_off(name, source)
    from v190_fix_directional_legacy import off_source as directional_off
    source = directional_off(name, source)
    if name == "builder_rail.nut":
        # Extra guarded rollback hook is specific to RDS and must disappear OFF.
        rollback_hook = "  if (RAIL_DEPOT_SIGNAL && depot != null && OpexRailDepotSignalRollbackTracked(depot)) depot = null;\n"
        if source.count(rollback_hook) > 1:
            raise AssertionError("RAIL-DEPOT-SIGNAL duplicated rollback hook")
        source = source.replace(rollback_hook, "")
        upgrade_guard = (
            "  /* Supprimer OpexPlaceJoinSignals seulement quand RDS dispose d'une branche\n"
            "   * PBS CERTIFIEE. En fallback depot historique, conserver les signaux du\n"
            "   * constructeur OFF, faute de quoi le repli n'est pas physiquement equivalent. */\n"
            "  local signals = RAIL_DEPOT_SIGNAL && OpexRailDepotSignalSpurRoutingCertified()\n"
            "      ? { ok = 3, fail = 0, skip = 0, junc = 1, failures = [] }\n"
            "      : OpexPlaceJoinSignals(planA2, planB2, tiles2, depot2);\n"
        )
        if source.count(upgrade_guard) > 1:
            raise AssertionError("RAIL-DEPOT-SIGNAL duplicated upgrade signal guard")
        source = source.replace(upgrade_guard,
                                "  local signals = OpexPlaceJoinSignals(planA2, planB2, tiles2, depot2);\n")
        # Opt-in RDS v2 passes the REAL platform length. Normalize only these
        # exact argument extensions to the already-frozen v1 RDS hunks.
        # Historical SHA, "old" bytes and the immutable fixture stay untouched.
        extensions = (
            ("OpexRailDepotSignalBuildPrimary(tiles, null, candidate.platformLength)",
             "OpexRailDepotSignalBuildPrimary(tiles)"),
            ("OpexRailDepotSignalBuildPrimary(tiles2, null, candidate.platformLength)",
             "OpexRailDepotSignalBuildPrimary(tiles2)"),
            ("OpexRailDepotSignalBuildPrimary(tiles, forbiddenDepot1, candidate.platformLength)",
             "OpexRailDepotSignalBuildPrimary(tiles, forbiddenDepot1)"),
            ("OpexRailDepotSignalBuildPrimary(tiles2, forbiddenD, candidate.platformLength)",
             "OpexRailDepotSignalBuildPrimary(tiles2, forbiddenD)"),
            ("OpexRailDepotSignalBuildPrimary(tiles2, prep.forbidden, line.platformLength)",
             "OpexRailDepotSignalBuildPrimary(tiles2, prep.forbidden)"),
            ("OpexRailDepotSignalBuildNear(tiles2, true, depot2, prep.forbidden, line.platformLength)",
             "OpexRailDepotSignalBuildNear(tiles2, true, depot2, prep.forbidden)"),
        )
        for current, original in extensions:
            if source.count(current) > 1:
                raise AssertionError(f"RAIL-DEPOT-SIGNAL duplicated train-length hunk: {current}")
            if current in source and original in source:
                raise AssertionError(f"RAIL-DEPOT-SIGNAL mixed train-length hunk: {current}")
            source = source.replace(current, original)
    edits = FIXTURE["files"].get(name, [])
    if not edits:
        return source
    active = [source.count(edit["new"]) == edit["count"] for edit in edits]
    if not any(active):
        # One-fragment options still have recognisable signatures if corrupted.
        signatures = {
            "info.nut": ('name = "rail_depot_signal"',),
            "globals_pre.nut": ("RAIL_DEPOT_SIGNAL <-",),
            "settings.nut": ('GetSetting("rail_depot_signal")',),
            "main.nut": ('require("rail_depot_signal.nut")',),
            "builder_rail.nut": ("OpexRailDepotSignalEnhance", "RAIL_DEPOT_SIGNAL ?"),
            "task_rail.nut": ("builtLine.depotEndB", "RAIL_DEPOT_SIGNAL &&"),
        }
        if any(sig in source for sig in signatures.get(name, ())):
            raise AssertionError(f"RAIL-DEPOT-SIGNAL unknown changed hunk in {name}")
        return source
    if not all(active):
        raise AssertionError(f"RAIL-DEPOT-SIGNAL partial modified hunk in {name}")
    for edit in reversed(edits):
        if source.count(edit["new"]) != edit["count"]:
            raise AssertionError(f"RAIL-DEPOT-SIGNAL changed hunk in {name}")
        source = source.replace(edit["new"], edit["old"], edit["count"])
    return source


def off_source(name, source):
    """Strict source OFF projection; preserve historic and merged identities."""
    original_sha = _sha(source)
    reviewed = _REVIEWED_MERGE_RDS_SHA.get(name, {})
    if original_sha in reviewed.values():
        # Already projected full-file bytes; no other policy may be reapplied
        # on a stale OFF source, nor may a similar-looking partial file pass.
        return source
    projected = strip_if_present(name, source)
    if name in FIXTURE["baseline_sha256"]:
        actual = _sha(projected)
        if actual != FIXTURE["baseline_sha256"][name] and reviewed.get(original_sha) != actual:
            raise AssertionError(f"RAIL-DEPOT-SIGNAL {name}: pre-intervention bytes changed")
    return projected


def off_sha256(name, source):
    """Return the legacy witness SHA for an exactly reviewed merge input.

    On a merged input this is the SHA of the *frozen pre-RDS branch witness*,
    NOT a claim that its augmented ROAD+RAIL bytes equal that old file.  Use
    hashlib.sha256(off_source(...).encode()) to measure the actual merge bytes.
    Older callers use this API specifically to validate historic identity.
    """
    projected = off_source(name, source)
    actual = _sha(projected)
    if _REVIEWED_MERGE_RDS_SHA.get(name, {}).get(_sha(source)) == actual:
        return FIXTURE["baseline_sha256"][name]
    return actual
