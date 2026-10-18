import unittest

import repo_stats


class ClassifyLinesTest(unittest.TestCase):
    def test_squirrel_comments_strings_and_blanks(self):
        text = "\n".join([
            "/* bloc",
            "",
            "   fin */",
            "local a = 1; // fin de ligne",
            "// seul",
            "# diese",
            'local s = "// pas un commentaire";',
            "/* x */ local b = 2;",
            "",
        ])
        self.assertEqual(repo_stats.classify_lines(text, "Squirrel"), (1, 4, 3))

    def test_api_inventory_is_published(self):
        rows = [l.split("\t") for l in repo_stats.API_FILE.read_text().splitlines()]
        kinds = {r[0] for r in rows}
        self.assertEqual(kinds, {"class", "const", "method", "static"})
        self.assertIn(["static", "AIController", "Sleep"], rows)


if __name__ == "__main__":
    unittest.main()
