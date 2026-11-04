"""Contrats RAIL-NET (rail_net, défaut 0) — 04/11/2026.

Greffe d'une source fret sur une boucle RAIL-LOOP certifiée : fusion sur la
voie chargée, divergence sur la voie vide, PBS_ONEWAY sur les embranchements.
Tests de source uniquement (le Squirrel ne se compile pas ici) : câblage
opt-in, ordre fail-closed, règles anti-interblocage portées en Python,
planificateur coût/capacité, projection OFF au bit près.
"""

import hashlib
import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))

from rail_net_off import INSERTIONS, MARKERS, off_source  # noqa: E402
from test_rail_loop_20261104 import (  # noqa: E402
    call_args, function_body, global_signatures, read, strip_squirrel)

# Octets de 8268b653, la base de RAIL-NET (après RAIL-LOOP/FILL/KEEP).
BASE_SHA = {
    "globals_pre.nut": "8face268240b4a085bb3e42463008bf581059ab1d4166c975d068f13f34db6a6",
    "settings.nut": "77004387006e87829837bffc516d4a45f748282ae39049c9436c3d6b84f424d2",
    "info.nut": "61ddba2a0ee564bd98813d1d5c44af5e4dbd93533fef6d047aefed9a41947ce1",
    "main.nut": "ce82ecf8cb6e153832ba144f6a421b2b734729bb7129e0597a8ee484fb50fc6d",
    "task_rail.nut": "9b9fac0913dedbebfd6bd41d89fa608c8ca7a551f376601768e9068018b59b13",
    "scheduler.nut": "bc0d6edcdb0ad881427dc0b03b33f26f537b8c2a0afaa7739b7a756a241daafe",
    "rail_loop.nut": "66a043a74f0b8f98ff97cbd861c568d120d58480251323bfb39cbfe9d17dbad2",
    "task_v284.nut": "3f0cf059f643941408fb4b16e53fa596936fc26ead46ff316876df9f2fc47edb",
}


def net():
    return read("rail_net.nut")


def body(name):
    return function_body(net(), name)


# --- Portages Python des fonctions pures (mêmes formules) --------------------

def passes_per_month(max_block, train_tiles, speed):
    if max_block < 1 or train_tiles < 1 or speed <= 0:
        return 0.0
    return 30.0 * (0.036 * speed) / (max_block + train_tiles)


def cycle_cap(blocks):
    return max(blocks - 2, 0)


def queue_fits(trains, blocks_before_platform):
    return trains <= blocks_before_platform + 1


class Wiring(unittest.TestCase):
    def test_setting_default_zero_boolean_single_read(self):
        info = read("info.nut")
        block = info[info.index('name = "rail_net"'):]
        block = block[:block.index("});")]
        self.assertIn("min_value = 0, max_value = 1", block)
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0", block)
        self.assertIn("AICONFIG_BOOLEAN", block)
        self.assertEqual(read("globals_pre.nut").count("RAIL_NET <- false;"), 1)
        self.assertEqual(read("settings.nut").count('GetSetting("rail_net")'), 1)
        self.assertEqual(read("main.nut").count('require("rail_net.nut");'), 1)
        self.assertEqual(read("main.nut").count("_railNetState = null;"), 1)

    def test_entry_points_are_guarded(self):
        self.assertIn("  if (RAIL_NET && OpexRailNetSelect(this, year)) return;\n", read("task_rail.nut"))
        self.assertIn("  if (RAIL_NET && this._railNetState != null) OpexRailNetStep(this);\n", read("scheduler.nut"))
        expand = function_body(read("task_rail.nut"), "OpexAI::_expandRailLines")
        self.assertLess(expand.index("OpexRailLoopSelect(this, year)"), expand.index("OpexRailNetSelect(this, year)"))
        self.assertIn("if (OpexRailNetOwned(line)) continue;", expand)

    def test_feeders_excluded_from_other_transformations(self):
        self.assertIn("&& !OpexRailNetOwned(line)", function_body(read("rail_loop.nut"), "OpexRailLoopEligible"))
        grow = function_body(read("rail_loop.nut"), "OpexRailLoopGrow")
        self.assertIn("if (RAIL_NET && !OpexRailNetHostMayGrow(owner, line)) return false;", grow)
        self.assertIn("if (OpexRailNetOwned(line)) continue;", function_body(read("task_v284.nut"), "OpexV284Select"))

    def test_owned_is_field_based_so_off_lines_are_unaffected(self):
        owned = strip_squirrel(body("OpexRailNetOwned"))
        self.assertIn('("" in line)', owned)
        self.assertNotIn("RAIL_NET", owned)


