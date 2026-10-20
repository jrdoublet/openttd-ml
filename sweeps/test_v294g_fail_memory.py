"""Contrats statiques et unitaires de V294g : memoire d'echec rail par lieu et expiration par motif.

Verifie :
1. Declaration du reglage v294_rail_fail_memory (0..2) avec defaut 0 aux 4 difficultes.
2. Lecture unique dans settings.nut vers la globale V294_RAIL_FAIL_MEMORY.
3. Declaration de la globale V294_RAIL_FAIL_MEMORY a 0 dans globals_pre.nut.
4. Declaration des constantes litterales d'expiration V294G_EXPIRY_* dans globals_pre.nut.
5. Memoire des lieux : presence de _abandonedPlaces dans main.nut, lines.nut, persist.nut.
6. Gardes strictes V294_RAIL_FAIL_MEMORY > 0 autour des filtres de lieux et rejets v294g_place.
7. Persistance : sauvegarde et chargement de abandonedPlaces avec repli sur table vide si absent.
8. Cooldowns par motif V294g : SITE* (730 j), ABND (180 j), NOPA (365 j), STNFAIL (90 j).
9. Journalisation sous DECISION_LOG : V294G event=place_ban|place_skip|expire.
10. Absence de closures dans les fichiers modifies.
"""
from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _read(rel_path):
    return (AI / rel_path).read_text(encoding="utf-8")


def _function_body(source, signature):
    idx = source.find(signature)
    if idx < 0:
        return ""
    brace = source.find("{", idx)
    if brace < 0:
        return ""
    depth = 0
    pos = brace
    while pos < len(source):
        char = source[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:pos]
        pos += 1
    return ""


