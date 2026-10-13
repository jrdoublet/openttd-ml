import unittest

from analyse_spans_intrinsic_p0 import parse, summarize


class SpanTreeTests(unittest.TestCase):
    def test_nested_costs_are_subtracted_once_and_aggs_not_added(self):
        lines = [
            '[script:4] [0] [I] OPEX 1973-7-1 SPAN id=3 par=2 dep=2 n=select.full ds=1973-7-1 t0=4 tk=0 op=30',
            '[script:4] [0] [I] OPEX 1973-7-1 SPAN_AGG par=3 n=pub.select.score.insert cnt=3 tk=0 op=12',
            '[script:4] [0] [I] OPEX 1973-7-1 SPAN id=2 par=1 dep=1 n=pub.select.score ds=1973-7-1 t0=3 tk=0 op=70',
            '[script:4] [0] [I] OPEX 1973-7-1 SPAN id=1 par=0 dep=0 n=select.reselect ds=1973-7-1 t0=2 tk=1 op=120',
        ]
        nodes, diagnostics = parse(lines)
        self.assertEqual(nodes[1]['exclusive_ops'], 50)
        self.assertEqual(nodes[2]['exclusive_ops'], 40)
        self.assertEqual(nodes[3]['exclusive_ops'], 30)
        self.assertEqual(nodes[3]['aggregates'][0]['op'], 12)
        self.assertEqual(diagnostics['negative_exclusive'], 0)
        report = summarize(nodes)['1973']
        self.assertEqual(report['spans']['select.reselect']['inclusive']['total'], 120)
        self.assertEqual(report['spans']['select.reselect']['exclusive']['total'], 50)
        self.assertEqual(report['intra_span_aggregates']['pub.select.score.insert']['ops'], 12)

    def test_orphans_are_excluded_and_invalid_tree_flagged(self):
        lines = [
            '[script:4] [0] [I] OPEX 1972-12-30 SPAN id=20 par=0 n=select.incremental tk=0 op=10 orphan=1',
            '[script:4] [0] [I] OPEX 1973-1-1 SPAN id=30 par=99 n=select.reselect tk=1 op=25',
        ]
        nodes, q = parse(lines)
        self.assertEqual(q['orphan_spans'], 1)
        self.assertEqual(q['missing_parents'], 1)
        self.assertEqual(summarize(nodes)['1972']['spans'], {})


if __name__ == '__main__':
    unittest.main()