class FailClosedOrder(unittest.TestCase):
    def setUp(self):
        self.build = body("OpexRailNetBuild")

    def test_host_pieces_are_laid_last(self):
        order = [
            "AIRail.BuildRailStation(state.plan.anchor",
            "OpexRailLoopBuildIndex(spur1, state.structures1, i)",
            "OpexRailLoopBuildIndex(spur2, state.structures2, i)",
            "OpexBuildDepot(spur1, forbidden)",
            "OpexRailLoopSignalRun(spur1, k + 2, n1 - 3, 1, spacing, built.signals)",
            "OpexRailLoopSignalRun(spur2, host.platformLength + 2, n2 - 4, 1, spacing, built.signals)",
            "AIRail.BuildRail(state.merge.lead, state.merge.tile, state.merge.next)",
            "AIRail.BuildRail(state.diverge.prev, state.diverge.tile, state.diverge.lead)",
            "AIRail.AreTilesConnected(state.merge.prev, state.merge.tile, state.merge.next)",
        ]
        positions = [self.build.index(x) for x in order]
        self.assertEqual(positions, sorted(positions))

    def test_certification_checks_host_intact_and_both_junctions(self):
        for needle in ("AIRail.AreTilesConnected(state.merge.prev, state.merge.tile, state.merge.next)",
                       "AIRail.AreTilesConnected(state.merge.lead, state.merge.tile, state.merge.next)",
                       "AIRail.AreTilesConnected(state.diverge.prev, state.diverge.tile, state.diverge.next)",
                       "AIRail.AreTilesConnected(state.diverge.prev, state.diverge.tile, state.diverge.lead)",
                       "OpexRailNetVerifyPath(spur1) && OpexRailNetVerifyPath(spur2)"):
            self.assertIn(needle, self.build)

    def test_preconditions_before_any_spending(self):
        first_spend = self.build.index("AITile.DemolishTile(state.plan.anchor")
        for guard in ('why = "served"', 'why = "end_structure"', 'why = "turn_90"',
                      'why = "native_track"', 'why = "cash"'):
            self.assertLess(self.build.index(guard), first_spend, guard)
        self.assertLess(self.build.index("local account = AIAccounting();"), first_spend)

    def test_rollback_never_demolishes_a_host_tile(self):
        rb = strip_squirrel(body("OpexRailNetRollback"))
        self.assertIn("AIRail.RemoveRail(state.merge.lead, state.merge.tile, state.merge.next)", rb)
        self.assertIn("AIRail.RemoveRail(state.diverge.prev, state.diverge.tile, state.diverge.lead)", rb)
        self.assertIn("if (t == state.merge.tile || t == state.diverge.tile) continue;", rb)
        self.assertNotIn("DemolishTile(state.merge", rb)
        self.assertNotIn("DemolishTile(state.diverge", rb)

    def test_every_failure_rolls_back_and_remembers(self):
        step = body("OpexRailNetStep")
        self.assertIn("OpexRailNetRollback(state, res.built);", step)
        self.assertEqual(step.count("OpexRailNetRollback(state, res.built);"), 2)
        self.assertIn("OpexRailNetRemember(state.host, state.source.industry, RAIL_NET_RETRY_DAYS);",
                      body("OpexRailNetFail"))

    def test_feeder_train_built_in_host_depot_and_started_after_registration(self):
        commit = body("OpexRailNetCommit")
        self.assertIn("OpexBuildTrains(owner._catalog, host.cargo, \"freight\", host.depot,", commit)
        self.assertIn("host.platformLength, false);", commit)
        self.assertLess(commit.index("owner._lines.append(line);"), commit.index("AIVehicle.StartStopVehicle(train)"))


