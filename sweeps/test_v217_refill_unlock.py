"""sweeps/test_v217_refill_unlock.py - Contrats du reglage v217_refill_unlock.

Verifie :
1. Declaration du reglage v217_refill_unlock dans info.nut (0/1/2, defaut 0 aux 4 difficultes).
2. Lecture unique et bornee dans settings.nut.
3. Declarations globales dans globals_pre.nut (V217_REFILL_UNLOCK, V217_LAST_TRY_DATE, V217_SKIPPED_MONTH).
4. Persistance robuste au Save/Load dans persist.nut et main.nut.
5. Mode 0 : chemin identique au comportement historique (verrou mensuel immediat, inerte).
6. Mode 1 : verrou mensuel seulement sur refill effectif, nouvel essai autorise tous les 7 jours sur SKIP.
7. Mode 2 : Mode 1 + enchainement sur cargo fret suivant si < V217_POOL_MIN startables (au plus 2 cargos).
8. Journal V217_UNLOCK strictement garde sous DECISION_LOG (bit 256 de probes) avec tous les champs requis.
"""

from pathlib import Path
import re
import unittest

AI_DIR = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI_DIR / name).read_text(encoding="utf-8")


def function_body(source, name):
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


class TestV217RefillUnlock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI_DIR.glob("*.nut")}
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.globals = cls.sources["globals_pre.nut"]
        cls.orch = cls.sources["orchestrator.nut"]
        cls.persist = cls.sources["persist.nut"]
        cls.main = cls.sources["main.nut"]
        cls.refill_body = function_body(cls.orch, "OpexAI::_v217RailRefill")

    def test_setting_declaration_in_info(self):
        """v217_refill_unlock doit etre declare avec min 0, max 2, et defaut 0 aux 4 difficultes."""
        self.assertIn('name = "v217_refill_unlock"', self.info)
        start = self.info.index('name = "v217_refill_unlock"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 2", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b")
        self.assertIn("flags = 0", block)

    def test_setting_read_once_and_bounded(self):
        """GetSetting('v217_refill_unlock') doit etre lu exactement une fois et borne 0..2."""
        reads = sum(t.count('GetSetting("v217_refill_unlock")') for t in self.sources.values())
        self.assertEqual(reads, 1, "v217_refill_unlock doit etre lu une seule fois")
        self.assertIn('local refillUnlock = AIController.GetSetting("v217_refill_unlock");', self.settings)
        self.assertRegex(
            self.settings,
            r"V217_REFILL_UNLOCK = \(refillUnlock != null && refillUnlock >= 0 && refillUnlock <= 2\) \? refillUnlock : 0;"
        )

    def test_globals_declared(self):
        """Les globales V217 doivent etre declarees dans globals_pre.nut."""
        self.assertIn("V217_REFILL_UNLOCK <- 0;", self.globals)
        self.assertIn("V217_LAST_TRY_DATE <- -1;", self.globals)
        self.assertIn("V217_SKIPPED_MONTH <- -1;", self.globals)

    def test_save_load_persistence(self):
        """Les etats V217 doivent etre persistances et reconcilies sans dependre du reset de Start()."""
        # Save dans shortSave et saveObj
        for target in ("shortSave", "saveObj"):
            self.assertIn(f"if (V217_LAST_MONTH >= 0) {target}.v217LastMonth <- V217_LAST_MONTH;", self.persist)
            self.assertIn(f"if (V217_LAST_TRY_DATE >= 0) {target}.v217LastTryDate <- V217_LAST_TRY_DATE;", self.persist)
            self.assertIn(f"if (V217_SKIPPED_MONTH >= 0) {target}.v217SkippedMonth <- V217_SKIPPED_MONTH;", self.persist)
        # Load dans OpexAI::Load
        self.assertIn('this._reloadV217LastMonth = ("v217LastMonth" in data) ? data.v217LastMonth : -1;', self.persist)
        self.assertIn('this._reloadV217LastTryDate = ("v217LastTryDate" in data) ? data.v217LastTryDate : -1;', self.persist)
        self.assertIn('this._reloadV217SkippedMonth = ("v217SkippedMonth" in data) ? data.v217SkippedMonth : -1;', self.persist)
        # Reconcile apres OpexLoadSettings
        self.assertIn("if (this._reloadV217LastMonth >= 0) V217_LAST_MONTH = this._reloadV217LastMonth;", self.persist)
        self.assertIn("if (this._reloadV217LastTryDate >= 0) V217_LAST_TRY_DATE = this._reloadV217LastTryDate;", self.persist)
        self.assertIn("if (this._reloadV217SkippedMonth >= 0) V217_SKIPPED_MONTH = this._reloadV217SkippedMonth;", self.persist)

    def test_mode_0_path_identity(self):
        """En mode 0, le verrou mensuel V217_LAST_MONTH = ym est pose immediatement."""
        body = self.refill_body
        self.assertIn("if (V217_LAST_MONTH == ym) return;", body)
        self.assertIn("if (V217_REFILL_UNLOCK == 0) {", body)
        mode0_block = body[body.index("if (V217_REFILL_UNLOCK == 0) {"):body.index("} else {")]
        self.assertIn("V217_LAST_MONTH = ym;", mode0_block)

    def test_mode_1_unlock_guards_and_cadence(self):
        """En mode 1, un SKIP n'interdit pas un essai ulterieur (borne a 7 jours), verrou seulement sur refill."""
        body = self.refill_body
        # Cadence de 7 jours
        self.assertIn("(date - V217_LAST_TRY_DATE) < 7) return;", body)
        # En mode 1+, les SKIP posent V217_LAST_TRY_DATE mais ne posent PAS V217_LAST_MONTH
        cash_skip = body[body.index("if (cash <= V217_IDLE_CASH_MIN) {"):body.index("local startable = 0;")]
        self.assertIn("V217_LAST_TRY_DATE = date;", cash_skip)
        self.assertIn("V217_SKIPPED_MONTH = ym;", cash_skip)
        self.assertNotIn("V217_LAST_MONTH = ym;", cash_skip)

        pool_skip = body[body.index("if (startable >= V217_POOL_MIN) {"):body.index("local freightCargos")]
        self.assertIn("V217_LAST_TRY_DATE = date;", pool_skip)
        self.assertIn("V217_SKIPPED_MONTH = ym;", pool_skip)
        self.assertNotIn("V217_LAST_MONTH = ym;", pool_skip)

        # Le verrou mensuel n'est pose qu'apres les gardes, quand le refill demarre
        lock_idx = body.index("if (V217_REFILL_UNLOCK > 0) {\n    V217_LAST_MONTH = ym;\n    V217_LAST_TRY_DATE = date;\n  }")
        self.assertGreater(lock_idx, body.index("startable >= V217_POOL_MIN"))

    def test_mode_2_multi_cargo_chaining_and_cap(self):
        """En mode 2, si cargo 1 donne < V217_POOL_MIN startables, enchaine sur le suivant (max 2 cargos)."""
        body = self.refill_body
        self.assertIn("if (evalPass == 1 && V217_REFILL_UNLOCK == 2 && freightCargos.len() > 1)", body)
        self.assertIn("if (startablePass1 < V217_POOL_MIN)", body)
        self.assertIn("cargoIndices.append((nextCargo + 1) % freightCargos.len());", body)
        # Verification que les candidats du cargo 1 sont fusionnes avec ceux du cargo 2
        self.assertIn("OpexProjectRememberAll(this._projects.candidateGroups, p, scratch);", body)
        self.assertIn("OpexMergeRailCandidateSet(firstRail, this._projects.rail);", body)
        self.assertIn("OpexReselectProjects(", body)

    def test_unlock_decision_log_format_and_guard(self):
        """V217_UNLOCK doit etre strictement garde sous DECISION_LOG et bit 256 avec date, mode, raison, cargo(s), candidats."""
        body = self.refill_body
        self.assertIn("if (V217_REFILL_UNLOCK > 0 && DECISION_LOG)", body)
        start = body.index('OpexDecide("V217_UNLOCK",')
        log_call = body[start:body.index(");", start)]
        self.assertIn('"date=" + date', log_call)
        self.assertIn('" mode=" + V217_REFILL_UNLOCK', log_call)
        self.assertIn('" reason=" + unlockReason', log_call)
        self.assertIn('" cargo=" + unlockCargos', log_call)
        self.assertIn('" cargos=" + unlockCargos', log_call)
        self.assertIn('" candidates=" + n', log_call)
        self.assertIn('" kept=" + n', log_call)


if __name__ == "__main__":
    unittest.main()
