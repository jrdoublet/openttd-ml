"""AC04-B + AC05 + AC06-v2 accepted AIR catalogue corrections.

Checks the adopted defaults, physical-site identity and legacy V86 branch.
These model/source tests complement, but do not replace, the Docker A/B gates.
"""
import itertools
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")
PRE = (ROOT / "ai/OpexAI/globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai/OpexAI/settings.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
SCHED = (ROOT / "ai/OpexAI/scheduler_tasks.nut").read_text(encoding="utf-8")
ORCH = (ROOT / "ai/OpexAI/orchestrator.nut").read_text(encoding="utf-8")
PERSIST = (ROOT / "ai/OpexAI/persist.nut").read_text(encoding="utf-8")
UPDATE = (ROOT / "ai/OpexAI/projects_update.nut").read_text(encoding="utf-8")


def function(source, name):
    a = source.index("function " + name + "(")
    b = source.index("{", a)
    depth = 0
    for pos in range(b, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[a:pos + 1]
    raise AssertionError("unclosed source function " + name)


def add_sites(initial, extra, cap, dedup):
    sites = list(initial)
    for item in extra:
        if len(sites) >= cap:
            break
        if dedup and any(existing[1] == item[1] for existing in sites):
            continue
        sites.append(item)
    return sites


class ACAdopted(unittest.TestCase):
    def test_independent_air_phase_contracts_and_v141_publication(self):
        """Each resumable AIR phase owns its cursor; no scheduler redesign."""
        phases = ("OpexAirPlansPrepare", "OpexAirPlansFindSites",
                  "OpexAirPlansNewPairs", "OpexAirPlansDiscoverHubs",
                  "OpexAirPlansHubToSite", "OpexAirPlansHubToHub",
                  "OpexAirPlansFinalize")
        driver = function(AIR, "OpexAirPlans")
        for name in phases:
            self.assertIn("function " + name + "(", AIR)
            self.assertIn(name + "(", driver)
        for checkpoint in ("scanIndex", "rankIndex", "hubSiteI", "hubSiteJ",
                           "hubHubI", "hubHubJ", "hubPhase"):
            self.assertIn(checkpoint, AIR)
        for yield_reason in ("sites_yield", "pairs_yield", "hub_site_yield", "hub_hub_yield"):
            self.assertIn(yield_reason, driver)
        c78 = function(SCHED, "OpexC78ContinueCatalogAirRebuild")
        self.assertIn("OpexAir0310PublishIncremental", c78)
        self.assertIn("s.partialPending", c78)
        self.assertIn("owner._rebuildProjects(s.fleetPlan, airOverride)", c78)
        self.assertIn("function OpexAir0310PublishIncremental(", UPDATE)

    def test_defaults_overrideable_without_other_experiments(self):
        for name, global_name in (("ac04_extra_site_dedup", "AC04_EXTRA_SITE_DEDUP"),
                                  ("ac05_skip_unused_hub_income", "AC05_SKIP_UNUSED_HUB_INCOME"),
                                  ("ac06_c76_snapshot_ack", "AC06_C76_SNAPSHOT_ACK")):
            start = INFO.index('name = "' + name + '"')
            spec = INFO[start:INFO.index("});", start)]
            self.assertIn("easy_value = 1, medium_value = 1, hard_value = 1", spec)
            self.assertIn("custom_value = 1", spec)
            self.assertIn(global_name + " <- true;", PRE)
            self.assertIn('AIController.GetSetting("' + name + '")', SETTINGS)
        self.assertNotIn('name = "ac04_hub_route_fix"', INFO)
        self.assertIn('AC06_C76_SNAPSHOT_ACK = C76_REGEN_TARGETED', SETTINGS)

    def test_ac06_v2_small_snapshot_and_late_revision_guards(self):
        capture = function(ORCH, "OpexAC06CaptureRevisionNumbers")
        layer = function(ORCH, "OpexAC06SnapshotLayer")
        acknowledge = function(ORCH, "OpexAC06AcknowledgeSnapshot")
        start = function(SCHED, "OpexC78StartCatalogAirRebuild")
        apply = function(SCHED, "OpexC78ContinueCatalogAirRebuild")
        for key in ("towns", "industries", "lines"):
            self.assertIn("current." + key, capture)
        for key in ("rail", "road", "air", "water"):
            self.assertIn("current.engines." + key, capture)
        self.assertNotIn("_c76SaveRevisions", capture)
        self.assertNotIn("_c76ModeConsumed", capture)
        self.assertNotIn("coveredByLayer", acknowledge)  # Rejected v3.
        self.assertIn("OpexAC06SnapshotLayer(snapshot, layer)", acknowledge)
        self.assertIn("local rev = covered > previous ? covered : previous;", acknowledge)
        self.assertIn("snapshot.engines_air", layer)
        self.assertIn("OpexAC06CaptureRevisionNumbers(owner) : null", start)
        self.assertIn("OpexAC06AcknowledgeSnapshot(owner, s.c76StartRevisions)", apply)
        self.assertIn("owner._c76AcknowledgeAllLayers();", apply)  # Flag OFF.
        self.assertIn("saveObj.c76Revisions <- this._c76SaveRevisions()", PERSIST)
        self.assertNotIn("c76StartRevisions", PERSIST)  # Transient C78.

        deps = {"air": ("towns", "engines.air", "lines"),
                "rail_pax": ("towns", "engines.rail", "lines"),
                "fleet": ("lines", "engines.rail", "engines.road", "engines.air", "engines.water")}
        layers = ("towns", "industries", "lines", "engines.rail",
                  "engines.road", "engines.air", "engines.water")
        for event in layers:
            current = {k: 1 for k in layers}
            snapshot = dict(current)
            current[event] += 1
            ack = {k: 0 for k in layers}
            consumed = {m: {k: 0 for k in ds} for m, ds in deps.items()}
            consumed["fleet"]["engines.air"] = 3  # C77 already newer.
            for k in layers:
                ack[k] = max(ack[k], snapshot[k])
            for mode, ds in deps.items():
                for k in ds:
                    consumed[mode][k] = max(consumed[mode][k], snapshot[k])
            self.assertEqual({k for k in layers if current[k] > ack[k]}, {event})
            self.assertEqual(consumed["fleet"]["engines.air"], 3)

    def test_ac04b_anchor_identity_not_town(self):
        body = function(AIR, "OpexAC04ExtraSiteAlreadyKnown")
        self.assertIn("site.anchor == candidate.anchor", body)
        discover = function(AIR, "OpexAirPlansDiscoverHubs")
        self.assertIn("AC04_EXTRA_SITE_DEDUP && OpexAC04ExtraSiteAlreadyKnown(sites, extraSite)", discover)
        self.assertIn("if (c83OwnSecondSlot) extraSite.c83OwnSecondSlot <- true;", discover)
        self.assertEqual(add_sites([(42,100)], [(42,100),(42,200),(43,300),(43,300)], 4, True),
                         [(42,100),(42,200),(43,300)])
        self.assertEqual(add_sites([(42,100)], [(42,100),(42,200),(43,300)], 4, False),
                         [(42,100),(42,100),(42,200),(43,300)])
        for n, cap in itertools.product(range(12), (1, 2, 4, 8)):
            values = add_sites([(n, n * 100)], [(x % 4,x % 5) for x in range(n)], cap, True)
            self.assertEqual(len(values), len(set(v[1] for v in values)))

    def test_ac05_marginal_v86_unchanged_when_read(self):
        body = function(AIR, "OpexAirPlansHubToHub")
        self.assertIn("AIR_HUBHUB_MARGINAL && !(AC05_SKIP_UNUSED_HUB_INCOME && C121_AIR_ECONOMICS)", body)
        self.assertIn("AIR_HUBHUB_MARGINAL && !C121_AIR_ECONOMICS", body)
        self.assertIn("hubAvgIncome[i]", body)
        self.assertIn("hubAvgIncome[j]", body)
        for marginal, c121, flag in itertools.product((False, True), repeat=3):
            computed = marginal and not (flag and c121)
            read = marginal and not c121
            self.assertFalse(read and not computed)
            if not flag:
                self.assertEqual(computed, marginal)


if __name__ == "__main__":
    unittest.main()
