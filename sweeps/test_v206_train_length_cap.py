"""V282 : contrats source du correctif V206 (rame bornee par vehicle.max_train_length) sur V280."""
import pathlib
import re
import unittest

AI = pathlib.Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class V206TrainLengthCapTest(unittest.TestCase):
    def test_setting_declared_default_zero(self):
        info = read("info.nut")
        block = re.search(r'name = "v206_train_length_cap".*?\}\);', info, re.S).group(0)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value", "default_value"):
            self.assertRegex(block, key + r" = 0\b")
        self.assertIn("max_value = 2", block)

    def test_setting_loaded(self):
        self.assertIn("V206_TRAIN_LENGTH_CAP <- 0;", read("globals_pre.nut"))
        self.assertIn('AIController.GetSetting("v206_train_length_cap")', read("settings.nut"))

    def test_consist_cap_all_cargos_under_guard(self):
        economy = read("economy.nut")
        self.assertIn("if (V206_TRAIN_LENGTH_CAP > 0 && catalog.maxTrainLength > 0) {", economy)
        self.assertIn("OpexRailNominalMaxWagons(catalog.maxTrainLength)", economy)
        # La borne V207 (pax) reste intacte.
        self.assertIn('if (kind == "pax" && OpexV207Active() && catalog.maxTrainLength > 0) {', economy)

    def test_platform_cap_only_in_mode_two(self):
        catalog = read("catalog.nut")
        self.assertIn("if (V206_TRAIN_LENGTH_CAP >= 2 && this.maxTrainLength >= 1 "
                      "&& this.maxTrainLength < this.platformLength) {", catalog)
        self.assertIn('this.platformLength = AIGameSettings.GetValue("station.station_spread");', catalog)


if __name__ == "__main__":
    unittest.main()