class DeadlockRules(unittest.TestCase):
    def test_cycle_cap_matches_rail_loop_commit(self):
        self.assertIn("local cap = blocks - 2;", function_body(read("rail_loop.nut"), "OpexRailLoopCommit"))
        self.assertIn("local cap = cycleBlocks - 2;", body("OpexRailNetCycleCap"))
        self.assertEqual([cycle_cap(b) for b in (0, 2, 3, 10)], [0, 0, 1, 8])

    def test_queue_never_reaches_a_junction(self):
        self.assertTrue(queue_fits(3, 2))
        self.assertFalse(queue_fits(4, 2))
        self.assertIn("return trains <= blocksBeforePlatform + 1;", body("OpexRailNetQueueFits"))
        diverge = body("OpexRailNetDivergeSite")
        self.assertIn("if (!OpexRailNetQueueFits(hostTrains, OpexRailNetSignalsAfter(empty, i))) break;", diverge)
        self.assertIn("host.rawset(\"railNetQueueCap\", OpexRailNetSignalsAfter(state.tracks.empty, state.diverge.index));",
                      body("OpexRailNetCommit"))
        self.assertIn("OpexRailNetQueueFits(host.trains + 1, queue)", body("OpexRailNetHostMayGrow"))
        grow = body("OpexRailNetGrow")
        self.assertIn("OpexRailNetQueueFits(line.trains + 1,", grow)
        self.assertIn("if (OpexRailNetHostTrains(owner, host) + 1 > cap) return false;", grow)

    def test_junction_block_clears_a_whole_train(self):
        build = body("OpexRailNetBuild")
        self.assertIn("host.platformLength + 2, n2 - 4", build)
        plan = body("OpexRailNetPlan")
        self.assertIn("local margin = host.platformLength + 2;", plan)

    def test_host_growth_counts_feeder_trains(self):
        may = body("OpexRailNetHostMayGrow")
        self.assertIn("OpexRailNetHostTrains(owner, host) + 1 <= cap", may)
        trains = body("OpexRailNetHostTrains")
        self.assertIn("line.railNetHost == host.lineId) n += line.trains;", trains)

    def test_junction_tile_is_plain_straight_single_track(self):
        jt = body("OpexRailNetJunctionTile")
        for needle in ("if (cur - prev != next - cur) return null;", "OpexTileTrackCount(cur) != 1",
                       "AIRail.IsRailStationTile(cur)", "AIRail.IsRailDepotTile(cur)",
                       "AIBridge.IsBridgeTile(cur)", "AITunnel.IsTunnelTile(cur)",
                       "AIRail.GetSignalType(cur, prev) != AIRail.SIGNALTYPE_NONE"):
            self.assertIn(needle, jt)

    def test_no_ninety_degree_turn_at_junctions(self):
        begin = body("OpexRailNetBegin")
        self.assertIn("[merge.lead + merge.dir, diverge.lead - diverge.dir]", begin)
        build = body("OpexRailNetBuild")
        self.assertIn("OpexRailNetHasNinety([spur1[n1 - 3], spur1[n1 - 2], state.merge.tile, state.merge.next])", build)
        self.assertIn("OpexRailNetHasNinety([state.diverge.prev, state.diverge.tile, spur2[1], spur2[2]])", build)

    def test_signals_face_travel_direction(self):
        blocks = body("OpexRailNetBlocks")
        self.assertIn("AIRail.GetSignalType(tiles[i], tiles[i - 1]) != AIRail.SIGNALTYPE_NONE", blocks)
        fix2 = function_body(read("v190_fix_directional.nut"), "OpexV190Fix2PlaceSignal")
        self.assertIn("local front = toward > 0 ? prev : next;", fix2)
        tracks = body("OpexRailNetTracks")
        self.assertIn("if (host.railLoopFlow > 0) return { loaded = route, empty = track2 };", tracks)
        self.assertIn("return { loaded = track2, empty = OpexRailNetReverse(route) };", tracks)


