"""Tests de contrat pour PO-02 (échéance de publication propre à chaque vivier modal)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read_nut(name):
    return (AI / name).read_text(encoding="utf-8")


class TestPO02Expiry(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info = read_nut("info.nut")
        self.assertIn('"po02_independent_expiry"', info)
        block = re.search(r'AddSetting\(\{\s*name = "po02_independent_expiry"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "Bloc AddSetting po02_independent_expiry manquant")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 1", body)
        self.assertIn("easy_value = 0", body)
        self.assertIn("medium_value = 0", body)
        self.assertIn("hard_value = 0", body)
        self.assertIn("custom_value = 0", body)

    def test_globals_and_loader(self):
        globals_pre = read_nut("globals_pre.nut")
        self.assertIn("PO02_INDEPENDENT_EXPIRY <- 0;", globals_pre)
        self.assertIn("PO02_LAST_PUBLISH_DATE <- { air = 0, rail = 0, road = 0, water = 0, fleet = 0 };", globals_pre)
        settings = read_nut("settings.nut")
        self.assertIn('PO02_INDEPENDENT_EXPIRY = AIController.GetSetting("po02_independent_expiry") == 1 ? 1 : 0;', settings)

    def test_po01c_regen_ttl_and_acknowledge(self):
        po_regen = read_nut("po01c_regen.nut")
        self.assertIn("PO02_INDEPENDENT_EXPIRY", po_regen)
        self.assertIn("PO02_LAST_PUBLISH_DATE", po_regen)
        self.assertIn('(mode == "water") ? 90 : 30', po_regen)
        self.assertIn("now - lastPub >= ttl", po_regen)
        # Vérification dans OpexPO01CAcknowledge
        self.assertIn("if (mode in PO02_LAST_PUBLISH_DATE) PO02_LAST_PUBLISH_DATE[mode] = now;", po_regen)

    def test_persist_support(self):
        persist = read_nut("persist.nut")
        self.assertIn("po02LastPublishDate", persist)
        self.assertIn("PO02_INDEPENDENT_EXPIRY", persist)

    def test_fleet_slot_full_save_and_ungated_load(self):
        """Contrat : le slot fleet existe, le save complet ecrit la meme cle,
        et Load ne depend pas de PO02_INDEPENDENT_EXPIRY (encore a 0)."""
        globals_pre = read_nut("globals_pre.nut")
        slot = globals_pre.split("PO02_LAST_PUBLISH_DATE <- ", 1)[1].split(";", 1)[0]
        self.assertIn("fleet = 0", slot)
        persist = read_nut("persist.nut")
        self.assertIn("saveObj.po02LastPublishDate <- PO02_LAST_PUBLISH_DATE;", persist)
        self.assertIn("shortSave.po02LastPublishDate <- PO02_LAST_PUBLISH_DATE;", persist)
        self.assertNotIn(
            'if (PO02_INDEPENDENT_EXPIRY && ("po02LastPublishDate" in data)',
            persist,
        )
        load = persist.split("function OpexAI::Load", 1)[1]
        self.assertIn('("po02LastPublishDate" in data)', load)
        self.assertIn("fleet = 0", load)

    def test_hygiene_no_forbidden_constructs(self):
        for name in ("po01c_regen.nut", "persist.nut"):
            content = read_nut(name)
            self.assertNotIn(".find(", content, f".find( interdit dans {name}")
