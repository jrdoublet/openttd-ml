"""AC-07 : modèle figé de publication AIR, identité et ordre des groupes.

Les données et la conversion sont des stubs, pas une exécution NoAI ni une
preuve de neutralité économique/opcode ; le code réel est contrôlé statiquement.
"""

from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
import random
import unittest

ROOT = Path(__file__).resolve().parents[1]
UPDATE = (ROOT / "ai/OpexAI/projects_update.nut").read_text(encoding="utf-8")
SCHED = (ROOT / "ai/OpexAI/scheduler_tasks.nut").read_text(encoding="utf-8")
BUILDER = (ROOT / "ai/OpexAI/projects_builders.nut").read_text(encoding="utf-8")
TASK = (ROOT / "ai/OpexAI/task_projects.nut").read_text(encoding="utf-8")


def function(source, signature):
    start = source.index(signature)
    at = source.index("{", start)
    depth = 0
    for i in range(at, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError(signature)


PUBLISH = function(UPDATE, "function OpexAir0310PublishIncremental(")
INSERT = function(UPDATE, "function OpexAir0310InsertAirBlock(")
VALID = function(UPDATE, "function OpexV141PublishedAirStillValid(")
REFRESH = function(UPDATE, "function OpexV141RefreshPublishedAir(")
CONTINUE = function(SCHED, "function OpexC78ContinueCatalogAirRebuild(")
REBUILD = function(TASK, "function OpexAI::_rebuildProjects(")
FROM_AIR = function(BUILDER, "function OpexProjectFromAir(")


@dataclass(frozen=True)
class Project:
    ident: str
    mode: str
    key: str
    valid: bool = True
    payload: str | None = None
    dest_key: str | None = None
    score: int = 100
    revenue: int = 500
    planning: int = 0
    date: int = 1
    cargo: int = 0


def append_airs(others, airs):
    result, injected = [], False
    for project in others:
        if not injected and project.mode in ("water", "fleet"):
            result.extend(airs)
            injected = True
        result.append(project)
    if not injected:
        result.extend(airs)
    return result


def publish_model(groups, scan_plans, old_count, old_airplans=(), stage="complete",
                  new_cargo=1, air_ops=1000, date=4):
    """Port strict de la partition en trois voies ; sélection métier exclue."""
    inherited = stage == "air_rail" and len(old_airplans) > old_count
    prior_raw = list(old_airplans[old_count:]) if inherited else []
    prior_kept = [plan for plan in prior_raw if plan.valid]
    denominator = len(scan_plans) + len(prior_kept)
    ops_per_plan = air_ops // denominator if denominator else air_ops
    pending, new_order = {}, []
    for plan in scan_plans[old_count:]:
        if not plan.valid:
            continue
        # La vraie conversion peut refuser des plans, en changeant leur
        # nombre mais pas la provenance des autres projets.
        key = plan.dest_key or plan.key
        p = replace(plan, key=key, planning=ops_per_plan,
                    date=date, cargo=new_cargo)
        if key not in pending:
            pending[key] = []
            new_order.append(key)
        pending[key].append(p)

    kept, moved, others_by_key = {}, {}, {}
    for key, values in groups.items():
        others, surviving = [], []
        for project in values:
            if project.mode != "air":
                others.append(project)
                continue
            if project.payload in {p.payload for p in prior_raw if p.payload is not None} and (
                    project.payload not in {p.payload for p in prior_kept}):
                continue
            if project.payload is None:
                surviving.append(project)
                continue
            if not project.valid:
                continue
            fresh_key = project.dest_key or project.key
            refreshed = replace(project, key=fresh_key, planning=ops_per_plan,
                                date=date, cargo=new_cargo)
            if fresh_key == key:
                surviving.append(refreshed)
            else:
                moved.setdefault(fresh_key, []).append(refreshed)
        others_by_key[key] = others
        if surviving:
            kept[key] = surviving
    pre, post, premark = [], [], set()
    for key in groups:
        lane = others_by_key[key]
        has_rail_road = any(p.mode in ("rail", "road") for p in lane)
        has_kept = key in kept
        incoming = key in pending or key in moved
        is_late = key.startswith(("subsidy|", "fleet|"))
        if not is_late and (has_rail_road or has_kept):
            pre.append(key)
            premark.add(key)
        elif not incoming and (lane or has_kept):
            post.append(key)
    deferred = [key for key in new_order if key not in premark]
    deferred.extend(key for key in moved if key not in premark and key not in pending)
    emitted = {}
    for key in pre + deferred + post:
        airs = kept.get(key, []) + moved.get(key, []) + pending.get(key, [])
        lane = append_airs(others_by_key.get(key, []), airs)
        if lane:
            emitted[key] = lane
    return emitted, list(scan_plans) + prior_kept, ops_per_plan


class AC07PartialTests(unittest.TestCase):
    def test_live_branching_first_publish_subsequent_and_final_apply(self):
        self.assertIn('if (("partialPending" in s) && s.partialPending)', CONTINUE)
        self.assertIn('("lastPublishedCount" in s) && s.lastPublishedCount > 0', CONTINUE)
        self.assertLess(CONTINUE.index("OpexAir0310PublishIncremental("),
                        CONTINUE.index("owner._rebuildProjects(s.fleetPlan, partialAir, false);"))
        self.assertIn("if (publishCounts == null)", CONTINUE)
        self.assertIn("owner._rebuildProjects(s.fleetPlan, airOverride);", CONTINUE)
        self.assertLess(CONTINUE.index("s.lastPublishedCount = s.plans.len();"),
                        CONTINUE.index('if (s.phase == "apply")'))
        self.assertIn("advanceStage = false;", REBUILD)
        self.assertIn("if (advanceStage && STAGED_BOOTSTRAP", REBUILD)

    def test_current_v141_fields_and_conversion_validity(self):
        self.assertIn("V141_CATALOG_INCREMENTAL && !C111_AIR_C100_DECISION_SHADOW", PUBLISH)
        self.assertIn("local newPlans = (publishedCount < scanPlans.len()) ? scanPlans.slice(publishedCount)", PUBLISH)
        self.assertIn("local planCount = scanPlans.len() + priorKept.len();", PUBLISH)
        self.assertIn("OpexV141RefreshPublishedAir(project, catalog, airOpsPerPlan);", PUBLISH)
        self.assertIn("OpexProjectFromAir(catalog, plan, airOpsPerPlan);", PUBLISH)
        self.assertIn("OpexV141PublishedAirStillValid(payload)", PUBLISH)
        self.assertIn("OpexV141LogCheck", PUBLISH)
        self.assertIn("project.planningOpcodes = planningOps;", REFRESH)
        self.assertIn("project.economicsDate = AIDate.GetCurrentDate();", REFRESH)
        self.assertIn("project.cargo = catalog.paxCargo;", REFRESH)
        self.assertIn('OpexV141WriteSlot(project, "c118TownIds"', REFRESH)
        self.assertIn("local expectedOps = PROJECT_AIR_TRANSACTION_OPS;", FROM_AIR)
        self.assertIn("OpexAir0310PriorDropped(payload, priorRaw, priorKept)", PUBLISH)
        self.assertIn("OpexStagedAirPlanStillValid(catalog, priorPlan,", PUBLISH)

    def test_partition_then_recount_and_reselect(self):
        for expr in ("foreach (slotKey, entry in projects.candidateGroups)",
                     "foreach (addedKey in newKeyOrder)", "foreach (movedKey, movedList in movedAir)",
                     "if (slotKey in keptAir)", "if (slotKey in movedAir)",
                     "if (slotKey in pendingNew)", "OpexAir0310InsertAirBlock(row, airBlock)",
                     "projects.candidateGroups = rebuilt;", "projects.airPlans = storedPlans;",
                     "OpexProjectsRecountGroups(projects);",
                     "OpexReselectProjects(projects, publishCapital"):
            self.assertIn(expr, PUBLISH)
        positions = [PUBLISH.index(s) for s in
                     ("local spPubFilter", "local spPubPart", "local spPubInsert",
                      "local spPubStore", "local spPubRecount", "local spPubCap",
                      "local spPubSelect")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("OpexAir0310ModeIsLate(project)", INSERT)
        self.assertIn('project.mode == "water" || project.mode == "fleet"', UPDATE)

    def test_no_loss_no_phantom_and_stable_lane_order_5760_cases(self):
        rng = random.Random(7042026)
        count = 0
        modes = ("air", "rail", "road", "water", "fleet")
        for case in range(5760):
            keys = ("od|a", "od|b", "od|c", "fleet|4", "subsidy|9")
            groups = {}
            for p in range(rng.randint(0, 23)):
                key = rng.choice(keys)
                mode = rng.choice(modes)
                ident = f"p{case}.{p}"
                payload = ident if mode == "air" and rng.random() < .87 else None
                proj = Project(ident, mode, key, rng.random() > .20,
                               payload, rng.choice(keys) if mode == "air" and rng.random() < .23 else None)
                groups.setdefault(key, []).append(proj)
            old_count = rng.randint(1, 7)
            total = old_count + rng.randint(0, 5)
            plans = [Project(f"new{case}.{j}", "air", rng.choice(keys),
                             rng.random() > .16, f"payload{case}.{j}")
                     for j in range(total)]
            stage = rng.choice(("complete", "air_rail"))
            old_airplans = list(plans[:old_count]) + [
                Project(f"prior{case}.{j}", "air", "od|b",
                        rng.random() > .25, f"priorpayload{case}.{j}")
                for j in range(rng.randint(0, 3))
            ]
            got, stored, denominator = publish_model(groups, plans, old_count,
                                                       old_airplans, stage)
            flatten = [p for values in got.values() for p in values]
            original = [p for values in groups.values() for p in values]
            # Every non-air item must be retained byte-for-byte and once.
            self.assertEqual(Counter(p.ident for p in flatten if p.mode != "air"),
                             Counter(p.ident for p in original if p.mode != "air"))
            prior_raw = old_airplans[old_count:] if stage == "air_rail" and len(old_airplans) > old_count else []
            prior_dropped = {p.payload for p in prior_raw if not p.valid}
            eligible_old = [p.ident for p in original if p.mode == "air"
                            and (p.payload is None or (p.valid and p.payload not in prior_dropped))]
            expected_new = [p.ident for p in plans[old_count:] if p.valid]
            self.assertEqual(Counter(p.ident for p in flatten if p.mode == "air"),
                             Counter(eligible_old + expected_new))
            self.assertEqual([p.ident for p in stored[:len(plans)]],
                             [p.ident for p in plans])
            if stage == "air_rail" and prior_raw:
                self.assertEqual([p.ident for p in stored[len(plans):]],
                                 [p.ident for p in prior_raw if p.valid])
            for key, lane in got.items():
                self.assertTrue(all(p.key == key for p in lane))
                first_late = next((i for i, p in enumerate(lane) if p.mode in ("water", "fleet")), len(lane))
                self.assertTrue(all(p.mode != "air" for p in lane[first_late:]))
                self.assertTrue(all(p.planning == denominator and p.date == 4 and p.cargo == 1
                                    for p in lane if p.mode == "air" and p.payload is not None))
            count += 1
        self.assertEqual(count, 5760)

    def test_first_chunk_no_prior_and_group_overlap(self):
        first = [Project("a", "air", "od|1", payload="plan-a")]
        second = [Project("b", "air", "od|1", payload="plan-b"),
                  Project("c", "air", "od|1", payload="plan-c")]
        base = {"od|1": [Project("r", "rail", "od|1"),
                          Project("a", "air", "od|1", payload="plan-a"),
                          Project("w", "water", "od|1")]}
        groups, plans, ops = publish_model(base, first + second, 1)
        self.assertEqual([p.ident for p in groups["od|1"]], ["r", "a", "b", "c", "w"])
        self.assertEqual([p.ident for p in plans], ["a", "b", "c"])
        self.assertEqual(ops, 333)
        self.assertEqual([p.mode for p in append_airs([base["od|1"][0], base["od|1"][2]],
                                                       [base["od|1"][1]])], ["rail", "air", "water"])

    def test_moved_and_shared_key_keep_all_alternatives(self):
        groups = {
            "od|old": [Project("rail", "rail", "od|old"),
                       Project("air", "air", "od|old", payload="old", dest_key="od|new")],
            "od|new": [Project("road", "road", "od|new")],
        }
        plans = [Project("already", "air", "od|x"), Project("fresh", "air", "od|new")]
        out, _, _ = publish_model(groups, plans, 1)
        self.assertEqual([p.ident for p in out["od|old"]], ["rail"])
        self.assertEqual([p.ident for p in out["od|new"]], ["road", "air", "fresh"])

    def test_bootstrap_prior_kept_dropped_and_duplicate_exception(self):
        plans = [Project("a", "air", "od|a"), Project("b", "air", "od|b")]
        prior_good = Project("prior-good", "air", "od|z", payload="prior-good")
        prior_bad = Project("prior-bad", "air", "od|z", False, "prior-bad")
        groups = {"od|z": [prior_good, prior_bad]}
        emitted, stored, ops = publish_model(groups, plans, 1,
                                             [plans[0], plans[1], prior_good, prior_bad], "air_rail")
        self.assertEqual([p.ident for p in emitted["od|z"]], ["prior-good"])
        # `b` est déjà dans le préfixe scan et présent dans la queue héritée ;
        # l'append le réplique intentionnellement au bootstrap (écart admis).
        self.assertEqual([p.ident for p in stored], ["a", "b", "b", "prior-good"])
        self.assertEqual(ops, 250)
        # La particularité du bootstrap est connue : une reconstruction complète
        # peut ajouter deux fois le préfixe hérité. Ne pas exiger une parité
        # exacte de multiplicité sur ce chemin.
        self.assertIn("Queue heritee du bootstrap AIR_RAIL seulement", PUBLISH)
        self.assertIn("et le compte deux fois. Ecart", PUBLISH)

    def test_invalid_payload_and_fallback_are_explicit(self):
        base = {"od|z": [Project("orphan", "air", "od|z", payload=None)]}
        emitted, _, _ = publish_model(base, [Project("old", "air", "od|z")], 1)
        self.assertEqual([p.ident for p in emitted["od|z"]], ["orphan"])
        for guard in ("owner == null || scanPlans == null || publishedCount <= 0",
                      "owner._projects == null || owner._catalog == null",
                      "!(\"candidateGroups\" in projects)",
                      "!(\"stats\" in projects)"):
            self.assertIn(guard, PUBLISH)
        self.assertIn("if (publishCounts == null)", CONTINUE)


if __name__ == "__main__":
    unittest.main()
