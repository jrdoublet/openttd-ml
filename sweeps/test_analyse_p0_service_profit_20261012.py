import unittest
from analyse_p0_service_profit_20261012 import summarize, analyze


def snap(seed=42,year=1973,arm="OpexAI",vehicle=1,mode="air",profit=30):
    return {"seed":seed,"year":year,"repeat":0,"arm":arm,"ok":True,
        "unresolved_vehicles":[],"lines":[{"mode":mode,"vehicle_ids":[vehicle],
        "profit_this_year_gbp":profit,"profit_last_year_gbp":profit/2}]}


class ProfitCompositionTests(unittest.TestCase):
    def test_pair_mode_profit_not_equal_company_profit(self):
        report={"line_telemetry":{"snapshots":[snap(),snap(arm="AAAHogEx",vehicle=2,mode="road",profit=70)]}}
        row=analyze(report,(42,),(1973,))["by_seed_year"]["42/1973"]
        self.assertEqual(30,row["opex_minus_aaa"]["air"]["vehicle_profit_this_year_gbp"])
        self.assertEqual(-70,row["opex_minus_aaa"]["road"]["vehicle_profit_this_year_gbp"])

    def test_duplicate_vehicle_rejected(self):
        s=snap()
        s["lines"].append(dict(s["lines"][0]))
        with self.assertRaisesRegex(ValueError,"duplicate"):
            summarize(s)

    def test_invalid_or_missing_must_not_be_zero(self):
        s=snap();s["unresolved_vehicles"]=[99]
        with self.assertRaises(ValueError): summarize(s)
        t=snap();del t["lines"][0]["profit_this_year_gbp"]
        with self.assertRaisesRegex(ValueError,"missing numerical"):
            summarize(t)


if __name__=="__main__":unittest.main()
