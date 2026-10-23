"""Static inventory helper contracts, without running an OpenTTD game."""

import unittest

from inventory_squirrel_loops import classify, markdown_index, scan_text


class InventorySquirrelLoopsTests(unittest.TestCase):
    def test_ignores_strings_and_comments_and_tracks_function(self):
        source = '''// for (x in ignored) {}
function OpexDemo(items) {
  local s = "while (trick)";
  foreach (v in items) { if (v > 1) return v; }
  /* for (local i = 0; i < 200; i++) {} */
  for (local n = 0; n < 2; n++) { while (n < 0) break; }
}
'''
        rows = scan_text(source, "demo.nut")
        self.assertEqual([(r.line, r.kind, r.function) for r in rows], [
            (4, "foreach", "OpexDemo"), (6, "for", "OpexDemo"),
            (6, "while", "OpexDemo")])

    def test_multiline_header_and_nested_body(self):
        source = '''function F() {
 while (should_continue(
      count, other)) {
   if (count > 4) { break; }
 }
}
'''
        rows = scan_text(source, "demo.nut")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].line, 2)
        self.assertIn("break", rows[0].body)

    def test_index_retains_every_location_and_class_totals(self):
        source = '''function OpexLoop(items) {
  foreach (town in items) { if (town.pop > 5) continue; }
  while (items.len() > 3) { items.pop(); }
  for (local i = 0; i < 2; i++) { local x = i; }
}
'''
        rows = scan_text(source, "demo.nut")
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(classify(row)[0] in "ABCDH" for row in rows), 3)
        rendered = markdown_index(rows)
        self.assertIn("<!-- INDEX_BEGIN -->", rendered)
        self.assertIn("<!-- INDEX_END -->", rendered)
        for row in rows:
            self.assertIn(f"| {row.line} | `{row.function}` |", rendered)


if __name__ == "__main__":
    unittest.main()
