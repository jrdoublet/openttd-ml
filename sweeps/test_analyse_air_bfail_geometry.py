"""Fixtures HOST du relevé géométrique BFAIL, sans moteur OpenTTD."""
import unittest

from analyse_air_bfail_geometry import analyze_geometry_lines


CORE = ("AIR_FINANCE_TRY date=1970-12-02 path=portfolio outcome=failed reason=BFAIL "
        "new_airports=2 pre_b_ok=1 pre_b_err=0 pre_b_verdict=accept "
        "pre_b_anchor=44793 real_b_err=2 real_b_stage=level actual=20000 "
        "c_level_a=0 c_airport_a=17000 ")
GEO = ("b_level_phase=command_failed b_level_cmd=failed b_level_cmd_err=2 "
       "b_level_retry_err=-1 b_level_w=2 b_level_h=1 b_level_end=400 "
       "b_level_x=249 b_level_y=174 b_level_target_z=2 "
       "b_level_slopes_setting=0 b_level_cash_before=140000 b_level_cash_after=140000 "
       "b_level_pre_mismatch=1 b_level_post_mismatch=1 "
       "b_level_pre_blocked=0 b_level_post_blocked=0 "
       "b_level_pre_slopes=1 b_level_post_slopes=1 "
       "b_level_pre_invalid=0 b_level_post_invalid=0 "
       "b_level_pre_min=2 b_level_pre_max=3 "
       "b_level_post_min=2 b_level_post_max=3 b_level_changed=0 "
       "b_level_pre_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,2.2.0 "
       "b_level_post_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,2.2.0")


class AirGeometryTests(unittest.TestCase):
    def parse(self, line):
        return analyze_geometry_lines([line + "\n"], "reference_seed5678_r0.log")

    def test_direct_command_failure_distinct_from_postcheck(self):
        result = self.parse(CORE + GEO)
        self.assertEqual(result["parsed_b"], 1)
        self.assertEqual(result["cases"][0]["phase"], "command_failed")
        self.assertEqual(result["cases"][0]["b_level_cmd_err"], 2)
        self.assertEqual(result["cases"][0]["changed_tiles"], 0)
        self.assertFalse(result["warnings"])

    def test_postcheck_nonflat_is_a_separate_failure(self):
        result = self.parse((CORE + GEO).replace("real_b_err=2", "real_b_err=263")
                            .replace("b_level_phase=command_failed", "b_level_phase=postcheck_nonflat")
                            .replace("b_level_cmd=failed", "b_level_cmd=ok")
                            .replace("b_level_cmd_err=2", "b_level_cmd_err=0")
                            .replace("b_level_post_slopes=1", "b_level_post_slopes=2")
                            .replace("b_level_changed=0", "b_level_changed=1")
                            .replace("b_level_post_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,2.2.0",
                                     "b_level_post_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,2.3.1"))
        self.assertEqual(result["cases"][0]["changed_tiles"], 1)
        self.assertFalse(result["warnings"])

    def test_built_after_level_success_is_retained(self):
        line = (CORE + GEO).replace("reason=BFAIL", "reason=OK")
        line = line.replace("outcome=failed", "outcome=built")
        line = line.replace("real_b_err=2 real_b_stage=level", "real_b_err=0 real_b_stage=built")
        line = line.replace("b_level_phase=command_failed", "b_level_phase=success")
        line = line.replace("b_level_cmd=failed", "b_level_cmd=ok")
        line = line.replace("b_level_cmd_err=2", "b_level_cmd_err=0")
        line = line.replace("b_level_post_mismatch=1", "b_level_post_mismatch=0")
        line = line.replace("b_level_post_slopes=1", "b_level_post_slopes=0")
        line = line.replace("b_level_post_max=3", "b_level_post_max=2")
        line = line.replace("b_level_changed=0", "b_level_changed=1")
        line = line.replace("b_level_post_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,2.2.0",
                            "b_level_post_grid=2.2.0,2.2.0,2.2.0,2.2.0,2.2.0,2.2.0")
        result = self.parse(line)
        self.assertEqual(result["parsed_b"], 1)
        self.assertFalse(result["warnings"])

    def test_a_failed_first_needs_no_geometry(self):
        line = CORE.replace("reason=BFAIL", "reason=AFAIL").replace("real_b_stage=level", "real_b_stage=not_attempted")
        result = self.parse(line)
        self.assertEqual(result["attempted_b"], 0)
        self.assertEqual(result["parsed_b"], 0)
        self.assertFalse(result["warnings"])

    def test_absent_and_corrupt_geometry_fail_closed(self):
        self.assertEqual(self.parse(CORE)["warnings"][0]["code"], "missing_geometry_fields")
        self.assertEqual(self.parse(CORE + GEO.replace("b_level_pre_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,2.2.0",
                            "b_level_pre_grid=2.2.0"))["warnings"][0]["code"],
                         "invalid_geometry_grid_length")

    def test_stage_mismatch_is_not_counted(self):
        result = self.parse((CORE + GEO).replace("real_b_stage=level", "real_b_stage=built"))
        self.assertEqual(result["parsed_b"], 0)
        self.assertEqual(result["warnings"][0]["code"], "inconsistent_stage_phase")

    def test_edge_tile_must_be_explicitly_invalid(self):
        line = (CORE + GEO).replace("b_level_phase=command_failed", "b_level_phase=invalid_end")
        line = line.replace("b_level_cmd=failed", "b_level_cmd=not_called")
        line = line.replace("b_level_cmd_err=2", "b_level_cmd_err=-1")
        line = line.replace("b_level_pre_invalid=0", "b_level_pre_invalid=1")
        line = line.replace("b_level_post_invalid=0", "b_level_post_invalid=1")
        line = line.replace("b_level_pre_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,2.2.0",
                            "b_level_pre_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,X")
        line = line.replace("b_level_post_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,2.2.0",
                            "b_level_post_grid=2.2.0,2.2.0,2.3.1,2.2.0,2.2.0,X")
        result = self.parse(line)
        self.assertEqual(result["parsed_b"], 1)
        self.assertFalse(result["warnings"])


if __name__ == "__main__":
    unittest.main()