class TestV294gFailMemory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.relative_to(AI).as_posix(): p.read_text(encoding="utf-8")
                       for p in AI.rglob("*.nut")}
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.globals_pre = cls.sources["globals_pre.nut"]
        cls.main = cls.sources["main.nut"]
        cls.lines = cls.sources["lines.nut"]
        cls.task_rail = cls.sources["task_rail.nut"]
        cls.persist = cls.sources["persist.nut"]
        cls.candidates = cls.sources["candidates.nut"]
        cls.candidates_v276 = cls.sources["candidates_v276.nut"]
        cls.projects = cls.sources["projects.nut"]
        cls.orchestrator = cls.sources["orchestrator.nut"]

    def test_setting_declared_default_zero_four_levels(self):
        m = re.search(r'AddSetting\(\{\s*name = "v294_rail_fail_memory",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(m, "v294_rail_fail_memory doit etre declare dans info.nut")
        block = m.group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b", f"{level}_value doit valoir 0")
        self.assertIn("min_value = 0, max_value = 2", block)

    def test_setting_loaded_once(self):
        # Lecture unique dans settings.nut
        reads = re.findall(r'GetSetting\("v294_rail_fail_memory"\)', self.settings)
        self.assertEqual(len(reads), 1, "v294_rail_fail_memory doit etre lu exactement une fois dans settings.nut")
        # Aucune autre lecture dans le reste du code
        for path, content in self.sources.items():
            if path == "settings.nut":
                continue
            self.assertNotIn('GetSetting("v294_rail_fail_memory")', content,
                             f"Lecture inattendue de v294_rail_fail_memory dans {path}")

    def test_global_declared_in_globals_pre(self):
        self.assertIn("V294_RAIL_FAIL_MEMORY <- 0;", self.globals_pre)

    def test_expiry_constants_literal_integers(self):
        # Verifier les constantes d'expiration V294g (constantes litterales sans calcul)
        constants = {
            "V294G_EXPIRY_SITE_DAYS": 730,
            "V294G_EXPIRY_ABND_DAYS": 180,
            "V294G_EXPIRY_NOPA_DAYS": 365,
            "V294G_EXPIRY_STNFAIL_DAYS": 90,
            "V294G_EXPIRY_DEFAULT_DAYS": 365,
        }
        for name, expected_val in constants.items():
            pattern = rf"\bconst\s+{name}\s*=\s*(\d+);"
            m = re.search(pattern, self.globals_pre)
            self.assertIsNotNone(m, f"Constante {name} manquante dans globals_pre.nut")
            self.assertEqual(int(m.group(1)), expected_val, f"Valeur de {name} incorrecte")

    def test_class_field_and_constructor_initialization(self):
        self.assertIn("_abandonedPlaces = null;", self.main)
        self.assertIn("this._abandonedPlaces = {};", self.main)

    def test_place_helpers_present_in_lines(self):
        self.assertIn("function OpexRailCandidatePlaceKey(", self.lines)
        self.assertIn("function OpexRailCandidateBannedPlace(", self.lines)
        self.assertIn("function OpexV294gReasonCooldown(", self.lines)
        self.assertIn("function OpexAI::_markPlaceAbandoned(", self.lines)
        self.assertIn("function OpexAI::_pruneAbandonedPlaces(", self.lines)

    def test_reason_cooldown_values(self):
        body = _function_body(self.lines, "function OpexV294gReasonCooldown(reason)")
        self.assertTrue(body, "OpexV294gReasonCooldown doit exister")
        self.assertIn("V294G_EXPIRY_SITE_DAYS", body)
        self.assertIn("V294G_EXPIRY_ABND_DAYS", body)
        self.assertIn("V294G_EXPIRY_NOPA_DAYS", body)
        self.assertIn("V294G_EXPIRY_STNFAIL_DAYS", body)
        self.assertIn("V294G_EXPIRY_DEFAULT_DAYS", body)

    def test_guards_in_task_rail_build_project(self):
        body = _function_body(self.task_rail, "function OpexAI::_tryBuildRailProject(")
        self.assertTrue(body, "_tryBuildRailProject doit exister")
        # Garde mode 1 : verification OpexRailCandidateBannedPlace
        self.assertIn("V294_RAIL_FAIL_MEMORY > 0", body)
        self.assertIn("OpexRailCandidateBannedPlace(candidate, this._abandonedPlaces)", body)
        self.assertIn('"v294g_place"', body)

    def test_guards_in_task_rail_record_attempt(self):
        body = _function_body(self.task_rail, "function OpexAI::_recordRailAttempt(")
        self.assertTrue(body, "_recordRailAttempt doit exister")
        self.assertIn("V294_RAIL_FAIL_MEMORY > 0", body)
        self.assertIn("this._markPlaceAbandoned", body)

    def test_guards_in_orchestrator(self):
        body = _function_body(self.orchestrator, "function OpexAI::_v217RailRefill(")
        self.assertTrue(body, "_v217RailRefill doit exister")
        self.assertIn("V294_RAIL_FAIL_MEMORY > 0", body)
        self.assertIn("OpexRailCandidateBannedPlace(c, this._abandonedPlaces)", body)

    def test_save_and_load_persistence(self):
        body_save = _function_body(self.persist, "function OpexAI::Save()")
        self.assertTrue(body_save, "Save() doit exister")
        self.assertIn("abandonedPlaces = this._abandonedPlaces != null ? this._abandonedPlaces : {}", body_save)
        self.assertIn("abandonedPlaces = abandonedPlaces", body_save)

        body_load = _function_body(self.persist, "function OpexAI::Load(version, data)")
        self.assertTrue(body_load, "Load() doit exister")
        self.assertIn('"abandonedPlaces" in data', body_load)
        # Fallback a table vide si absent
        self.assertIn("this._abandonedPlaces = {};", body_load)

    def test_candidate_generation_filters(self):
        body_pax = _function_body(self.candidates, "function OpexPaxCandidates(")
        self.assertTrue(body_pax, "OpexPaxCandidates doit exister")
        self.assertIn("V294_RAIL_FAIL_MEMORY > 0 && abandonedPlaces != null", body_pax)

        body_freight = _function_body(self.candidates, "function OpexFreightCandidates(")
        self.assertTrue(body_freight, "OpexFreightCandidates doit exister")
        self.assertIn("V294_RAIL_FAIL_MEMORY > 0 && abandonedPlaces != null", body_freight)

    def test_decision_log_events(self):
        # DECISION_LOG tags: event=place_ban, event=place_skip, event=expire
        self.assertIn('event=place_ban', self.lines)
        self.assertIn('event=expire', self.lines)
        self.assertIn('event=place_skip', self.task_rail)
        self.assertIn('"V294G"', self.lines)
        self.assertIn('"V294G"', self.task_rail)

    def test_no_closures_in_modified_methods(self):
        # Verifier qu'aucune closure n'est definie dans les nouvelles fonctions V294g
        for fn in (
            "function OpexRailCandidatePlaceKey(",
            "function OpexRailCandidateBannedPlace(",
            "function OpexV294gReasonCooldown(",
            "function OpexAI::_markPlaceAbandoned(",
            "function OpexAI::_pruneAbandonedPlaces(",
        ):
            body = _function_body(self.lines, fn)
            self.assertTrue(body, f"{fn} doit exister dans lines.nut")
            anonymous = re.findall(r'function\s*\([^\)]*\)\s*\{', body)
            self.assertEqual(len(anonymous), 0, f"Closure anonyme detectee dans {fn}")


if __name__ == "__main__":
    unittest.main()
