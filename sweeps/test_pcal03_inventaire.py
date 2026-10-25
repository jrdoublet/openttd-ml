#!/usr/bin/env python3
"""sweeps/test_pcal03_inventaire.py — Tests unitaires de déduplication des spans (PCAL-03).

Vérifie que les spans imbriqués (par=) calculent correctement :
- Le coût inclusif (total mesuré pour la balise)
- Le coût propre / exclusif (inclusif - somme des enfants directs)
- Les totaux de poste sommés sur les coûts propres sans double comptage
- L'option --inclusive pour préserver l'ancien comportement si demandé
"""

import json
import tempfile
import unittest
from pathlib import Path

from sweeps.pcal03_inventaire import EngineLogParser, compile_pcal03_inventory, format_table


class TestPcal03Deduplication(unittest.TestCase):
    def test_profile_examples_use_current_single_mask(self):
        source = (Path(__file__).resolve().parent / "pcal03_inventaire.py").read_text(encoding="utf-8")
        doc = source.split('"""', 2)[1]
        self.assertIn('OpexAI[probes=39170]', doc)
        self.assertIn('--script-debug', doc)
        self.assertNotIn('OpexAI[probe_span_trace=', doc)
        self.assertEqual(39170, 2 | 256 | 2048 | 4096 | 32768)
        self.assertEqual(39170 & 1, 0)

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
