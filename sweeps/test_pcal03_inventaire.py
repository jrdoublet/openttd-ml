#!/usr/bin/env python3
"""sweeps/test_pcal03_inventaire.py — Tests unitaires de déduplication des spans (PCAL-03).

Vérifie que les spans imbriqués (par=) calculent correctement :
- Le coût inclusif (total mesuré pour la balise)
- Le coût propre / exclusif (inclusif - somme des enfants directs)
- Les totaux de poste sommés sur les coûts propres sans double comptage
- L'option --inclusive pour préserver l'ancien comportement si demandé
"""

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from sweeps.pcal03_inventaire import (
    EngineLogParser, compile_pcal03_inventory, deduplicate_log_files, format_table,
)


class TestPcal03Deduplication(unittest.TestCase):
    def test_numeric_seed_aliases_cannot_double_opcode_totals(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            content = b"OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=air.plans op=100\n"
            files = [root / name for name in
                     ("reference_seed1_r0.log", "reference_seed01_r0.log")]
            for file in files:
                file.write_bytes(content)
            with self.assertRaisesRegex(ValueError, "identite de partie numerique ambigue"):
                deduplicate_log_files(files)

    def test_numeric_repeat_aliases_rejected_even_with_different_payloads(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = root / "reference_seed42_r0.log"
            second = root / "reference_seed42_r00.log.gz"
            first.write_bytes(b"OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=air.plans op=100\n")
            with gzip.open(second, "wb") as stream:
                stream.write(b"OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=air.plans op=500\n")
            with self.assertRaisesRegex(ValueError, "identite de partie numerique ambigue"):
                deduplicate_log_files([first, second])

    def test_numeric_aliases_across_independent_campaigns_do_not_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = []
            for directory_name, filename in (("campaign_a", "reference_seed1_r0.log"),
                                             ("campaign_b", "reference_seed01_r00.log")):
                directory = root / directory_name
                directory.mkdir()
                file = directory / filename
                file.write_text("OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=air.plans op=100\n",
                                encoding="utf-8")
                files.append(file)
            self.assertEqual(deduplicate_log_files(files), [p.resolve() for p in files])

    def test_same_basename_across_campaigns_keeps_two_file_years(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = []
            for campaign in ("campaign_a", "campaign_b"):
                directory = root / campaign
                directory.mkdir()
                path = directory / "reference_seed42_r0.log"
                path.write_text("OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=air.plans op=100\n",
                                encoding="utf-8")
                paths.append(path)
            parser = EngineLogParser()
            for path in deduplicate_log_files(paths):
                parser.parse_file(path)
            report = compile_pcal03_inventory(parser)
            self.assertEqual(report["summary"]["num_files"], 2)
            self.assertEqual(report["summary"]["years_simulated"], 2.0)
            self.assertEqual(report["posts"]["Poste 1"]["items"]["air.plans"]["total_ops"], 200)
            self.assertEqual(report["posts"]["Poste 1"]["items"]["air.plans"]["ops_per_year"], 100)

    def test_overlapping_years_from_same_named_logs_not_merged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            parser = EngineLogParser()
            for campaign, years in (("campaign_a", (1970, 1971)),
                                    ("campaign_b", (1971, 1972))):
                directory = root / campaign
                directory.mkdir()
                path = directory / "reference_seed42_r0.log"
                path.write_text("".join(
                    f"OPEX {year}-01-01 SPAN id={year} par=0 dep=0 n=air.plans op=100\n"
                    for year in years), encoding="utf-8")
                parser.parse_file(path)
            report = compile_pcal03_inventory(parser)
            self.assertEqual(report["summary"]["num_files"], 2)
            self.assertEqual(report["summary"]["years_simulated"], 4.0)
            self.assertEqual(report["summary"]["min_year"], 1970)
            self.assertEqual(report["summary"]["max_year"], 1972)
            self.assertEqual(report["posts"]["Poste 1"]["items"]["air.plans"]["ops_per_year"], 100)

    def test_distinct_names_same_year_keep_distinct_source_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            parser = EngineLogParser()
            for name in ("reference_seed42_r0.log", "variant_seed42_r0.log"):
                path = root / name
                path.write_text("OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=air.plans op=100\n",
                                encoding="utf-8")
                parser.parse_file(path)
            report = compile_pcal03_inventory(parser)
            self.assertEqual(report["summary"]["num_files"], 2)
            self.assertEqual(report["summary"]["years_simulated"], 2.0)
            self.assertEqual(report["posts"]["Poste 1"]["items"]["air.plans"]["ops_per_year"], 100)

    def test_profile_examples_use_current_single_mask(self):
        source = (Path(__file__).resolve().parent / "pcal03_inventaire.py").read_text(encoding="utf-8")
        doc = source.split('"""', 2)[1]
        self.assertIn('OpexAI[probes=39170]', doc)
        self.assertIn('--script-debug', doc)
        self.assertNotIn('OpexAI[probe_span_trace=', doc)
        self.assertEqual(39170, 2 | 256 | 2048 | 4096 | 32768)
        self.assertEqual(39170 & 1, 0)

    def test_guide_uses_only_current_probe_mask(self):
        guide = (Path(__file__).resolve().parent.parent / "docs" / "pcal03_inventaire_20261021.md").read_text(encoding="utf-8")
        commands = guide.split("### Protocole et commande", 1)[1].split("## 2.", 1)[0]
        self.assertIn('OpexAI[probes=39170]', commands)
        self.assertIn('--script-debug', commands)
        self.assertNotIn('OpexAI[probes=13]', commands)
        self.assertNotIn('OpexAI[probe_span_trace=', commands)

    def test_identical_plain_and_gzip_count_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            log = root / "reference_seed42_r0.log"
            content = b"OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=air.plans op=100\n"
            log.write_bytes(content)
            with gzip.open(root / (log.name + ".gz"), "wb") as stream:
                stream.write(content)
            chosen = deduplicate_log_files([log.with_suffix('.log.gz'), log, log])
            self.assertEqual(chosen, [log.resolve()])
            parser = EngineLogParser()
            for path in chosen:
                parser.parse_file(path)
            self.assertEqual(parser.spans["air.plans"]["calls"], 1)
            self.assertEqual(parser.spans["air.plans"]["exclusive_ops"], 100)

    def test_conflicting_plain_and_gzip_refused_even_if_totals_equal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            log = root / "reference_seed42_r0.log"
            log.write_bytes(b"OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=air.plans op=100\n")
            with gzip.open(root / (log.name + ".gz"), "wb") as stream:
                stream.write(b"OPEX 1970-01-02 SPAN id=1 par=0 dep=0 n=air.plans op=100\n")
            with self.assertRaisesRegex(ValueError, "copies de partie contradictoires"):
                deduplicate_log_files([log, root / (log.name + ".gz")])

    def test_same_game_name_in_two_campaigns_kept_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = []
            for name in ("reference", "variant"):
                directory = root / name
                directory.mkdir()
                log = directory / "reference_seed42_r0.log"
                log.write_text(f"OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n={name} op=100\n", encoding="utf-8")
                files.append(log)
            self.assertEqual(deduplicate_log_files(files), [path.resolve() for path in files])

    def test_synthetic_tree_deduplication(self):
        """Vérifie sur un arbre synthétique (parent + 2 enfants + petit-enfant)

        Arbre :
          parent (id=1, par=0, op=100)
            ├── child1 (id=2, par=1, op=40)
            │     └── grandchild (id=4, par=2, op=15)
            └── child2 (id=3, par=1, op=30)

        Attendu :
          parent      : incl=100, propre = 100 - (40 + 30) = 30
          child1      : incl=40,  propre = 40 - 15 = 25
          child2      : incl=30,  propre = 30 - 0 = 30
          grandchild  : incl=15,  propre = 15 - 0 = 15
          Total propre = 30 + 25 + 30 + 15 = 100 (= inclusif racine, 0 double comptage)
          Total ancien = 100 + 40 + 30 + 15 = 185 (+85 % de sur-comptage)
        """
        lines = [
            "OPEX 1970-01-01 SPAN id=4 par=2 dep=2 n=grandchild op=15\n",
            "OPEX 1970-01-01 SPAN id=2 par=1 dep=1 n=child1 op=40\n",
            "OPEX 1970-01-01 SPAN id=3 par=1 dep=1 n=child2 op=30\n",
            "OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=parent op=100\n",
        ]

        parser = EngineLogParser()
        for line in lines:
            parser.parse_line("test.log", line)
        parser.finalize()

        # Vérification par balise
        self.assertEqual(parser.spans["parent"]["inclusive_ops"], 100)
        self.assertEqual(parser.spans["parent"]["exclusive_ops"], 30)
        self.assertEqual(parser.spans["parent"]["calls"], 1)

        self.assertEqual(parser.spans["child1"]["inclusive_ops"], 40)
        self.assertEqual(parser.spans["child1"]["exclusive_ops"], 25)
        self.assertEqual(parser.spans["child1"]["calls"], 1)

        self.assertEqual(parser.spans["child2"]["inclusive_ops"], 30)
        self.assertEqual(parser.spans["child2"]["exclusive_ops"], 30)
        self.assertEqual(parser.spans["child2"]["calls"], 1)

        self.assertEqual(parser.spans["grandchild"]["inclusive_ops"], 15)
        self.assertEqual(parser.spans["grandchild"]["exclusive_ops"], 15)
        self.assertEqual(parser.spans["grandchild"]["calls"], 1)

        # Somme des coûts propres = exactement le coût racine
        total_exclusive = sum(s["exclusive_ops"] for s in parser.spans.values())
        self.assertEqual(total_exclusive, 100)

        # Somme des coûts inclusifs = ancien comportement avec doublons
        total_inclusive = sum(s["inclusive_ops"] for s in parser.spans.values())
        self.assertEqual(total_inclusive, 185)

    def test_order_independence(self):
        """Vérifie que l'ordre des lignes dans le journal ne change pas le calcul."""
        # Ordre direct (parent avant enfants, ex: orphan rescue)
        lines_direct = [
            "OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=parent op=100\n",
            "OPEX 1970-01-01 SPAN id=2 par=1 dep=1 n=child1 op=40\n",
            "OPEX 1970-01-01 SPAN id=3 par=1 dep=1 n=child2 op=30\n",
            "OPEX 1970-01-01 SPAN id=4 par=2 dep=2 n=grandchild op=15\n",
        ]
        parser = EngineLogParser()
        for line in lines_direct:
            parser.parse_line("direct.log", line)
        parser.finalize()

        self.assertEqual(parser.spans["parent"]["exclusive_ops"], 30)
        self.assertEqual(parser.spans["child1"]["exclusive_ops"], 25)
        self.assertEqual(parser.spans["child2"]["exclusive_ops"], 30)
        self.assertEqual(parser.spans["grandchild"]["exclusive_ops"], 15)

    def test_poste1_nested_air_spans_deduplication(self):
        """Vérifie la déduplication sur les vraies balises du Poste 1 (AIR).

        Exemple documenté dans PCAL-03 :
          loop.c121_catalog_resume (id=1, par=0, op=36500000)
            └── catalog.slice (id=2, par=1, op=36000000)
                  └── air.plans (id=3, par=2, op=14000000)
                        ├── air.new_pairs (id=4, par=3, op=6850000)
                        └── air.hub_site (id=5, par=3, op=2690000)
        """
        lines = [
            "OPEX 1970-02-01 SPAN id=4 par=3 dep=3 n=air.new_pairs op=6850000\n",
            "OPEX 1970-02-01 SPAN id=5 par=3 dep=3 n=air.hub_site op=2690000\n",
            "OPEX 1970-02-01 SPAN id=3 par=2 dep=2 n=air.plans op=14000000\n",
            "OPEX 1970-02-01 SPAN id=2 par=1 dep=1 n=catalog.slice op=36000000\n",
            "OPEX 1970-02-01 SPAN id=1 par=0 dep=0 n=loop.c121_catalog_resume op=36500000\n",
            # SPAN_AGG interne à air.plans
            "OPEX 1970-02-01 SPAN_AGG par=3 n=air.c121.demand cnt=10 op=3170000\n",
        ]

        parser = EngineLogParser()
        for line in lines:
            parser.parse_line("air.log", line)

        # 1. Mode par défaut (exclusif / propre)
        data_excl = compile_pcal03_inventory(parser, inclusive=False)
        p1_excl = data_excl["posts"]["Poste 1"]

        # Le total du poste 1 doit être égal au coût racine (36,5 M), et non 36,5 + 36 + 14 + ...
        self.assertEqual(p1_excl["total_ops"], 36500000)
        self.assertEqual(p1_excl["total_exclusive_ops"], 36500000)

        # Détail des éléments
        items = p1_excl["items"]
        self.assertEqual(items["loop.c121_catalog_resume"]["exclusive_ops"], 500000)
        self.assertEqual(items["loop.c121_catalog_resume"]["inclusive_ops"], 36500000)

        self.assertEqual(items["catalog.slice"]["exclusive_ops"], 22000000)
        self.assertEqual(items["catalog.slice"]["inclusive_ops"], 36000000)

        self.assertEqual(items["air.plans"]["exclusive_ops"], 14000000 - (6850000 + 2690000))
        self.assertEqual(items["air.plans"]["inclusive_ops"], 14000000)

        self.assertEqual(items["air.new_pairs"]["exclusive_ops"], 6850000)
        self.assertEqual(items["air.hub_site"]["exclusive_ops"], 2690000)

        # SPAN_AGG est présent pour description mais son coût propre est 0 pour ne pas sur-compter
        self.assertEqual(items["agg:air.c121.demand"]["inclusive_ops"], 3170000)
        self.assertEqual(items["agg:air.c121.demand"]["exclusive_ops"], 0)

        # 2. Mode --inclusive (ancien comportement)
        parser_incl = EngineLogParser()
        for line in lines:
            parser_incl.parse_line("air.log", line)
        data_incl = compile_pcal03_inventory(parser_incl, inclusive=True)
        p1_incl = data_incl["posts"]["Poste 1"]

        # Ancien total : sommation naïve de tous les parents, enfants et aggs
        expected_naive = 36500000 + 36000000 + 14000000 + 6850000 + 2690000 + 3170000
        self.assertEqual(p1_incl["total_ops"], expected_naive)
        self.assertEqual(p1_incl["total_ops"], 99210000)

    def test_file_parsing_and_format_table(self):
        """Vérifie la lecture d'un fichier réel sur disque et le formatage texte."""
        with tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False) as f:
            f.write("OPEX 1970-01-01 SPAN id=2 par=1 dep=1 n=air.plans op=1000\n")
            f.write("OPEX 1970-01-01 SPAN id=1 par=0 dep=0 n=loop.c121_catalog_resume op=3000\n")
            filepath = Path(f.name)

        try:
            parser = EngineLogParser()
            parser.parse_file(filepath)
            data = compile_pcal03_inventory(parser, inclusive=False)
            table_text = format_table(data)
            self.assertIn("Poste 1", table_text)
            self.assertIn("Propre/an", table_text)
            self.assertIn("Inclusif/an", table_text)
            self.assertIn("3 000", table_text)
        finally:
            filepath.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
