from pathlib import Path
import sys
import tempfile
import unittest

SWEEPS_DIR = Path(__file__).resolve().parent
if str(SWEEPS_DIR) not in sys.path:
    sys.path.insert(0, str(SWEEPS_DIR))

import repo_stats_opexai as rso


class TestClassifyLines(unittest.TestCase):
    """Tests de la classification des lignes par langage."""

    def test_squirrel_comments_strings_and_blanks(self):
        text = "\n".join([
            "/* commentaire bloc début",
            "",
            "   fin du bloc */",
            "local a = 1; // commentaire en fin de ligne (compte en code)",
            "// commentaire mono-ligne seul",
            "# commentaire avec diese seul",
            'local s1 = "// pas un commentaire dans chaine";',
            'local s2 = "/* pas un bloc */";',
            'local s3 = "chaine avec \\"//\\" echappe";',
            "/* inline */ local b = 2; /* autre inline */",
            "",
        ])
        # 11 lignes définies :
        # L0: /* comment -> comment (1)
        # L1: '' dans bloc -> blank (1)
        # L2: fin */ -> comment (2)
        # L3: local a = 1; // com -> code (1)
        # L4: // com -> comment (3)
        # L5: # com -> comment (4)
        # L6: local s1 = ... -> code (2)
        # L7: local s2 = ... -> code (3)
        # L8: local s3 = ... -> code (4)
        # L9: /* inline */ local b = 2; -> code (5)
        # L10: '' final non splitte par splitlines
        blank, comment, code = rso.classify_lines(text, "Squirrel")
        self.assertEqual((blank, comment, code), (1, 4, 5))

    def test_markdown_classification(self):
        text = "\n".join([
            "# Titre",
            "",
            "<!-- commentaire markdown -->",
            "Paragraphe de texte",
        ])
        blank, comment, code = rso.classify_lines(text, "Markdown")
        self.assertEqual(blank, 1)
        self.assertEqual(comment, 1)
        self.assertEqual(code, 2)

    def test_json_and_shell_classification(self):
        json_text = '{\n  "key": "value"\n}\n'
        b, c, k = rso.classify_lines(json_text, "JSON")
        self.assertEqual((b, c, k), (0, 0, 3))

        sh_text = "#!/bin/bash\n# commentaire\necho 'bonjour'\n"
        b, c, k = rso.classify_lines(sh_text, "Bourne Shell")
        self.assertEqual((b, c, k), (0, 2, 1))


class TestStripSquirrelCode(unittest.TestCase):
    """Tests du nettoyage du code Squirrel avant analyse statique."""

    def test_strip_comments_and_strings(self):
        sample = (
            'local x = AITile.GetSlope(tile); // AIMap.IsValidTile(0)\n'
            'local msg = "AIRail.BuildRail(0, 0, 0)";\n'
            '/* AIAirport.AT_SMALL\n'
            '   AICompany.GetBankBalance(0) */\n'
            'local y = AITile.SLOPE_FLAT;\n'
        )
        cleaned = rso.strip_squirrel_code(sample)

        # Les symboles réels de code doivent subsister
        self.assertIn("AITile.GetSlope", cleaned)
        self.assertIn("AITile.SLOPE_FLAT", cleaned)

        # Les symboles masqués par commentaires ou chaînes doivent avoir disparu
        self.assertNotIn("AIMap.IsValidTile", cleaned)
        self.assertNotIn("AIRail.BuildRail", cleaned)
        self.assertNotIn("AIAirport.AT_SMALL", cleaned)
        self.assertNotIn("AICompany.GetBankBalance", cleaned)


class TestApiAnalysisOnFixtures(unittest.TestCase):
    """Tests de l'analyse statique NoAI sur de petites fixtures."""

    def setUp(self):
        self.mock_api = [
            ("class", "AITile", ""),
            ("static", "AITile", "GetSlope"),
            ("const", "AITile", "SLOPE_FLAT"),
            ("class", "AIAirport", ""),
            ("static", "AIAirport", "IsValidAirport"),
            ("const", "AIAirport", "AT_SMALL"),
            ("class", "AIList", ""),
            ("method", "AIList", "Valuate"),
            ("class", "AIController", ""),
            ("static", "AIController", "Sleep"),
        ]

    def test_fixture_call_counts_and_exclusion(self):
        fixture_code = "\n".join([
            "local t = AITile();",
            "local s = AITile.GetSlope(t);",
            "if (s == AITile.SLOPE_FLAT) {",
            "    local l = AIList();",
            "    l.Valuate(func);",
            "    Sleep(1);",
            "}",
            'local fake1 = "AIAirport.IsValidAirport(0)";',
            'local fake2 = "AIAirport.AT_SMALL";',
            "// AIAirport.IsValidAirport(1);",
            "# AIAirport.AT_SMALL;",
            "/* AIAirport.IsValidAirport(2); */",
        ])

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.nut"
            file_path.write_text(fixture_code, encoding="utf-8")

            stats = rso.analyze_api_usage([file_path], self.mock_api)

            # Éléments utilisés :
            # - class AITile (1)
            # - static AITile.GetSlope (1)
            # - const AITile.SLOPE_FLAT (1)
            # - class AIList (1)
            # - method AIList.Valuate (1)
            # - static AIController.Sleep (1)
            # Total utilisés = 6 / 10
            self.assertEqual(stats["total_api"], 10)
            self.assertEqual(stats["used_count"], 6)
            self.assertEqual(stats["total_calls"], 6)
            self.assertAlmostEqual(stats["coverage_pct"], 60.0)

            # AIAirport ne doit pas avoir d'appels
            top_classes = {r["class"]: r for r in stats["top_20"]}
            self.assertIn("AITile", top_classes)
            self.assertEqual(top_classes["AITile"]["calls"], 3)
            self.assertEqual(top_classes["AITile"]["used_items"], 3)
            self.assertEqual(top_classes["AIAirport"]["calls"], 0)