class CapacityAndPlanner(unittest.TestCase):
    def test_passes_per_month_formula(self):
        self.assertIn("return 30.0 * tilesPerDay / (maxBlock + trainTiles);", body("OpexRailNetPassesPerMonth"))
        self.assertAlmostEqual(passes_per_month(10, 4, 100), 30 * 3.6 / 14)
        self.assertEqual(passes_per_month(0, 4, 100), 0.0)
        # Un canton plus long réduit le débit : la plus longue section commande.
        self.assertGreater(passes_per_month(7, 4, 100), passes_per_month(20, 4, 100))

    def test_capacity_gate_uses_utilisation_and_cycle_cap(self):
        cap = body("OpexRailNetCapacity")
        self.assertIn("demand * 100 <= supply * RAIL_NET_UTIL_PCT", cap)
        self.assertIn("hostTrains + extraTrains <= cycleCap", cap)

    def test_planner_connects_only_when_cheaper_and_within_capacity(self):
        plan = body("OpexRailNetPlan")
        cost = plan.index("quote.connect * 100 > quote.plain * RAIL_NET_COST_PCT")
        capacity = plan.index("OpexRailNetCapacity(owner, host, tracks, 1)")
        ok = plan.index('ok = true, reason = "connect"')
        self.assertLess(cost, capacity)
        self.assertLess(capacity, ok)
        self.assertIn('reason = "plain_cheaper"', plan)
        self.assertIn('reason = "no_junction"', plan)

    def test_plain_line_is_left_to_the_portfolio(self):
        code = strip_squirrel(net())
        for forbidden in ("OpexBuildLine(", "_startRailSearch(", "_railSearch ="):
            self.assertNotIn(forbidden, code)
        select = body("OpexRailNetSelect")
        self.assertIn("if (owner._railNetState != null || owner._railLoopState != null) return false;", select)

    def test_one_feeder_per_host_in_this_step(self):
        eligible = body("OpexRailNetHostEligible")
        self.assertIn('!("railNetFeeder" in host)', eligible)
        self.assertIn("host.railLoop == 2", eligible)


class BenchWatch(unittest.TestCase):
    def test_watch_is_decision_log_only_and_monthly(self):
        watch = body("OpexRailNetWatch")
        self.assertTrue(strip_squirrel(watch).lstrip("{ \n").startswith("if (DECISION_LOG) return;".replace("(", "(!", 1)))
        self.assertIn("now - line.railNetWatchDate < 30", watch)
        self.assertIn("AIVehicle.VS_CRASHED", watch)
        self.assertIn("AIVehicle.GetCurrentSpeed(v) == 0", watch)
        self.assertIn("OpexRailNetWatch(owner, line, now);", body("OpexRailNetSelect"))


class ModuleSafety(unittest.TestCase):
    def test_static_safety(self):
        code = strip_squirrel(net())
        for bad in ("getroottable", ".find(", "Sleep(", ".Valuate(", "foreach (ind, _ in"):
            self.assertNotIn(bad, code)
        self.assertIsNone(re.search(r"function\s*\(", code))
        self.assertIsNone(re.search(r"\b(clone|base)\b", code))
        self.assertIsNone(re.search(r"^const ", code, re.M))

    def test_arity_of_opex_calls(self):
        sigs = global_signatures()
        code = strip_squirrel(net())
        checked = 0
        for m in re.finditer(r"\b(Opex\w+)\s*\(", code):
            if re.search(r"function\s+$", code[max(0, m.start() - 12):m.start()]):
                continue
            name = m.group(1)
            if name not in sigs:
                continue
            n = len(call_args(code, m.end() - 1))
            self.assertTrue(any(r <= n <= t for r, t in sigs[name]), (name, n, sigs[name]))
            checked += 1
        self.assertGreater(checked, 40)

    def test_every_called_opex_function_exists(self):
        sigs = global_signatures()
        code = strip_squirrel(net())
        called = set(re.findall(r"\b(Opex[A-Z]\w+)\s*\(", code))
        missing = sorted(n for n in called if n not in sigs)
        self.assertEqual(missing, [])


class RailNetOffProjection(unittest.TestCase):
    def test_off_projection_restores_base_bytes(self):
        for name, digest in BASE_SHA.items():
            with self.subTest(name=name):
                projected = off_source(name, read(name))
                self.assertEqual(hashlib.sha256(projected.encode("utf8")).hexdigest(), digest)
                self.assertEqual(off_source(name, projected), projected)

    def test_partial_or_duplicated_hunk_fails_closed(self):
        damaged = read("task_rail.nut").replace("OpexRailNetSelect(this, year)", "OpexRailNetSelect(this, year + 0)")
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", damaged)
        with self.assertRaises(AssertionError):
            off_source("scheduler.nut", read("scheduler.nut") + INSERTIONS["scheduler.nut"][0])

    def test_markers_cover_all_hunks(self):
        for name, fragments in INSERTIONS.items():
            for fragment in fragments:
                with self.subTest(name=name, fragment=fragment[:40]):
                    self.assertTrue(any(m in fragment for m in MARKERS))

    def test_chain_head_strips_rail_net_first(self):
        chain = (SWEEPS / "invest_stall_diagnostic_off.py").read_text(encoding="utf8")
        self.assertLess(chain.index("rail_net_off"), chain.index("rail_keep_off"))


if __name__ == "__main__":
    unittest.main()
