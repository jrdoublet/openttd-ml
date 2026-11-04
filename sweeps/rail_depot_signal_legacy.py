"""Strict, frozen pre-RAIL-DEPOT-SIGNAL source projection.

The fixture was reviewed against six SHA-256 hashes recorded in the working
tree before implementing this opt-in. Never update hashes from live code in a
test: another concurrent workstream must be reconciled explicitly.
"""

import hashlib
import json
from pathlib import Path

FIXTURE = json.loads((Path(__file__).parent / "fixtures/rail_depot_signal_off.json").read_text(encoding="utf-8"))


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
    """Strict historical projection, including the frozen pre-intervention SHA."""
    projected = strip_if_present(name, source)
    if name in FIXTURE["baseline_sha256"]:
        actual = hashlib.sha256(projected.encode("utf-8")).hexdigest()
        if actual != FIXTURE["baseline_sha256"][name]:
            raise AssertionError(f"RAIL-DEPOT-SIGNAL {name}: pre-intervention bytes changed")
    return projected


def off_sha256(name, source):
    return hashlib.sha256(off_source(name, source).encode("utf-8")).hexdigest()
