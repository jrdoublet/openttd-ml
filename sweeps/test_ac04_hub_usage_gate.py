"""AC04-A v3 source/behavior fixtures, not actual Squirrel runtime or A/B proof.

The candidate is distinct from rejected discovery-loop v1 and v2:
normalize only a zero-route hub at pair-evaluation time while retaining
the list indices and snapshot shape.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai/OpexAI/settings.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai/OpexAI/globals_pre.nut").read_text(encoding="utf-8")


def block(src, function_name):
    head = src.index("function " + function_name + "(")
    start = src.index("{", head)
    level = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            level += 1
        elif src[i] == "}":
            level -= 1
            if level == 0:
                return src[head:i + 1]
    raise AssertionError("unclosed function " + function_name)


def at_usage(hubs, index, caps, use_index=True):
    """Pure state model; the real Squirrel helper is measured separately."""
    result = [dict(h) for h in hubs]
    for hub in result:
        hub["blocked"] = False
        if hub["routes"] != 0:
            continue
        # Mock both branches of CountStationRoutes: index and lines count.
        routes = index.get(hub["station"], 0)
        if not use_index:
            routes = sum(1 for a, b in index["_lines"]
                         if hub["station"] in (a, b))
        if routes <= 0:
            continue
        if not hub["valid_anchor"]:
            hub["blocked"] = True
            continue
        hub["routes"] = routes
        hub["blocked"] = routes >= caps[hub["station"]]
    return result


class TestAC04HubUsageGate(unittest.TestCase):
    def test_setting_complete_adopted_and_rollback_zero(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('ac04_hub_usage_gate',))

    def test_pair_usage_and_no_discovery_mutation(self):
        validate = block(AIR, "OpexAC04ValidateHubsAtUsage")
        discover = block(AIR, "OpexAirPlansDiscoverHubs")
        site = block(AIR, "OpexAirPlansHubToSite")
        hub = block(AIR, "OpexAirPlansHubToHub")
        plans = block(AIR, "OpexAirPlans")
        phase = block(AIR, "OpexAirPlansHubDiscoveryPhase")
        self.assertIn("OpexAir0310CountStationRoutes(ctx, hub.stationId)", validate)
        self.assertIn("if (hub.routes != 0) continue;", validate)
        self.assertIn("hub.ac04Blocked =", validate)
        self.assertIn('if (hub.ac04Blocked) continue;', site)
        self.assertIn(
            'if ((hub1.ac04Blocked || hub2.ac04Blocked)) continue;',
            hub,
        )
        self.assertIn("OpexAirPlansHubDiscoveryPhase(ctx, comboIndex, combo, airport, plane, light)", plans)
        self.assertLess(phase.index("OpexAC04ValidateHubsAtUsage(ctx)"),
                        phase.index("OpexAirV95Post73Probe(ctx, combo, airport, plane)"))
        self.assertLess(plans.index("OpexAirPlansHubDiscoveryPhase("),
                        plans.index("OpexAirPlansHubToSitePhase("))
        self.assertIn("hubs.append({ town = hubTown, anchor = loc, stationId = st, routes = 0 });", discover)
        self.assertNotIn("OpexAC04ValidateHubsAtUsage", discover)

    def test_saturated_false_orphan_blocks_without_compacting_indices(self):
        hubs = [{"station": 11, "routes": 0, "valid_anchor": True},
                {"station": 91, "routes": 0, "valid_anchor": True},
                {"station": 20, "routes": 1, "valid_anchor": True}]
        idx = {11: 4, 91: 0, 20: 1, "_lines": [(11, 33), (11, 34), (11, 35), (11, 36), (20, 30)]}
        caps = {11: 4, 91: 4, 20: 2}
        for use_index in (True, False):
            got = at_usage(hubs, idx, caps, use_index=use_index)
            self.assertEqual([x["station"] for x in got], [11, 91, 20])
            self.assertEqual([x["blocked"] for x in got], [True, False, False])
            self.assertEqual([x["routes"] for x in got], [4, 0, 1])

    def test_dead_streak_capacity_and_stale_snapshot(self):
        # The batch guard includes "dead" AIR lines, unlike hub discovery.
        hub = [{"station": 42, "routes": 0, "valid_anchor": True}]
        idx = {42: 2, "_lines": [(42, 12), (13, 42)]}
        self.assertTrue(at_usage(hub, idx, {42: 2})[0]["blocked"])
        self.assertFalse(at_usage(hub, idx, {42: 3})[0]["blocked"])
        self.assertTrue(at_usage([{"station": 42, "routes": 0, "valid_anchor": False}],
                                 idx, {42: 3})[0]["blocked"])


if __name__ == "__main__":
    unittest.main()
