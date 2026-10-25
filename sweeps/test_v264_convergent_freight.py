#!/usr/bin/env python3
"""V264 : fret convergent adopte en permanence vers une industrie deja desservie."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
PROTECTED = (
    "c67_terrain_map",
    "v180_",
    "v182_",
    "v177_",
    "v207_",
    "v197_",
    "v198_",
    "v199_",
    "v200_",
    "rail_geometry_",
)


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


def _spread_window(x0, y0, x1, y1, spread, length, along_x):
    """Meme bornes que OpexV264SpreadWindow (union inclusive <= spread)."""
    if along_x:
        return (
            x1 - spread + 1,
            x0 + spread - length,
            y1 - spread + 1,
            y0 + spread - 1,
        )
    return (
        x1 - spread + 1,
        x0 + spread - 1,
        y1 - spread + 1,
        y0 + spread - length,
    )


def _union_fits(x0, y0, x1, y1, ax, ay, length, along_x, spread):
    """CanExpandRailStation : largeur et hauteur de l'union inclusives <= spread."""
    if along_x:
        nx0, nx1, ny0, ny1 = ax, ax + length - 1, ay, ay
    else:
        nx0, nx1, ny0, ny1 = ax, ax, ay, ay + length - 1
    ux0, uy0 = min(x0, nx0), min(y0, ny0)
    ux1, uy1 = max(x1, nx1), max(y1, ny1)
    return (ux1 - ux0 + 1) <= spread and (uy1 - uy0 + 1) <= spread


def _in_window(win, ax, ay):
    ax0, ax1, ay0, ay1 = win
    return ax0 <= ax <= ax1 and ay0 <= ay <= ay1


def _chebyshev(ax, ay, x0, y0, x1, y1):
    dx = (x0 - ax) if ax < x0 else ((ax - x1) if ax > x1 else 0)
    dy = (y0 - ay) if ay < y0 else ((ay - y1) if ay > y1 else 0)
    return dx if dx > dy else dy


class TestV264ConvergentFreight(unittest.TestCase):
    def test_adopted_policy_is_constant_and_not_a_setting(self):
        # Politique adoptee au defaut 1 puis figee au lot 7.
        info = _read("info.nut")
        self.assertNotIn('name = "v264_convergent_freight"', info)
        self.assertIn("const V264_CONVERGENT_FREIGHT = 1;", _read("globals_pre.nut"))

    def test_removed_setting_is_not_read(self):
        settings = _read("settings.nut")
        self.assertNotIn('GetSetting("v264_convergent_freight")', settings)
        self.assertNotIn("V264_CONVERGENT_FREIGHT =", settings)

    def test_generation_only_inside_existing_exclusion(self):
        candidates = _read("candidates.nut")
        freight = _function_body(candidates, "OpexFreightCandidates")
        gate = freight.index("if (!v179Keep && (ss != null || sd != null))")
        call = freight.index("OpexV264ConvergentService(")
        self.assertLess(gate, call)
        self.assertIn(
            "if (ss == null && sd != null)",
            freight[gate:call],
        )
        town = freight.index("if (hasTownSinks)")
        self.assertNotIn("V264", freight[town:])
        pax = _function_body(candidates, "OpexPaxCandidates")
        self.assertNotIn("V264", pax)
        self.assertNotIn("convergent_dest", pax)

    def test_service_and_emit_are_active_without_old_off_guard(self):
        candidates = _read("candidates.nut")
        service = _function_body(candidates, "OpexV264ConvergentService")
        emit = _function_body(candidates, "OpexV264EmitConvergent")
        self.assertNotIn("V264_CONVERGENT_FREIGHT", service)
        self.assertNotIn("V264_CONVERGENT_FREIGHT", emit)
        self.assertIn("if (service == null || service.blocked) return null;", service)
        self.assertIn("if (candidate == null) return null;", emit)
        self.assertIn("AICargoList_StationAccepting(stationId)", service)
        self.assertIn("MIN_SEPARATION", service)
        self.assertNotIn("isTransformer", service)
        self.assertNotIn("< ORIGIN_SEPARATION", service)
        self.assertNotIn(">= ORIGIN_SEPARATION", service)
        self.assertIn('candidate.joinEnd <- "B"', emit)
        self.assertIn("candidate.convergent_dest <- 1", emit)
        self.assertIn("candidate.joinPlatform <- attached.platform", emit)
        self.assertIn("candidate.joinStationId <- attached.stationId", emit)
        self.assertIn("candidate.originServed = true", emit)
        self.assertNotIn("candidate.joinLineId", emit)
        self.assertNotIn("joinLineId <-", emit)
        keep = emit.index('OpexDecide("V264_KEEP"')
        self.assertLess(emit.index("if (DECISION_LOG)"), keep)
        self.assertLess(emit.index("if (DECISION_LOG)"), emit.index("AICargo.GetCargoLabel"))

    def test_too_close_skips_only_end_b(self):
        lines = _read("lines.nut")
        tc = _function_body(lines, "OpexAI::_tooClose")
        self.assertIn("local shareEndB = isSharedDest", tc)
        self.assertIn(
            '(("convergent_dest" in candidate) && candidate.convergent_dest == 1)',
            tc,
        )
        self.assertEqual(tc.count('if (isSharedDest && entry[0] == "B") continue;'), 2)
        self.assertEqual(tc.count('if (shareEndB && entry[0] == "B") continue;'), 2)
        self.assertIn("if (isSharedDest && stationId == joinStationId) continue;", tc)
        self.assertNotIn("shareEndB && stationId", tc)
        self.assertNotIn('shareEndB && entry[0] == "A"', tc)

    def test_parallel_join_untouched_and_spread_is_fallback(self):
        builder = _read("builder_rail.nut")
        parallel = _function_body(builder, "OpexJoinPlatformPlans")
        self.assertNotIn("V264", parallel)
        self.assertNotIn("convergent", parallel)
        self.assertIn("JOIN_PARALLEL_MAX_SIDE", parallel)
        plans = _function_body(builder, "OpexRailPlatformPlans")
        self.assertIn(
            '|| (("convergent_dest" in candidate) && candidate.convergent_dest)',
            plans,
        )
        join_call = plans.index("OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsB)")
        spread_call = plans.index("OpexV264SpreadJoinPlans(")
        self.assertLess(join_call, spread_call)
        self.assertIn("if (jointPlansB.len() == 0)", plans[join_call:spread_call])
        decide = plans.index('OpexDecide("V264_JOIN"')
        self.assertLess(plans.index("if (DECISION_LOG)"), decide)
        self.assertIn("if (strictOriginReuseJoin)", plans)

    def test_spread_uses_engine_bounds_and_one_length(self):
        builder = _read("builder_rail.nut")
        names = (
            "OpexV264StationRailBox",
            "OpexV264RectDistance",
            "OpexV264SpreadWindow",
            "OpexV264AnchorInWindow",
            "OpexV264ParallelAnchor",
            "OpexV264TrySpreadAnchor",
            "OpexV264SpreadVisit",
            "OpexV264SpreadScan",
            "OpexV264SpreadJoinPlans",
        )
        start = builder.index("function OpexV264StationRailBox(")
        blob = builder[start:builder.index("function OpexRailTryPlatformLength(")]
        for token in (
            "station.station_spread",
            "station.distant_join_stations",
            "AITileList_StationType",
            "AITestMode",
            "BuildRailStation",
            "MAX_STATION_PLANS",
            "JOIN_PARALLEL_MAX_SIDE",
            "game_settings.ini",
            "station_cmd.cpp",
            "script_rail.cpp",
        ):
            self.assertIn(token, blob, token)
        self.assertNotIn("OpexRailMinimumPlatformLength", blob)
        self.assertNotIn("150000", blob)
        self.assertNotIn("80000", blob)
        self.assertNotIn("80", blob)
        spread = _function_body(builder, "OpexV264SpreadJoinPlans")
        self.assertTrue(spread.split("{", 1)[1].lstrip().startswith(
            "if (platform == null) return [];"))
        self.assertNotIn("V264_CONVERGENT_FREIGHT", spread)
        self.assertIn("if (spread == null || spread < 4) return [];", spread)
        self.assertNotIn("spread = 12", spread)
        for name in names:
            body = _function_body(builder, name)
            for family in PROTECTED:
                self.assertNotIn(family, body, (name, family))

    def test_retired_v182_floor_does_not_restrict_v264(self):
        make = _function_body(_read("candidates.nut"), "OpexMakeCandidate")
        self.assertNotIn("V182_RAIL_FREIGHT_MIN_DIST", make)
        self.assertIn("V269_RAIL_LATE_RELAX", make)
        for name in ("OpexV264ConvergentService", "OpexV264EmitConvergent"):
            self.assertNotIn("V182", _function_body(_read("candidates.nut"), name))


