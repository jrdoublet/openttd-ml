"""Contrat de retrait — rail_cached_proximity_gate (defaut 0, porte A 40x5 fail_primary).

Au defaut la garde renvoyait toujours vrai (X || false = X sur le retour
immediat ; X && false = false sur le filtre de reselection et le compteur
d'audit). Le precontrole de chantier OpexAI::_tooClose reste la source de
verite. Save/Load ne portait pas ce reglage.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start : pos + 1]
    raise AssertionError(f"corps non ferme: {signature}")


class RailCachedProximityGateRemoved(unittest.TestCase):
    def test_setting_global_and_loader_are_gone(self):
        self.assertNotIn('name = "rail_cached_proximity_gate"', source("info.nut"))
        self.assertNotIn("RAIL_CACHED_PROXIMITY_GATE", source("globals_pre.nut"))
        self.assertNotIn("rail_cached_proximity_gate", source("settings.nut"))
        self.assertNotIn("RAIL_CACHED_PROXIMITY_GATE", source("settings.nut"))
        for path in AI.glob("*.nut"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("rail_cached_proximity_gate", text, path.name)
            self.assertNotIn("RAIL_CACHED_PROXIMITY_GATE", text, path.name)
            self.assertNotIn("OpexRailCachedProximity", text, path.name)
            self.assertNotIn("RAIL_CACHE_PROXIMITY", text, path.name)

    def test_cached_helpers_and_inactive_branches_are_gone(self):
        generation = source("projects_generation.nut")
        selection = source("projects_selection.nut")
        update = source("projects_update.nut")
        self.assertNotIn("function OpexRailCachedProximity(", generation)
        self.assertNotIn("function OpexRailCachedProximityKeep(", generation)
        self.assertNotIn("OpexRailCachedProximityKeep(", generation)
        self.assertNotIn("OpexRailCachedProximityKeep(", selection)
        self.assertNotIn("OpexRailCachedProximity(", update)
        self.assertNotIn("proximityDroppedPax", selection)
        self.assertNotIn("proximityDroppedPax", update)

    def test_revalidation_keeps_both_served_rejection_only(self):
        generation = source("projects_generation.nut")
        historical = function_body(generation, "function OpexCandidateStillValid(")
        indexed = function_body(generation, "function OpexCandidateStillValidIndexed(")
        hist_rail = historical[historical.index('if (mode == "rail")'):]
        idx_rail = indexed[indexed.index('if (mode == "rail")'):]
        self.assertIn(
            "if (OpexOriginServed(lines, p.src, false) && OpexOriginServed(lines, p.dst, false))",
            hist_rail,
        )
        self.assertIn(
            "if ((p.src in ctx.servedRailOnly) && (p.dst in ctx.servedRailOnly))",
            idx_rail,
        )
        self.assertNotIn("OpexRailCachedProximityKeep", hist_rail)
        self.assertNotIn("OpexRailCachedProximityKeep", idx_rail)
        self.assertIn("return true;", hist_rail)
        self.assertIn("return true;", idx_rail)

    def test_build_precheck_stays_and_audit_drops_stay_zero(self):
        build = function_body(source("lines.nut"), "function OpexAI::_tooClose(candidate)")
        for invariant in (
            '("joinLineId" in candidate) ? candidate.joinLineId : -1',
            "line.lineId == joinLineId",
            "AIMap.DistanceManhattan(entry[1], originTile)",
            "OpexRememberClosest(d, ORIGIN_SEPARATION, originA)",
            "OpexRememberClosest(d, ORIGIN_SEPARATION, originB)",
            "originA >= 0 && originB >= 0",
            "OpexLineStationId(line, lineEnd)",
            "AIMap.DistanceManhattan(entry[1], stationTile)",
            "OpexRememberClosest(d, MIN_SEPARATION, blocking)",
            "return { hard = -1, blocking = blocking };",
        ):
            self.assertIn(invariant, build)
        self.assertIn(
            'OpexRailPortfolioAudit("reselect", alternatives, funded,\n      capitalBudget, 0, 0);',
            source("projects_selection.nut"),
        )
        self.assertIn(
            'OpexRailPortfolioAudit("incremental", alternatives, funded,\n      capitalBudget, 0, 0);',
            source("projects_update.nut"),
        )
        persist = source("persist.nut")
        self.assertNotIn("rail_cached_proximity_gate", persist)
        self.assertNotIn("RAIL_CACHED_PROXIMITY_GATE", persist)


if __name__ == "__main__":
    unittest.main()
