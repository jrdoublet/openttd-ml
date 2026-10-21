"""V307 1.8 : contrats des sites de gare disperses par octant.

La transcription Python de la selection controle l'ordre et les quotas independamment
des journaux OpenTTD, sans lancer Docker.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import unittest

from sweeps.diag_v307_sites import parse_logs, summarise


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(file):
    return (AI / file).read_text(encoding="utf-8")


def octant(dx, dy):
    """Transcription de OpexV307Octant, axes E, SE, S, SW, W, NW, N, NE."""
    if dx == 0 and dy == 0:
        return -1
    ax, ay = abs(dx), abs(dy)
    if ax > 2 * ay:
        return 0 if dx > 0 else 4
    if ay > 2 * ax:
        return 2 if dy > 0 else 6
    if dx > 0:
        return 1 if dy > 0 else 7
    return 3 if dy > 0 else 5


def octant_round_robin(candidates, total=12, per_octant=3):
    """Candidates = (x, y, distance, admissible), sorted near-first per octant."""
    buckets = {i: [] for i in range(8)}
    for x, y, dist, admissible in candidates:
        if admissible:
            side = octant(x, y)
            if side >= 0:
                buckets[side].append((dist, x, y))
    for side in buckets:
        buckets[side].sort()
    selected = []
    depth = 0
    while len(selected) < total and depth < per_octant:
        any_remaining = False
        for side in range(8):
            if depth < len(buckets[side]):
                any_remaining = True
                selected.append((side, buckets[side][depth]))
                if len(selected) == total:
                    break
        if not any_remaining:
            break
        depth += 1
    return selected


class TestV307Sites(unittest.TestCase):
    def test_octant_axes_and_diagonals(self):
        self.assertEqual([octant(*xy) for xy in
                          [(4, 0), (3, 3), (0, 4), (-3, 3), (-4, 0),
                           (-3, -3), (0, -4), (3, -3)]], list(range(8)))
        self.assertEqual(octant(0, 0), -1)

    def test_round_robin_prefers_spread_and_nearest(self):
        # Two opposite octants supply many closer plans; they cannot evict other octants.
        points = [(3 + i, 0, i + 1, True) for i in range(10)]
        points += [(0, 3 + i, i + 2, True) for i in range(10)]
        points += [(-3 - i, 0, i + 3, True) for i in range(10)]
        points += [(0, -3 - i, i + 4, True) for i in range(10)]
        selected = octant_round_robin(points)
        counts = Counter(side for side, _ in selected)
        self.assertEqual(len(selected), 12)
        self.assertTrue(all(n <= 3 for n in counts.values()))
        self.assertEqual(set(counts), {0, 2, 4, 6})
        for side, count in counts.items():
            depths = [value[0] for s, value in selected if s == side]
            self.assertEqual(depths, sorted(depths))

    def test_option_off_on_all_difficulties(self):
        info = source("info.nut")
        setting = re.search(r'name = "v307_sites",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(setting)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf'{level}_value\s*=\s*0\b')
        self.assertEqual(source("settings.nut").count('GetSetting("v307_sites")'), 1)
        self.assertIn("V307_SITES <- 0;", source("globals_pre.nut"))

    def test_native_industry_tile_sources_and_octant_caps(self):
        rail = source("builder_rail.nut")
        self.assertIn("AITileList_IndustryAccepting", rail)
        self.assertIn("AITileList_IndustryProducing", rail)
        self.assertIn("OpexV307SiteOctant", rail)
        self.assertIn("V307S_PLANS", rail)
        self.assertIn("OpexOpsClock()", rail)
        self.assertIn("OpexStationPlans", rail)
        self.assertNotIn(".find(", rail)

    def test_reader_empty_probe_preserves_unknown_ops(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "reference_seed42_r0.log"
            file.write_text("[0] [I] OPEX 1971-1-2 RAIL_ATTEMPT kind=freight reason=ABND\n",
                            encoding="utf-8")
            report = summarise(parse_logs([file]))
        self.assertEqual(report["reference"]["reasons"]["ABND"], 1)
        self.assertEqual(report["reference"]["sites"], 0)
        self.assertIsNone(report["reference"]["real_profit"])


if __name__ == "__main__":
    unittest.main()