class TestV264SpreadGeometry(unittest.TestCase):
    def test_perpendicular_example_and_window_matches_union(self):
        # Gare x=10..14, y=20. Quai perpendiculaire de longueur 5.
        x0, x1, y0, y1 = 10, 14, 20, 20
        spread, length = 12, 5
        win = _spread_window(x0, y0, x1, y1, spread, length, False)
        self.assertTrue(_in_window(win, 15, 18))
        self.assertTrue(_union_fits(x0, y0, x1, y1, 15, 18, length, False, spread))
        self.assertFalse(_in_window(win, 30, 18))
        self.assertFalse(_union_fits(x0, y0, x1, y1, 30, 18, length, False, spread))
        self.assertEqual(_chebyshev(15, 18, x0, y0, x1, y1), 2)

        for box in ((10, 20, 14, 20), (4, 8, 9, 11)):
            bx0, by0, bx1, by1 = box
            for along_x in (False, True):
                for used in (1, 5, spread):
                    win = _spread_window(bx0, by0, bx1, by1, spread, used, along_x)
                    for ax in range(bx0 - spread - 1, bx1 + spread + 2):
                        for ay in range(by0 - spread - 1, by1 + spread + 2):
                            self.assertEqual(
                                _in_window(win, ax, ay),
                                _union_fits(bx0, by0, bx1, by1, ax, ay, used, along_x, spread),
                                (box, along_x, used, ax, ay),
                            )

    def test_piece_longer_than_spread_never_fits(self):
        # station_cmd.cpp:1471 : w_org ou h_org > station_spread est refuse.
        # OpexV264SpreadJoinPlans retourne avant le balayage.
        self.assertIn(
            "if (length > spread) return [];",
            _function_body(_read("builder_rail.nut"), "OpexV264SpreadJoinPlans"),
        )
        self.assertFalse(any(
            _union_fits(10, 20, 14, 20, ax, ay, 13, True, 12)
            for ax in range(0, 40) for ay in range(10, 30)
        ))


if __name__ == "__main__":
    unittest.main()
