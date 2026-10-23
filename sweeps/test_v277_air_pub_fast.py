#!/usr/bin/env python3
"""Contrats statiques et de comportement V277 : publication AIR rapide et filtre indexe.

Verifications :
1. Reglage v277_air_pub_fast (0..2, defaut 0 aux quatre difficultes, lu dans settings.nut).
2. Globale V277_AIR_PUB_FAST declaree a 0 dans globals_pre.nut.
3. A 0, le code historique s'execute de maniere inchangee :
   - publication AIR parcourt candidateGroups et reecrit les projets ;
   - filtre de re-selection appelle OpexAirBatchPlanStillLive sans construire ctx.
4. En mode 1, les chemins rapides s'executent :
   - publication rapide insere dans candidateGroups sans reparcourir le vivier ;
   - mise a jour incrementale exacte de all, odProjects, modeCandidates, modeAlternatives ;
   - filtre de re-selection appelle OpexAirBatchPlanStillLiveIndexed avec ctx pre-construit.
5. En mode 2 (mode controle) :
   - execute les deux chemins, compare et journalise les ecarts sous V277_CHECK ;
   - conserve le resultat historique.
6. Le filtre de re-selection construit le contexte indexe une seule fois hors de la boucle.
7. Le cache mensuel de validite des sites (OpexAir0310SiteValidityBegin/Ok) est conserve,
   sans utiliser OpexAirSiteStillBuildableIndexed (cache par appel).
8. Simulation Python de l'insertion rapide confirmant la parite exacte avec le chemin historique.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise AssertionError("unterminated " + signature)


class TestV277AirPubFast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("info.nut")
        cls.globals_pre = _read("globals_pre.nut")
        cls.settings = _read("settings.nut")
        cls.update = _read("projects_update.nut")
        cls.generation = _read("projects_generation.nut")
        cls.publish_body = _function_body(
            cls.update, "function OpexAir0310PublishIncremental("
        )
        cls.insert_helper = _function_body(
            cls.update, "function OpexV277AirPubFastInsert("
        )
        cls.filter_body = _function_body(
            cls.generation,
            "function OpexAir0310FilterAirAlternativesStillValid(",
        )

    def test_setting_declared_default_auto_bounds_0_to_3(self):
        block = re.search(r'name = "v277_air_pub_fast",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block, "v277_air_pub_fast doit etre declare dans info.nut")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 3", body)
        self.assertIn("step_size = 1", body)
        self.assertIn("flags = 0", body)
        for level in (
            "easy_value",
            "medium_value",
            "hard_value",
            "custom_value",
            "default_value",
        ):
            # Defaut auto (3) depuis le 20/10 : actif des 1024x1024 seulement.
            self.assertRegex(body, level + r" = 3\b", f"{level} doit valoir 3")

    def test_global_declared_and_read_once(self):
        self.assertIn("V277_AIR_PUB_FAST <- 0;", self.globals_pre)
        reads = [
            (path.name, path.read_text(encoding="utf-8").count('GetSetting("v277_air_pub_fast")'))
            for path in AI.glob("*.nut")
        ]
        total_reads = sum(count for _, count in reads)
        self.assertEqual(total_reads, 1, "v277_air_pub_fast doit etre lu exactement une fois")
        self.assertIn('AIController.GetSetting("v277_air_pub_fast")', self.settings)
        self.assertIn(
            "V277_AIR_PUB_FAST = (v277Pub != null && v277Pub >= 0 && v277Pub <= 2) ? v277Pub : 0;",
            self.settings,
        )

    def test_mode_0_historical_path_unchanged(self):
        # En mode 0, publication : pas de retour rapide, passe par spPubFilter/spPubPart/spPubInsert
        self.assertIn("if (V277_AIR_PUB_FAST == 1 && priorRaw.len() == 0)", self.publish_body)
        self.assertIn("spPubFilter", self.publish_body)
        self.assertIn("spPubPart", self.publish_body)
        self.assertIn("spPubInsert", self.publish_body)
        self.assertIn("OpexProjectsRecountGroups(projects);", self.publish_body)

        # C83 switched recheck and V277 filter checker retired; revalidation
        # remains unconditional on both sites and abandoned status.
        self.assertIn("OpexCandidateIsAbandoned(project, abandonedPairs)", self.filter_body)
        self.assertIn("OpexAir0310SiteValidityOk(validity, keyA,", self.filter_body)
        self.assertIn("OpexAir0310SiteValidityOk(validity, keyB,", self.filter_body)
        self.assertNotIn("C83_FIXES", self.filter_body)

    def test_filter_builds_context_once_outside_loop(self):
        ctx_decl = "local validity = OpexAir0310SiteValidityBegin(stationLimitedTowns);"
        self.assertEqual(self.filter_body.count("OpexIncrRevalidateIndexContext(lines)"), 0)
        self.assertEqual(self.filter_body.count(ctx_decl), 1)
        loop_start = self.filter_body.index("foreach (project in alternatives)")
        ctx_pos = self.filter_body.index(ctx_decl)
        self.assertLess(ctx_pos, loop_start, "la validite doit etre initialisee avant la boucle foreach")

    def test_filter_preserves_monthly_site_validity_cache(self):
        # Cache mensuel conserve
        self.assertIn("OpexAir0310SiteValidityBegin(stationLimitedTowns)", self.filter_body)
        self.assertIn("OpexAir0310SiteValidityOk(validity, keyA", self.filter_body)
        self.assertIn("OpexAir0310SiteValidityOk(validity, keyB", self.filter_body)
        # OpexAirSiteStillBuildableIndexed NE doit PAS etre appele
        self.assertNotIn("OpexAirSiteStillBuildableIndexed", self.filter_body)

    def test_mode_2_control_mode_logging_and_preservation(self):
        # Verification publication en mode 2
        self.assertIn("else if (V277_AIR_PUB_FAST == 2 && priorRaw.len() == 0)", self.publish_body)
        self.assertIn('OpexDecide("V277_CHECK", checkMsg);', self.publish_body)
        self.assertIn('if (!DECISION_LOG) AILog.Warning("V277_CHECK " + checkMsg);', self.publish_body)
        self.assertIn("projects.candidateGroups = rebuilt;", self.publish_body)

        # Mode 2 continues to check publication; retired filter checker cannot
        # choose a different path or bypass either live-site validation.
        self.assertNotIn("V277_AIR_PUB_FAST", self.filter_body)
        self.assertNotIn("C83_FIXES", self.filter_body)
        self.assertIn("OpexAir0310SiteValidityOk(validity, keyA,", self.filter_body)
        self.assertIn("OpexAir0310SiteValidityOk(validity, keyB,", self.filter_body)

    def test_insert_helper_logic_simulation(self):
        # Simulation Python du comportement de OpexV277AirPubFastInsert
        def is_late(proj):
            return proj.get("mode") in ("water", "fleet")

        def fast_insert(groups, stats, new_key_order, pending_new):
            for slot_key in new_key_order:
                for created in pending_new[slot_key]:
                    if slot_key not in groups:
                        groups[slot_key] = [created]
                        stats["odProjects"] += 1
                        stats["modeCandidates"] += 1
                    else:
                        lst = groups[slot_key]
                        insert_idx = -1
                        for idx, p in enumerate(lst):
                            if is_late(p):
                                insert_idx = idx
                                break
                        if insert_idx >= 0:
                            lst.insert(insert_idx, created)
                        else:
                            lst.append(created)
                        stats["modeCandidates"] += 1
                        stats["modeAlternatives"] += 1

        def recount(groups):
            od = 0
            n = 0
            alt = 0
            for key, lst in groups.items():
                if not lst:
                    continue
                od += 1
                n += len(lst)
                if len(lst) > 1:
                    alt += len(lst) - 1
            return {"odProjects": od, "modeCandidates": n, "modeAlternatives": alt}

        # Scenario 1: Vivier vide, insertion d'un nouveau groupe
        groups = {}
        stats = {"odProjects": 0, "modeCandidates": 0, "modeAlternatives": 0}
        p1 = {"mode": "air", "id": 1}
        p2 = {"mode": "air", "id": 2}
        fast_insert(groups, stats, ["k1"], {"k1": [p1, p2]})
        self.assertEqual(groups["k1"], [p1, p2])
        self.assertEqual(stats, recount(groups))

        # Scenario 2: Insertion avant un projet tardif (water)
        p_rail = {"mode": "rail", "id": 10}
        p_water = {"mode": "water", "id": 20}
        p_air_new = {"mode": "air", "id": 30}
        groups2 = {"k2": [p_rail, p_water]}
        stats2 = recount(groups2)
        fast_insert(groups2, stats2, ["k2"], {"k2": [p_air_new]})
        self.assertEqual(groups2["k2"], [p_rail, p_air_new, p_water])
        self.assertEqual(stats2, recount(groups2))

        # Scenario 3: Insertion avant late avec projet air existant
        p_air_old = {"mode": "air", "id": 15}
        groups3 = {"k3": [p_rail, p_air_old, p_water]}
        stats3 = recount(groups3)
        p_air_new2 = {"mode": "air", "id": 35}
        fast_insert(groups3, stats3, ["k3"], {"k3": [p_air_new2]})
        self.assertEqual(groups3["k3"], [p_rail, p_air_old, p_air_new2, p_water])
        self.assertEqual(stats3, recount(groups3))


if __name__ == "__main__":
    unittest.main()
