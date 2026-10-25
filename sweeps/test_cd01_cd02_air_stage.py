"""CD01/CD02: source contracts and deterministic site->pair execution trace.

The HEAD a09a7b2 business implementations remain untouched. This test ties
the moved execution blocks to existing AC02/AC03 continuation fixtures.
It is NOT a Squirrel VM opcode/economic parity measurement.
"""

from pathlib import Path
import unittest

try:
    from sweeps.test_ac02_air_site_resume import (
        SiteState, sorted_towns, step as site_step,
    )
    from sweeps.test_ac03_air_new_pairs_resume import Cursor, step as pairs_step
except ModuleNotFoundError:
    from test_ac02_air_site_resume import SiteState, sorted_towns, step as site_step
    from test_ac03_air_new_pairs_resume import Cursor, step as pairs_step


AIR = (Path(__file__).resolve().parents[1] /
       "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")


def function(name):
    start = AIR.index("function " + name + "(")
    brace = AIR.index("{", start)
    depth = 0
    for i in range(brace, len(AIR)):
        depth += (AIR[i] == "{") - (AIR[i] == "}")
        if depth == 0:
            return AIR[start:i + 1]
    raise AssertionError(name)


class StageMachine:
    """Frozen substep boundaries; quotas count visits, never VM opcodes."""

    def __init__(self, towns, target=None, v93=True):
        self.towns = sorted_towns(towns, target=target, dirty_order=False)
        self.target = target
        self.v93 = v93
        self.site_cursor = SiteState()
        self.pair_cursor = Cursor()
        self.phase = "sites"
        self.trace = []

    def tick(self, site_budget, pair_budget):
        if self.phase == "sites":
            finished = site_step(self.site_cursor, self.towns, len(self.towns),
                                 site_budget, target=self.target,
                                 kind="large", v93=self.v93)
            self.trace.append("sites_done" if finished else "sites_yield")
            if not finished:
                return False
            self.phase = "new_pairs"
        if self.phase == "new_pairs":
            finished = pairs_step(
                self.pair_cursor, self.site_cursor.sites, self.target,
                pair_budget, lambda a, b: 1 + (a + b) % 3,
                lambda a, b: (a + b) % 2 == 0)
            self.trace.append("pairs_done" if finished else "pairs_yield")
            if finished:
                self.phase = "hubs"
            return finished
        return True

    def run(self, site_budget, pair_budget):
        for _ in range(500):
            if self.tick(site_budget, pair_budget):
                return self
        raise AssertionError("substeps did not terminate")


class CD01CD02StageContracts(unittest.TestCase):
    def test_continuations_produce_same_site_and_pair_output(self):
        towns = [
            {"id": 4, "pop": 1900, "found": True, "valid": True},
            {"id": 8, "pop": 1500, "found": True, "valid": True},
            {"id": 7, "pop": 1700, "found": True, "valid": False},
            {"id": 1, "pop": 580, "found": True, "valid": True},
            {"id": 9, "pop": 2300, "found": True, "valid": True},
        ]
        for target in (None, 4, 8, 999):
            for v93 in (True, False):
                reference = StageMachine(towns, target, v93).run(100, 100)
                for budget_sites in (1, 2, 3, 4, 9):
                    for budget_pairs in (1, 2, 3, 4, 9):
                        with self.subTest(target=target, v93=v93, site=budget_sites,
                                          pair=budget_pairs):
                            actual = StageMachine(towns, target, v93).run(
                                budget_sites, budget_pairs)
                            self.assertEqual(actual.phase, "hubs")
                            self.assertEqual(actual.site_cursor.sites, reference.site_cursor.sites)
                            self.assertEqual(actual.pair_cursor.visited, reference.pair_cursor.visited)
                            self.assertEqual(actual.pair_cursor.admitted, reference.pair_cursor.admitted)
                            self.assertEqual(actual.pair_cursor.total_ops, reference.pair_cursor.total_ops)
                            self.assertEqual(actual.trace.count("sites_done"), 1)
                            self.assertEqual(actual.trace.count("pairs_done"), 1)
                            self.assertEqual(len(actual.pair_cursor.visited),
                                             len(set(actual.pair_cursor.visited)))
                            self.assertFalse("pairs_yield" in actual.trace[
                                :actual.trace.index("sites_done")])


if __name__ == "__main__":
    unittest.main()