class TestRealRepoIntegration(unittest.TestCase):
    """Tests d'intégration sur les données réelles du dépôt OpexAI."""

    def test_load_real_api_inventory(self):
        api = rso.load_api_inventory()
        self.assertEqual(len(api), 1167)
        kinds = {r[0] for r in api}
        self.assertEqual(kinds, {"class", "const", "method", "static"})

    def test_real_repo_line_and_api_stats(self):
        files = rso.get_tracked_files()
        self.assertEqual(len(files), 77)

        line_stats = rso.compute_line_stats(files)
        self.assertEqual(line_stats["summary"]["files"], 77)
        self.assertEqual(line_stats["summary"]["code"], 45008)
        self.assertEqual(line_stats["summary"]["comment"], 5802)
        self.assertEqual(line_stats["summary"]["blank"], 2874)
        self.assertEqual(line_stats["summary"]["total"], 53684)

        api = rso.load_api_inventory()
        api_stats = rso.analyze_api_usage(files, api)
        self.assertEqual(api_stats["total_api"], 1167)
        self.assertEqual(api_stats["used_count"], 466)
        self.assertAlmostEqual(api_stats["coverage_pct"], 39.93, places=2)
        self.assertEqual(api_stats["total_calls"], 5682)

        # Top 5 des classes
        top_names = [r["class"] for r in api_stats["top_20"][:5]]
        self.assertEqual(top_names, ["AIMap", "AIDate", "AIVehicle", "AITile", "AIRail"])

    def test_generated_file_matches_pipeline(self):
        """Vérifie que python3 sweeps/repo_stats_opexai.py régénère exactement docs/repo_stats_opexai.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_out = Path(tmpdir) / "repo_stats.md"
            _, _, generated_text = rso.run_pipeline(output_file=tmp_out)

            existing_doc = rso.DEFAULT_OUT_FILE.read_text(encoding="utf-8")
            self.assertEqual(generated_text, existing_doc)


class TestInstanceMethodAttribution(unittest.TestCase):
    """Un appel .Nom( n'est credite qu'aux classes referencees, une seule fois."""

    def stats(self, code):
        api = [("class", "AIList", ""), ("method", "AIList", "Count"),
               ("class", "AIEventFoo", ""), ("method", "AIEventFoo", "GetVehicleID"),
               ("class", "AIEventBar", ""), ("method", "AIEventBar", "GetVehicleID"),
               ("static", "AIStation", "GetStationID"), ("method", "AIEventBar", "GetStationID")]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "main.nut"
            path.write_text(code, encoding="utf-8")
            return rso.analyze_api_usage([path], api)

    def test_unreferenced_class_gets_nothing(self):
        stats = self.stats("local l = AIList(); l.Count(); e.GetVehicleID();")
        calls = {r["class"]: r["calls"] for r in stats["top_20"]}
        self.assertEqual(calls.get("AIList"), 2)  # constructeur + Count
        self.assertFalse(calls.get("AIEventFoo") or calls.get("AIEventBar"))

    def test_shared_name_counted_once_as_ambiguous(self):
        stats = self.stats("AIEventFoo.Convert(e); AIEventBar.Convert(e); e.GetVehicleID();")
        calls = {r["class"]: r["calls"] for r in stats["top_20"]}
        self.assertEqual(calls.get(rso.AMBIGUOUS_OWNER), 1)

    def test_static_receiver_is_not_an_instance_call(self):
        stats = self.stats("AIEventBar.Convert(e); AIStation.GetStationID(t);")
        self.assertEqual(stats["by_kind"]["method"]["calls"], 0)
        self.assertEqual(stats["by_kind"]["static"]["calls"], 1)


if __name__ == "__main__":
    unittest.main()
