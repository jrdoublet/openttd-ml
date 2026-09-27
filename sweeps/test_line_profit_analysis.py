"""Tests unitaires pour sweeps/line_profit_analysis.py."""
import unittest

from sweeps.line_profit_analysis import (
    PROFIT_RAW_UNITS_PER_GBP,
    extract_estimates_from_signs,
    parse_sign,
    summarize_by_mode,
    track_lines_from_snapshots,
)


class TestLineProfitAnalysis(unittest.TestCase):

    def test_profit_raw_units_scale(self):
        """Vérifie la constante d'échelle 256.0 fixée par OpenTTD / NoAI."""
        self.assertEqual(PROFIT_RAW_UNITS_PER_GBP, 256.0)

    def test_parse_air_signs(self):
        """Parse les panneaux de plan et capital aérien."""
        af = parse_sign("AF|3|1|18500")
        self.assertIsNotNone(af)
        self.assertEqual(af["kind"], "air_plan")
        self.assertEqual(af["line_id"], 3)
        self.assertEqual(af["vehs"], 1)
        self.assertEqual(af["pred_profit"], 18500)

        ah = parse_sign("AH|3|0|42000|0")
        self.assertIsNotNone(ah)
        self.assertEqual(ah["kind"], "air_capital")
        self.assertEqual(ah["line_id"], 3)
        self.assertEqual(ah["reuse_a"], 0)
        self.assertEqual(ah["pred_capital"], 42000)
        self.assertEqual(ah["hub_routes"], 0)

        ac = parse_sign("AC|3|42000|41500|1|1")
        self.assertIsNotNone(ac)
        self.assertEqual(ac["kind"], "air_cost")
        self.assertEqual(ac["line_id"], 3)
        self.assertEqual(ac["planned_capital"], 42000)
        self.assertEqual(ac["actual_cost"], 41500)

    def test_parse_rail_road_signs(self):
        """Parse les panneaux d'évaluation rail/route (OF, OJ, OK, DC, RC)."""
        of = parse_sign("OF|5|65000")
        self.assertIsNotNone(of)
        self.assertEqual(of["kind"], "pred_revenue")
        self.assertEqual(of["line_id"], 5)
        self.assertEqual(of["pred_revenue"], 65000)

        oj = parse_sign("OJ|5|15000")
        self.assertIsNotNone(oj)
        self.assertEqual(oj["kind"], "pred_running")
        self.assertEqual(oj["line_id"], 5)
        self.assertEqual(oj["pred_running"], 15000)

        ok = parse_sign("OK|5|5000")
        self.assertIsNotNone(ok)
        self.assertEqual(ok["kind"], "pred_amort")
        self.assertEqual(ok["line_id"], 5)
        self.assertEqual(ok["pred_amort"], 5000)

        dc = parse_sign("DC|5|80000|78500|1|1|0")
        self.assertIsNotNone(dc)
        self.assertEqual(dc["kind"], "rail_cost")
        self.assertEqual(dc["line_id"], 5)
        self.assertEqual(dc["planned_capital"], 80000)
        self.assertEqual(dc["actual_cost"], 78500)

        rc = parse_sign("RC|72|2|1|12000|2")
        self.assertIsNotNone(rc)
        self.assertEqual(rc["kind"], "road_cost")
        self.assertEqual(rc["line_id"], 2)
        self.assertEqual(rc["actual_cost"], 12000)
        self.assertEqual(rc["vehs"], 2)

    def test_parse_annual_reporting_signs(self):
        """Parse les panneaux du rapport annuel (OZ, OO, OU, OY)."""
        oz = parse_sign("OZ|5|1973|42500")
        self.assertIsNotNone(oz)
        self.assertEqual(oz["kind"], "real_profit")
        self.assertEqual(oz["line_id"], 5)
        self.assertEqual(oz["year"], 1973)
        self.assertEqual(oz["real_profit"], 42500)

        oo = parse_sign("OO|5|1973|57500")
        self.assertIsNotNone(oo)
        self.assertEqual(oo["kind"], "real_revenue")
        self.assertEqual(oo["line_id"], 5)
        self.assertEqual(oo["real_revenue"], 57500)

        ou = parse_sign("OU|5|1973|1|15000")
        self.assertIsNotNone(ou)
        self.assertEqual(ou["kind"], "real_running")
        self.assertEqual(ou["vehs"], 1)
        self.assertEqual(ou["real_run_cost"], 15000)

        oy = parse_sign("OY|5|1973|68|72")
        self.assertIsNotNone(oy)
        self.assertEqual(oy["kind"], "ratings")
        self.assertEqual(oy["rating_a"], 68)
        self.assertEqual(oy["rating_b"], 72)

    def test_parse_invalid_signs(self):
        """Vérifie le rejet robuste des panneaux invalides ou non reconnus."""
        self.assertIsNone(parse_sign(""))
        self.assertIsNone(parse_sign(None))  # type: ignore
        self.assertIsNone(parse_sign("INVALIDE"))
        self.assertIsNone(parse_sign("AF|not_a_number|1|1000"))
        self.assertIsNone(parse_sign("OF|1"))  # trop court

    def test_extract_estimates_from_signs(self):
        """Vérifie la reconstitution de pred_profit et capital par line_id."""
        signs = [
            "OF|1|50000",
            "OJ|1|10000",
            "OK|1|5000",
            "DC|1|70000|69000|1|1|0",
            "AF|2|1|22000",
            "AH|2|1|38000|0",
            "OZ|1|1972|32000",
            "OZ|1|1973|34000",
            "OZ|2|1973|21000",
        ]
        res = extract_estimates_from_signs(signs)
        self.assertIn(1, res)
        self.assertIn(2, res)

        # Ligne 1 (rail) : profit = 50000 - 10000 - 5000 = 35000
        self.assertEqual(res[1]["pred_profit"], 35000)
        self.assertEqual(res[1]["pred_capital"], 70000)
        self.assertEqual(res[1]["actual_capital"], 69000)
        self.assertEqual(res[1]["annual_real_profit"], {1972: 32000, 1973: 34000})

        # Ligne 2 (air) : profit = 22000, capital = 38000
        self.assertEqual(res[2]["pred_profit"], 22000)
        self.assertEqual(res[2]["pred_capital"], 38000)
        self.assertEqual(res[2]["annual_real_profit"], {1973: 21000})

    def test_track_lines_from_snapshots(self):
        """Vérifie la classification montée en charge vs régime sur des snapshots synthétiques."""
        snapshots = [
            {
                "arm": "OpexAI", "seed": 42, "year": 1970,
                "lines": [
                    {
                        "mode": "rail", "line_key_local": "rail|1,2", "vehicles": 1,
                        "profit_this_year_gbp": 3000.0, "profit_last_year_gbp": 0.0,
                    }
                ]
            },
            {
                "arm": "OpexAI", "seed": 42, "year": 1971,
                "lines": [
                    {
                        "mode": "rail", "line_key_local": "rail|1,2", "vehicles": 1,
                        "profit_this_year_gbp": 8000.0, "profit_last_year_gbp": 4000.0,
                    },
                    {
                        "mode": "air", "line_key_local": "air|3,4", "vehicles": 1,
                        "profit_this_year_gbp": 5000.0, "profit_last_year_gbp": 0.0,
                    }
                ]
            },
            {
                "arm": "OpexAI", "seed": 42, "year": 1972,
                "lines": [
                    {
                        "mode": "rail", "line_key_local": "rail|1,2", "vehicles": 1,
                        "profit_this_year_gbp": 8500.0, "profit_last_year_gbp": 9000.0,
                    },
                    {
                        "mode": "air", "line_key_local": "air|3,4", "vehicles": 1,
                        "profit_this_year_gbp": 18000.0, "profit_last_year_gbp": 12000.0,
                    }
                ]
            },
            {
                "arm": "OpexAI", "seed": 42, "year": 1973,
                "lines": [
                    {
                        "mode": "rail", "line_key_local": "rail|1,2", "vehicles": 1,
                        "profit_this_year_gbp": 8200.0, "profit_last_year_gbp": 9500.0,
                    },
                    {
                        "mode": "air", "line_key_local": "air|3,4", "vehicles": 1,
                        "profit_this_year_gbp": 19000.0, "profit_last_year_gbp": 20000.0,
                    }
                ]
            },
        ]

        tracked = track_lines_from_snapshots(snapshots, arm="OpexAI")
        self.assertEqual(len(tracked), 2)

        # Ligne rail|1,2 : première année 1970
        rail = next(l for l in tracked if l["line_key"] == "rail|1,2")
        self.assertEqual(rail["first_year"], 1970)
        # Montée en charge : profit_last en 1971 = 4000.0
        self.assertEqual(rail["ramp_up"], 4000.0)
        # Régime : années >= 1972 (1972 et 1973) -> profit_last = [9000.0, 9500.0]
        self.assertEqual(rail["n_regime_years"], 2)
        self.assertEqual(rail["regime_profits"], [9000.0, 9500.0])
        self.assertEqual(rail["mean_regime"], 9250.0)

        # Ligne air|3,4 : première année 1971
        air = next(l for l in tracked if l["line_key"] == "air|3,4")
        self.assertEqual(air["first_year"], 1971)
        # Montée en charge : profit_last en 1972 = 12000.0
        self.assertEqual(air["ramp_up"], 12000.0)
        # Régime : années >= 1973 (1973 seul) -> profit_last = [20000.0]
        self.assertEqual(air["n_regime_years"], 1)
        self.assertEqual(air["regime_profits"], [20000.0])
        self.assertEqual(air["mean_regime"], 20000.0)

    def test_summarize_by_mode(self):
        """Vérifie le calcul des moyennes, médianes et pourcentages négatifs."""
        synthetic_lines = [
            {
                "mode": "rail", "seed": 42, "vehs": 1,
                "ramp_up": 5000.0, "mean_regime": 20000.0,
            },
            {
                "mode": "rail", "seed": 42, "vehs": 1,
                "ramp_up": 10000.0, "mean_regime": 40000.0,
            },
            {
                "mode": "rail", "seed": 100, "vehs": 1,
                "ramp_up": -1000.0, "mean_regime": -2000.0,
            },
        ]
        s = summarize_by_mode(synthetic_lines)
        self.assertIn("rail", s)
        r = s["rail"]
        self.assertEqual(r["total_lines"], 3)
        self.assertEqual(r["regime_lines"], 3)
        self.assertAlmostEqual(r["regime"]["mean"], (20000 + 40000 - 2000) / 3, places=2)
        self.assertEqual(r["regime"]["median"], 20000.0)
        self.assertEqual(r["regime"]["min"], -2000.0)
        self.assertEqual(r["regime"]["max"], 40000.0)
        self.assertEqual(r["regime"]["negative_count"], 1)
        self.assertAlmostEqual(r["regime"]["negative_pct"], 33.33, places=1)


if __name__ == "__main__":
    unittest.main()
