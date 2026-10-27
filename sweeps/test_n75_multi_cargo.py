"""N75-MC default-on contracts; an OpenTTD smoke validates Squirrel.

The legacy 58 setting declarations and PO01C bytes remain protected by
historical_bytes, never by replacing historical SHA literals.
"""

from pathlib import Path
import re
import unittest

from n75_mc_legacy import historical_bytes, historical_info

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class N75MultiCargoContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.scheduler = source("scheduler.nut")
        cls.globals_pre = source("globals_pre.nut")
        cls.persist = source("persist.nut")
        cls.orchestrator = source("orchestrator.nut")

    def test_setting_on_for_all_difficulties_and_one_read(self):
        blocks = re.findall(r'AddSetting\(\{\s*name = "n75_multi_cargo".*?\}\);',
                            self.info, re.S)
        self.assertEqual(len(blocks), 1)
        setting = blocks[0]
        self.assertIn('min_value = 0, max_value = 2', setting)
        for d in ('easy', 'medium', 'hard', 'custom'):
            self.assertRegex(setting, rf'{d}_value\s*=\s*2\b')
        self.assertEqual(self.settings.count('AIController.GetSetting("n75_multi_cargo")'), 1)
        # 58 historiques + options connues, DIST-BORNES unified OFF, +3 V233L, +1 AIR.
        self.assertEqual(self.info.count("AddSetting("), 78)
        self.assertEqual(historical_info(self.info).count("AddSetting("), 58)
        self.assertIn('N75_MULTI_CARGO <- 0;', self.globals_pre)
        self.assertIn('N75_MULTI_CARGO = (n75MultiCargo >= 1 && n75MultiCargo <= 2)', self.settings)

    def test_preserves_precisely_the_original_setting_bytes(self):
        for file in ('info.nut', 'settings.nut'):
            original = historical_bytes(file, (AI / file).read_bytes())
            self.assertNotIn(b'n75_multi_cargo', original)
        self.assertIn('V217_RAIL_REFILL = (railRefill != null', self.settings)
        self.assertIn('V276_CAND_SLICES = (v276 == 3) ? (bigMap ? 2 : 0) : v276;',
                      self.settings)

    def test_default_v217_one_then_n75_and_small_v276_zero(self):
        v217 = re.search(r'AddSetting\(\{\s*name = "v217_rail_refill".*?\}\);',
                         self.info, re.S).group()
        for d in ('easy', 'medium', 'hard', 'custom'):
            self.assertRegex(v217, rf'{d}_value\s*=\s*1\b')
        self.assertLess(self.scheduler.index('if (V217_RAIL_REFILL > 0) this._v217RailRefill();'),
                        self.scheduler.index('if (N75_MULTI_CARGO > 0) OpexN75MultiCargoRefill(this);'))
        self.assertIn('if (V217_RAIL_REFILL > 0 && V217_LAST_MONTH != month) return;',
                      self.scheduler)
        self.assertIn('V276_CAND_SLICES > 0', self.scheduler)

    def test_no_unregistered_class_extension_or_change_to_legacy_orchestrator(self):
        self.assertIn('function OpexN75MultiCargoRefill(ai)', self.scheduler)
        self.assertNotIn('function OpexAI::_n75MultiCargoRefill()', self.scheduler)
        self.assertNotIn('n75_multi_cargo', self.orchestrator)
        self.assertNotIn('n75_multi_cargo', source("main.nut"))

    def test_guards_time_active_work_cash_and_real_portfolio(self):
        code = self.scheduler
        for fragment in (
            'N75_MULTI_CARGO <= 0', 'year < OPEX_START_YEAR + 2',
            'STAGED_BOOTSTRAP && ai._generationStage < OPEX_STAGE_COMPLETE',
            'ai._railSearch != null || ai._activeWorker != null',
            'cash <= V217_IDLE_CASH_MIN || OpexN75FundedRail(ai, cash) > 0',
            'OpexProjectFinanceCapital(project) > cash',
            'project.profitAnnual <= 0',
            'ai._abandonedPairs != null',
            'close.hard < 0 && close.blocking < 0',
        ):
            self.assertIn(fragment, code)

    def test_shadow_no_regeneration_and_on_bounded_extra_attempt(self):
        shadow = self.scheduler.index('if (N75_MULTI_CARGO == 1)')
        regeneration = self.scheduler.index('OpexGenerateModeProjects(', shadow)
        self.assertLess(self.scheduler.index('return;', shadow), regeneration)
        self.assertIn('local attempts = V217_RAIL_REFILL > 0 ? 1 : 2;', self.scheduler)
        self.assertIn('for (local j = 0; j < attempts; j++)', self.scheduler)
        self.assertIn('local scratch = clone ai._projects;', self.scheduler)
        self.assertIn('OpexGenerateModeProjects(scratch,', self.scheduler)
        self.assertIn('ai._projects = OpexApplyGeneratedModeProjects(ai._projects, generated,', self.scheduler)
        self.assertIn('if (!found) {', self.scheduler)
        self.assertNotIn('OpexRegenerateModeProjects(', self.scheduler[:regeneration + 1000])
        self.assertIn('V217_REGEN_NO_PAX = previousNoPax;', self.scheduler)
        self.assertIn('OpexOpsMeasureEnd(mark)', self.scheduler)

    def test_load_and_both_saves_preserve_on_only_month(self):
        self.assertIn('N75_MC_SAVED_MONTH <- -1;', self.globals_pre)
        self.assertIn('N75_MC_LAST_MONTH = (N75_MULTI_CARGO > 0) ? N75_MC_SAVED_MONTH : -1;',
                      self.settings)
        self.assertIn('N75_MC_SAVED_MONTH = -1;', self.settings)
        self.assertIn('if (N75_MULTI_CARGO > 0) shortSave.n75McLastMonth <- N75_MC_LAST_MONTH;',
                      self.persist)
        self.assertIn('if (N75_MULTI_CARGO > 0) saveObj.n75McLastMonth <- N75_MC_LAST_MONTH;',
                      self.persist)
        self.assertIn('if (("n75McLastMonth" in data) && typeof data.n75McLastMonth == "integer")',
                      self.persist)


if __name__ == "__main__":
    unittest.main()
