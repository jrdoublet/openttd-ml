"""Host-only fixtures for observed vs unknown initial rail destination builds."""

from pathlib import Path
import tempfile
import unittest

from sweeps.diag_v307_sink_censure import analyse


def initial(dst):
    return (f"[0] [I] OPEX 1973-1-1 RAIL_BUILD line=1 src=10 dst={dst} "
            "cargo=COAL shared_dest=0 join_end=-\n")


def attempt(dst, reason="SITEAB", ok=0):
    return (f"[0] [I] OPEX 1973-2-1 RAIL_ATTEMPT src=11 dst={dst} "
            f"shared_dest=1 join_end=B reason={reason} ok={ok} iters=5000\n")


def shared(dst):
    return (f"[0] [I] OPEX 1973-2-2 RAIL_BUILD line=2 src=12 dst={dst} "
            "cargo=COAL shared_dest=1 join_end=B\n")


class V307SinkCensureKnownInitialTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def log(self, seed, contents):
        path = self.root / f"reference_seed{seed}_r0.log"
        path.write_text(contents, encoding="utf-8")
        return path

    def test_initial_build_precedes_siteab_and_is_classified_known(self):
        result = analyse([self.log(42, initial(500) + attempt(500))])
        self.assertEqual(result["totals"]["attempts"], 1)
        self.assertEqual(result["failure_by_prior_joins"], {"0": {"SITEAB": 1}})
        self.assertEqual(result["failure_by_prior_joins_known_initial"],
                         {"0": {"SITEAB": 1}})
        self.assertEqual(result["attempt_reasons_without_observed_initial"], {})

    def test_shared_build_never_substitutes_for_missing_initial(self):
        logs = (attempt(500, reason="built", ok=1) + shared(500) +
                attempt(500) + attempt(500, reason="ABND"))
        result = analyse([self.log(42, logs)])
        self.assertEqual(result["totals"]["attempts"], 3)
        self.assertEqual(result["totals"]["ok"], 1)
        self.assertEqual(result["failure_by_prior_joins"],
                         {"1": {"SITEAB": 1, "ABND": 1}})
        self.assertEqual(result["failure_by_prior_joins_known_initial"], {})
        self.assertEqual(result["attempt_reasons_without_observed_initial"],
                         {"ABND": 1, "SITEAB": 1, "built": 1})
        self.assertEqual(result["anomalies"]["build_shared_without_initial"], 1)

    def test_same_destination_in_two_seeds_cannot_borrow_initial_build(self):
        with_initial = self.log(7, initial(500) + attempt(500))
        without_initial = self.log(42, attempt(500))
        result = analyse([with_initial, without_initial])
        self.assertEqual(result["totals"]["attempts"], 2)
        self.assertEqual(result["reasons"]["SITEAB"], 2)
        self.assertEqual(result["failure_by_prior_joins"], {"0": {"SITEAB": 2}})
        self.assertEqual(result["failure_by_prior_joins_known_initial"],
                         {"0": {"SITEAB": 1}})
        self.assertEqual(result["attempt_reasons_without_observed_initial"],
                         {"SITEAB": 1})


if __name__ == "__main__":
    unittest.main()
